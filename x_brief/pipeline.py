"""End-to-end briefing pipeline for X Brief."""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from x_brief.config import XBriefConfig, load_user_config
from x_brief.fetcher import XClient
from x_brief.analyzer import infer_interests, build_search_queries
from x_brief.curator import curate_briefing
from x_brief.formatter import format_markdown
from x_brief.models import User
from x_brief.scan_reader import load_scan_posts, build_users_from_posts
from x_brief.dedup import load_brief_history, filter_already_briefed, save_brief_history

async def run_briefing(config_path: str, hours: int = 24) -> str:
    """Full pipeline: load config -> fetch -> analyze -> curate -> format."""
    
    # 1. Load configs
    user_config = load_user_config(config_path)
    bearer_token = os.environ.get("X_BRIEF_BEARER_TOKEN", "")
    if not bearer_token:
        raise ValueError("X_BRIEF_BEARER_TOKEN environment variable not set")
    
    print(f"📋 Loaded config: {len(user_config.tracked_accounts)} tracked accounts")
    
    async with XClient(bearer_token) as client:
        # 2. Resolve usernames to User objects
        print("🔍 Resolving user accounts...")
        usernames = user_config.tracked_accounts
        users: list[User] = []
        
        # Batch resolve (100 max per request)
        for i in range(0, len(usernames), 100):
            batch = usernames[i:i+100]
            batch_users = await client.get_users_by_usernames(batch)
            users.extend(batch_users)
            print(f"  Resolved {len(users)}/{len(usernames)} accounts")
        
        users_map = {u.id: u for u in users}
        print(f"✅ Resolved {len(users)} accounts")
        
        # 3. Infer interests from user bios
        interests = infer_interests(users)
        if user_config.recent_interests:
            interests = list(set(interests + user_config.recent_interests))
        print(f"🧠 Detected interests: {', '.join(interests)}")
        
        # 4. Fetch tweets from tracked accounts
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        end_time = datetime.now(timezone.utc)
        
        print(f"📥 Fetching tweets from last {hours}h...")
        all_posts = []
        errors = 0
        for i, user in enumerate(users):
            try:
                tweets = await client.get_user_tweets(
                    user.id, start_time=start_time, end_time=end_time, max_results=20
                )
                all_posts.extend(tweets)
                if (i + 1) % 10 == 0:
                    print(f"  Fetched from {i+1}/{len(users)} accounts ({len(all_posts)} posts)")
            except Exception as e:
                errors += 1
                if "429" in str(e) or "Too Many" in str(e):
                    print(f"  ⚠️ Rate limited at account {i+1}, waiting 60s...")
                    await asyncio.sleep(60)
                    try:
                        tweets = await client.get_user_tweets(
                            user.id, start_time=start_time, end_time=end_time, max_results=20
                        )
                        all_posts.extend(tweets)
                    except Exception:
                        pass
                else:
                    print(f"  ⚠️ Error fetching @{user.username}: {e}")
        
        print(f"✅ Fetched {len(all_posts)} posts from tracked accounts ({errors} errors)")
        
        # 5. Search for trending posts in interest areas
        search_queries = build_search_queries(interests)
        search_posts = []
        print(f"🔎 Searching {len(search_queries)} interest areas...")
        for query in search_queries[:3]:  # Limit to top 3 to save API credits
            try:
                results = await client.search_tweets(
                    query, start_time=start_time, end_time=end_time, max_results=20
                )
                search_posts.extend(results)
            except Exception as e:
                print(f"  ⚠️ Search error: {e}")
        print(f"✅ Found {len(search_posts)} trending posts")
        
        # 6. Curate and format
        print("🎯 Curating briefing...")
        briefing = curate_briefing(
            posts=all_posts,
            users=users_map,
            interests=interests,
            hours=hours,
            search_posts=search_posts,
        )
        
        # 7. Format
        output = format_markdown(briefing)
        print(f"\n{'='*60}")
        print(output)
        print(f"{'='*60}")
        
        # 8. Export JSON for web frontend
        json_data = export_briefing_json(briefing, users_map, hours)
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        json_path = os.path.join(data_dir, "latest-briefing.json")
        import json as json_mod
        with open(json_path, "w") as f:
            json_mod.dump(json_data, f, indent=2, default=str)
        print(f"📄 JSON exported to {json_path}")
        
        return output


