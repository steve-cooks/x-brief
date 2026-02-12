"""
Brief history tracking and deduplication for X Brief.
Ensures no post appears in more than one brief.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .models import Post


def load_brief_history(history_path: str) -> dict:
    """Load the brief history file. Returns empty structure if not found."""
    try:
        with open(history_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"posts": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()}


def filter_already_briefed(posts: list[Post], history: dict) -> list[Post]:
    """
    Remove posts that have already appeared in a previous brief.
    
    Args:
        posts: List of Post objects to filter
        history: Brief history dict with 'posts' mapping post_id -> metadata
    
    Returns:
        List of posts NOT in history (new posts only)
    """
    known_ids = set(history.get("posts", {}).keys())
    new_posts = [p for p in posts if p.id not in known_ids]
    filtered_count = len(posts) - len(new_posts)
    if filtered_count > 0:
        print(f"  🔄 Filtered {filtered_count} already-briefed posts ({len(new_posts)} remaining)")
    return new_posts


def save_brief_history(history_path: str, history: dict, new_posts: list[Post]) -> None:
    """
    Add new post IDs to the brief history and save.
    
    Args:
        history_path: Path to brief_history.json
        history: Current history dict
        new_posts: Posts that were included in this brief
    """
    now = datetime.now(timezone.utc).isoformat()
    
    for post in new_posts:
        history["posts"][post.id] = {
            "url": f"https://x.com/{post.author_username}/status/{post.id}",
            "author": post.author_username,
            "briefed_at": now,
            "summary": post.text[:80] if post.text else "",
        }
    
    # Run cleanup while we're at it
    cleanup_history(history)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(history_path) or ".", exist_ok=True)
    
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2, default=str)
    
    print(f"  📝 Saved {len(new_posts)} posts to brief history ({len(history['posts'])} total tracked)")


def cleanup_history(history: dict, max_age_hours: int = 168) -> None:
    """
    Remove entries older than max_age_hours (default 7 days) to prevent unbounded growth.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    posts = history.get("posts", {})
    
    to_remove = []
    for post_id, meta in posts.items():
        briefed_at_str = meta.get("briefed_at", "")
        try:
            briefed_at = datetime.fromisoformat(briefed_at_str)
            if briefed_at < cutoff:
                to_remove.append(post_id)
        except (ValueError, TypeError):
            # If we can't parse the date, keep it (conservative)
            pass
    
    for post_id in to_remove:
        del posts[post_id]
    
    if to_remove:
        print(f"  🧹 Cleaned up {len(to_remove)} expired entries from brief history")
    
    history["last_cleanup"] = datetime.now(timezone.utc).isoformat()
