"""
Brief history tracking and deduplication.
"""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from x_brief.models import Post


def load_brief_history(history_path: str) -> dict:
    """
    Load brief history from JSON file.
    
    Returns:
        Dict with 'posts' and 'last_cleanup' keys
    """
    path = Path(history_path).expanduser()
    
    if not path.exists():
        return {
            "posts": {},
            "last_cleanup": datetime.now(timezone.utc).isoformat()
        }
    
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading brief history: {e}")
        return {
            "posts": {},
            "last_cleanup": datetime.now(timezone.utc).isoformat()
        }


def filter_already_briefed(posts: list[Post], history: dict) -> list[Post]:
    """
    Remove posts that have already been included in a brief.
    
    Args:
        posts: List of Post objects to filter
        history: Brief history dict from load_brief_history()
    
    Returns:
        List of posts not yet briefed
    """
    briefed_ids = set(history.get('posts', {}).keys())
    new_posts = [p for p in posts if p.id not in briefed_ids]
    
    filtered_count = len(posts) - len(new_posts)
    if filtered_count > 0:
        print(f"🔍 Filtered out {filtered_count} already-briefed posts")
    
    return new_posts


def _should_cleanup(history: dict, min_interval_hours: int = 24) -> bool:
    """Return True when history cleanup should run based on last_cleanup."""
    last_cleanup_raw = history.get("last_cleanup")
    if not last_cleanup_raw:
        return True

    try:
        last_cleanup_dt = datetime.fromisoformat(last_cleanup_raw.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True

    if last_cleanup_dt.tzinfo is None:
        last_cleanup_dt = last_cleanup_dt.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - last_cleanup_dt > timedelta(hours=min_interval_hours)


def save_brief_history(history_path: str, history: dict, new_posts: list[Post]) -> None:
    """
    Save updated brief history with new posts.
    
    Args:
        history_path: Path to history JSON file
        history: Current history dict
        new_posts: Posts to add to history
    """
    path = Path(history_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Cleanup history at most once every 24h
    if _should_cleanup(history, min_interval_hours=24):
        history = cleanup_history(history)

    # Add new posts to history
    now = datetime.now(timezone.utc).isoformat()
    for post in new_posts:
        history['posts'][post.id] = {
            'url': f"https://x.com/{post.author_username}/status/{post.id}",
            'briefed_at': now,
            'title': post.text[:100]  # Short summary
        }
    
    # Write back to file
    try:
        with open(path, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"💾 Saved {len(new_posts)} posts to brief history")
    except Exception as e:
        print(f"⚠️ Error saving brief history: {e}")


def cleanup_history(history: dict, max_age_hours: int = 168) -> dict:
    """
    Remove old entries from brief history (default: 7 days).
    
    Args:
        history: Brief history dict
        max_age_hours: Maximum age in hours (default: 168 = 7 days)
    
    Returns:
        Cleaned history dict
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    cutoff_iso = cutoff.isoformat()
    
    posts = history.get('posts', {})
    original_count = len(posts)
    
    # Filter out old posts
    cleaned_posts = {
        post_id: data
        for post_id, data in posts.items()
        if data.get('briefed_at', '9999-99-99') > cutoff_iso
    }
    
    removed_count = original_count - len(cleaned_posts)
    if removed_count > 0:
        print(f"🗑️  Cleaned up {removed_count} old entries from brief history")
    
    return {
        'posts': cleaned_posts,
        'last_cleanup': datetime.now(timezone.utc).isoformat()
    }
