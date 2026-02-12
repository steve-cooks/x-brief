"""
Read Rabbit's timeline scan JSON files and convert to Post objects for the X Brief pipeline.
"""

import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .models import Post, PostMetrics, User


def load_scan_posts(scan_dir: str, hours: int = 48) -> list[Post]:
    """
    Load posts from Rabbit's timeline scan JSON files.
    
    Args:
        scan_dir: Directory containing YYYY-MM-DD-HH.json scan files
        hours: Only include scans from the last N hours (default 48)
    
    Returns:
        Deduplicated list of Post objects from all matching scans
    """
    scan_path = Path(scan_dir)
    if not scan_path.exists():
        print(f"⚠️ Scan directory not found: {scan_dir}")
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    seen_ids: set[str] = set()
    posts: list[Post] = []
    
    # Find all JSON scan files (YYYY-MM-DD-HH.json pattern)
    json_files = sorted(scan_path.glob("20??-??-??-??.json"))
    
    for fpath in json_files:
        try:
            with open(fpath, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"  ⚠️ Skipping {fpath.name}: {e}")
            continue
        
        # Parse scan_time and check if within window
        scan_time_str = data.get("scan_time", "")
        try:
            scan_time = datetime.fromisoformat(scan_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            print(f"  ⚠️ Skipping {fpath.name}: invalid scan_time")
            continue
        
        if scan_time < cutoff:
            continue
        
        # Process viral_alerts and notable_posts
        for entry in data.get("viral_alerts", []) + data.get("notable_posts", []):
            post = _parse_scan_entry(entry, scan_time)
            if post and post.id not in seen_ids:
                seen_ids.add(post.id)
                posts.append(post)
    
    print(f"✅ Loaded {len(posts)} posts from {len(json_files)} scan files (last {hours}h)")
    return posts


def build_users_from_posts(posts: list[Post]) -> dict[str, User]:
    """
    Build a minimal users dict from scan-sourced posts.
    Since scans don't have follower counts, we use defaults.
    """
    users: dict[str, User] = {}
    for post in posts:
        if post.author_id not in users:
            users[post.author_id] = User(
                id=post.author_id,
                username=post.author_username or post.author_id,
                name=post.author_name or post.author_username or post.author_id,
                description=None,
                followers_count=10000,  # Default — scans don't have this
                verified=False,
                profile_image_url=f"https://unavatar.io/twitter/{post.author_username or post.author_id}",
            )
    return users


def _parse_scan_entry(entry: dict, scan_time: datetime) -> Optional[Post]:
    """Parse a single scan entry (viral_alert or notable_post) into a Post."""
    url = entry.get("url", "")
    
    # Extract post ID from URL: https://x.com/handle/status/123456
    id_match = re.search(r'/status/(\d+)', url)
    if not id_match:
        return None
    post_id = id_match.group(1)
    
    # Extract username from @handle or URL
    author_raw = entry.get("author", "")
    username = author_raw.lstrip("@")
    if not username:
        # Try from URL
        user_match = re.search(r'x\.com/(\w+)/status/', url)
        username = user_match.group(1) if user_match else "unknown"
    
    author_name = entry.get("author_name", username)
    
    # Parse metrics
    metrics_data = entry.get("metrics", {})
    metrics = PostMetrics(
        likes=metrics_data.get("likes", 0),
        reposts=metrics_data.get("reposts", 0),
        replies=metrics_data.get("replies", 0),
        views=metrics_data.get("views", 0),
        quotes=metrics_data.get("quotes", 0),
    )
    
    text = entry.get("text", "")
    
    return Post(
        id=post_id,
        text=text,
        author_id=username,  # Use username as ID (no real ID from scans)
        author_username=username,
        author_name=author_name,
        created_at=scan_time,  # Use scan time as proxy
        metrics=metrics,
        media=[],
        urls=[url] if url else [],
        is_repost=False,
        is_quote=False,
    )
