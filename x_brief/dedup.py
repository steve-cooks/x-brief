"""
Brief history tracking and deduplication.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from x_brief.models import Post


def _parse_iso_datetime(value: object) -> datetime | None:
    """Parse an ISO datetime value into timezone-aware UTC datetime."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
            "last_cleanup": datetime.now(timezone.utc).isoformat(),
        }

    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading brief history: {e}")
        return {
            "posts": {},
            "last_cleanup": datetime.now(timezone.utc).isoformat(),
        }


def filter_already_briefed(posts: list[Post], history: dict, max_age_hours: int = 48) -> list[Post]:
    """
    Remove posts that have already been included in a recent brief.

    Only posts briefed within max_age_hours are excluded.

    Args:
        posts: List of Post objects to filter
        history: Brief history dict from load_brief_history()
        max_age_hours: Recent dedup window in hours (default: 48)

    Returns:
        List of posts not yet briefed in the recent window
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    recent_briefed_ids: set[str] = set()
    for post_id, metadata in history.get('posts', {}).items():
        briefed_at = _parse_iso_datetime(metadata.get('briefed_at') if isinstance(metadata, dict) else None)
        if briefed_at and briefed_at >= cutoff:
            recent_briefed_ids.add(post_id)

    new_posts = [p for p in posts if p.id not in recent_briefed_ids]

    filtered_count = len(posts) - len(new_posts)
    if filtered_count > 0:
        print(f"🔍 Filtered out {filtered_count} already-briefed posts from the last {max_age_hours}h")

    return new_posts


def _should_cleanup(history: dict, min_interval_hours: int = 24) -> bool:
    """Return True when history cleanup should run based on last_cleanup."""
    last_cleanup_dt = _parse_iso_datetime(history.get("last_cleanup"))
    if last_cleanup_dt is None:
        return True

    return datetime.now(timezone.utc) - last_cleanup_dt > timedelta(hours=min_interval_hours)


def save_brief_history(history_path: str, history: dict, new_posts: list[Post], max_age_hours: int = 48) -> None:
    """
    Save updated brief history with new posts.

    Args:
        history_path: Path to history JSON file
        history: Current history dict
        new_posts: Posts to add to history
        max_age_hours: Dedup history window in hours (default: 48)
    """
    path = Path(history_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Cleanup history at most once every 24h
    if _should_cleanup(history, min_interval_hours=24):
        history = cleanup_history(history, max_age_hours=max_age_hours)

    # Add new posts to history
    now = datetime.now(timezone.utc).isoformat()
    history.setdefault('posts', {})
    for post in new_posts:
        history['posts'][post.id] = {
            'url': f"https://x.com/{post.author_username}/status/{post.id}",
            'briefed_at': now,
            'title': post.text[:100],  # Short summary
        }

    # Write back to file
    try:
        with open(path, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"💾 Saved {len(new_posts)} posts to brief history")
    except Exception as e:
        print(f"⚠️ Error saving brief history: {e}")


def cleanup_history(history: dict, max_age_hours: int = 48) -> dict:
    """
    Remove old entries from brief history (default: 48 hours).

    Args:
        history: Brief history dict
        max_age_hours: Maximum age in hours (default: 48)

    Returns:
        Cleaned history dict
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    posts = history.get('posts', {})
    original_count = len(posts)

    cleaned_posts = {}
    for post_id, data in posts.items():
        if not isinstance(data, dict):
            continue
        briefed_at = _parse_iso_datetime(data.get('briefed_at'))
        if briefed_at and briefed_at >= cutoff:
            cleaned_posts[post_id] = data

    removed_count = original_count - len(cleaned_posts)
    if removed_count > 0:
        print(f"🗑️  Cleaned up {removed_count} old entries from brief history")

    return {
        'posts': cleaned_posts,
        'last_cleanup': datetime.now(timezone.utc).isoformat(),
    }