async def run_briefing_from_scans(
    config_path: str,
    scan_dir: str = None,
    hours: int = 48,
    skip_dedup: bool = False,
) -> str:
    """
    Pipeline that reads from Rabbit's timeline scan data instead of the X API.
    
    Args:
        config_path: Path to user config (for interests, tracked accounts)
        scan_dir: Directory with scan JSONs (default: ~/projects/second-brain/timeline_scans/)
        hours: Only include posts from scans within the last N hours (default 48)
    """
    # Default scan directory
    if scan_dir is None:
        scan_dir = os.path.expanduser("~/projects/second-brain/timeline_scans/")
    
    # History file for deduplication
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    history_path = os.path.join(data_dir, "brief_history.json")
    
    # 1. Load config for interests
    user_config = load_user_config(config_path)
    interests = user_config.recent_interests or [
        "AI", "Machine Learning", "LLMs", "Claude", "OpenAI", "Cursor",
        "OpenClaw", "Startups", "Building", "SaaS", "Design", "Trading bots",
    ]
    print(f"📋 Config loaded. Interests: {', '.join(interests)}")
    
    # 2. Load posts from scan data
    print(f"📂 Reading scans from {scan_dir} (last {hours}h)...")
    all_posts, scan_verified = load_scan_posts(scan_dir, hours=hours)
    
    if not all_posts:
        print("⚠️ No posts found in scan data. Nothing to brief on.")
        return "No posts found in scan data."
    
    # 3. Deduplicate against brief history (unless skipped for web app)
    if skip_dedup:
        print("⏭️  Skipping dedup (web app mode)")
        fresh_posts = all_posts
        history = None
    else:
        print("🔄 Checking brief history for duplicates...")
        history = load_brief_history(history_path)
        fresh_posts = filter_already_briefed(all_posts, history)
        
        if not fresh_posts:
            print("⚠️ All scanned posts have already been briefed. Nothing new.")
            return "All posts already briefed."
    
    # 4. Build users map from posts (with verification data)
    users_map = build_users_from_posts(fresh_posts, scan_verified=scan_verified)
    print(f"👥 Built {len(users_map)} user profiles from scan data")
    
    # 5. Curate briefing using existing scoring/curation logic
    print("🎯 Curating briefing...")
    briefing = curate_briefing(
        posts=fresh_posts,
        users=users_map,
        interests=interests,
        hours=hours,
        search_posts=fresh_posts,  # Treat all scan posts as potential search results too
    )
    
    # 6. Format
    output = format_markdown(briefing)
    print(f"\n{'='*60}")
    print(output)
    print(f"{'='*60}")
    
    # 7. Export JSON for web frontend
    json_data = export_briefing_json(briefing, users_map, hours)
    json_path = os.path.join(data_dir, "latest-briefing.json")
    with open(json_path, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    print(f"📄 JSON exported to {json_path}")
    
    # 8. Save posts to brief history (only when dedup is active — i.e., morning brief)
    if not skip_dedup and history is not None:
        briefed_posts = []
        for section in briefing.sections:
            for item in section.items:
                briefed_posts.append(item.post)
        save_brief_history(history_path, history, briefed_posts)
    
    return output


def export_briefing_json(briefing, users_map: dict, hours: int) -> dict:
    """Export briefing as JSON for the web frontend."""
    sections = []
    for section in briefing.sections:
        posts = []
        for item in section.items:
            post = item.post
            user = users_map.get(post.author_id)
            avatar_url = user.profile_image_url if user else None
            # Get higher res avatar (replace _normal with _bigger or _400x400)
            if avatar_url:
                avatar_url = avatar_url.replace("_normal", "_400x400")
            
            verified_type = user.verified_type if user else None
            
            # Format media for frontend
            media_items = []
            for media in post.media:
                media_item = {
                    "type": media.type,
                    "url": media.url,
                    "preview_image_url": media.preview_image_url,
                    "video_url": media.video_url,
                    "alt_text": media.alt_text,
                }
                media_items.append(media_item)
            
            # Strip "(pinned)" artifacts from scraped author data
            clean_author_name = (post.author_name or (user.name if user else post.author_username) or "").replace(" (pinned)", "")
            clean_author_username = (post.author_username or (user.username if user else "unknown") or "").replace(" (pinned)", "")
            clean_avatar_url = avatar_url.replace(" (pinned)", "") if avatar_url else None
            # Fallback to unavatar.io if no avatar URL from scraper
            if not clean_avatar_url and clean_author_username:
                clean_avatar_url = f"https://unavatar.io/twitter/{clean_author_username}"

            # Build quoted post data if present
            quoted_post_data = None
            if post.quoted_post:
                qp = post.quoted_post
                quoted_post_data = {
                    "authorName": qp.author_name,
                    "authorUsername": qp.author_username,
                    "text": qp.text,
                    "postUrl": qp.post_url,
                }
                if qp.metrics:
                    quoted_post_data["metrics"] = {
                        "likes": qp.metrics.likes,
                        "reposts": qp.metrics.reposts,
                        "views": qp.metrics.views,
                        "replies": qp.metrics.replies,
                        "bookmarks": qp.metrics.bookmarks,
                    }

            posts.append({
                "authorName": clean_author_name,
                "authorUsername": clean_author_username,
                "authorAvatarUrl": clean_avatar_url,
                "verified": verified_type,
                "text": post.text,
                "media": media_items,
                "quotedPost": quoted_post_data,
                "metrics": {
                    "likes": post.metrics.likes,
                    "reposts": post.metrics.reposts,
                    "views": post.metrics.views,
                    "replies": post.metrics.replies,
                    "bookmarks": post.metrics.bookmarks,
                },
                "postUrl": f"https://x.com/{clean_author_username}/status/{post.id}",
                "timestamp": _relative_time(post.created_at),
                "createdAt": post.created_at.isoformat() if post.created_at else None,
                "category": item.category,
            })
        sections.append({
            "title": section.title,
            "emoji": section.emoji,
            "posts": posts,
        })
    
    return {
        "generated_at": briefing.generated_at.isoformat(),
        "period_hours": hours,
        "sections": sections,
        "stats": briefing.stats,
    }


def enrich_briefing_json(json_path: str) -> None:
    """
    Enrich an existing briefing JSON with missing avatar URLs.
    
    Uses unavatar.io to fetch real Twitter avatars without API access.
    Can be called after either the API pipeline or browser scraper generates the JSON.
    
    Args:
        json_path: Path to the latest-briefing.json file
    """
    import json as json_mod
    
    # Read existing JSON
    try:
        with open(json_path, "r") as f:
            data = json_mod.load(f)
    except FileNotFoundError:
        print(f"⚠️ File not found: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in: {json_path}")
        return
    
    enriched_count = 0
    
    # Process each section
    for section in data.get("sections", []):
        for post in section.get("posts", []):
            # Skip if avatar already present and valid
            current_avatar = post.get("authorAvatarUrl")
            if current_avatar and "pbs.twimg.com" in current_avatar:
                continue
            
            # Get username and construct unavatar URL
            username = post.get("authorUsername")
            if username:
                # unavatar.io provides real Twitter avatars without API
                avatar_url = f"https://unavatar.io/twitter/{username}"
                post["authorAvatarUrl"] = avatar_url
                enriched_count += 1
    
    # Write back enriched JSON
    with open(json_path, "w") as f:
        json_mod.dump(data, f, indent=2, default=str)
    
    print(f"✅ Enriched {enriched_count} posts with avatar URLs in {json_path}")


def _relative_time(dt) -> str:
    """Convert datetime to relative time string."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return f"{int(diff.total_seconds() / 60)}m"
    elif hours < 24:
        return f"{int(hours)}h"
    else:
        return f"{int(hours / 24)}d"

def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m x_brief.pipeline <config_path> [--hours N] [--from-scans] [--scan-dir PATH]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    hours = 48 if "--from-scans" in sys.argv else 24
    if "--hours" in sys.argv:
        idx = sys.argv.index("--hours")
        hours = int(sys.argv[idx + 1])
    
    scan_dir = None
    if "--scan-dir" in sys.argv:
        idx = sys.argv.index("--scan-dir")
        scan_dir = sys.argv[idx + 1]
    
    skip_dedup = "--skip-dedup" in sys.argv
    
    if "--from-scans" in sys.argv:
        asyncio.run(run_briefing_from_scans(config_path, scan_dir=scan_dir, hours=hours, skip_dedup=skip_dedup))
    else:
        asyncio.run(run_briefing(config_path, hours))

if __name__ == "__main__":
    main()
