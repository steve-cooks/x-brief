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
                    "alt_text": media.alt_text,
                }
                # For videos and animated_gifs, find best quality variant
                if media.variants and len(media.variants) > 0:
                    # Sort by bitrate (highest first) for video/gif
                    sorted_variants = sorted(
                        [v for v in media.variants if v.get("content_type") in ("video/mp4", "video/webm")],
                        key=lambda v: v.get("bit_rate", 0),
                        reverse=True
                    )
                    if sorted_variants:
                        media_item["video_url"] = sorted_variants[0].get("url")
                        media_item["variants"] = sorted_variants
                media_items.append(media_item)
            
            posts.append({
                "authorName": post.author_name or (user.name if user else post.author_username),
                "authorUsername": post.author_username or (user.username if user else "unknown"),
                "authorAvatarUrl": avatar_url,
                "verified": verified_type,
                "text": post.text,
                "media": media_items,
                "metrics": {
                    "likes": post.metrics.likes,
                    "reposts": post.metrics.reposts,
                    "views": post.metrics.views,
                    "replies": post.metrics.replies,
                },
                "postUrl": f"https://x.com/{post.author_username or 'x'}/status/{post.id}",
                "timestamp": _relative_time(post.created_at),
                "category": item.category if item.category not in ("Top", "Worth a Look") else None,
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
        print("Usage: python -m x_brief.pipeline <config_path> [--hours N]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    hours = 24
    if "--hours" in sys.argv:
        idx = sys.argv.index("--hours")
        hours = int(sys.argv[idx + 1])
    
    asyncio.run(run_briefing(config_path, hours))

if __name__ == "__main__":
    main()
