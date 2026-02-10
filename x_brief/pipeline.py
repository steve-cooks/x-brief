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
        
        return output

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
