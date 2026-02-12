"""
Read and parse Rabbit timeline scan JSON files into Post objects.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from x_brief.models import Post, PostMetrics, User


def extract_post_id(url: str) -> Optional[str]:
    """Extract post ID from X/Twitter URL."""
    match = re.search(r'/status/(\d+)', url)
    return match.group(1) if match else None


def extract_username(handle_or_url: str) -> str:
    """Extract username from @handle or URL."""
    # Remove @ if present
    if handle_or_url.startswith('@'):
        return handle_or_url[1:]
    # Extract from URL if it's a URL
    match = re.search(r'x\.com/([^/]+)', handle_or_url)
    if match:
        return match.group(1)
    return handle_or_url.strip('@')


def parse_scan_post(post_data: dict, scan_time: datetime) -> Optional[Post]:
    """Convert a scan post dict to a Post object."""
    try:
        # Extract post ID from URL
        url = post_data.get('url', '')
        post_id = extract_post_id(url)
        if not post_id:
            return None
        
        # Extract author info
        author = post_data.get('author', '')
        author_username = extract_username(author)
        author_name = post_data.get('author_name', author_username)
        
        # Parse metrics
        metrics_data = post_data.get('metrics', {})
        metrics = PostMetrics(
            likes=metrics_data.get('likes', 0),
            reposts=metrics_data.get('reposts', 0),
            replies=metrics_data.get('replies', 0),
            views=metrics_data.get('views', 0),
            quotes=0  # Not in scan data
        )
        
        # Create Post object
        post = Post(
            id=post_id,
            text=post_data.get('text', ''),
            author_id=author_username,  # Use username as ID since we don't have real IDs
            author_username=author_username,
            author_name=author_name,
            created_at=scan_time,  # Use scan time as proxy for post time
            metrics=metrics,
            urls=[],  # Could extract from text if needed
            is_repost=False,
            is_quote=False
        )
        
        return post
    except Exception as e:
        print(f"  ⚠️ Error parsing post: {e}")
        return None


def load_scan_posts(scan_dir: str, hours: int = 48) -> list[Post]:
    """
    Load posts from Rabbit timeline scan JSON files.
    
    Args:
        scan_dir: Directory containing scan JSON files (YYYY-MM-DD-HH.json format)
        hours: Only load scans from the last N hours
    
    Returns:
        List of Post objects, deduplicated by post ID
    """
    scan_path = Path(scan_dir).expanduser()
    if not scan_path.exists():
        print(f"⚠️ Scan directory not found: {scan_path}")
        return []
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    posts_by_id: dict[str, Post] = {}  # Deduplicate by post ID
    scans_loaded = 0
    
    print(f"📁 Loading scans from {scan_path}")
    print(f"   Cutoff: {cutoff_time.isoformat()} ({hours}h ago)")
    
    # Find all JSON files matching the pattern
    json_files = sorted(scan_path.glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                scan_data = json.load(f)
            
            # Parse scan time
            scan_time_str = scan_data.get('scan_time')
            if not scan_time_str:
                continue
            
            scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))
            
            # Skip if too old
            if scan_time < cutoff_time:
                continue
            
            scans_loaded += 1
            
            # Process viral_alerts
            for post_data in scan_data.get('viral_alerts', []):
                post = parse_scan_post(post_data, scan_time)
                if post and post.id not in posts_by_id:
                    posts_by_id[post.id] = post
            
            # Process notable_posts
            for post_data in scan_data.get('notable_posts', []):
                post = parse_scan_post(post_data, scan_time)
                if post and post.id not in posts_by_id:
                    posts_by_id[post.id] = post
        
        except Exception as e:
            print(f"  ⚠️ Error loading {json_file.name}: {e}")
            continue
    
    posts = list(posts_by_id.values())
    print(f"✅ Loaded {len(posts)} unique posts from {scans_loaded} scan files")
    
    return posts


def build_users_from_posts(posts: list[Post]) -> dict[str, User]:
    """
    Build a minimal users dictionary from post data.
    
    Since scan data doesn't include full user profiles, we create minimal
    User objects with just the info we have from posts.
    
    Args:
        posts: List of Post objects
    
    Returns:
        Dict mapping author_id (username) to User object
    """
    users_map: dict[str, User] = {}
    
    for post in posts:
        if post.author_id not in users_map:
            # Create minimal User object
            users_map[post.author_id] = User(
                id=post.author_id,
                username=post.author_username,
                name=post.author_name,
                description=None,
                followers_count=1000,  # Default moderate count for scoring
                verified=False,
                profile_image_url=None
            )
    
    return users_map
