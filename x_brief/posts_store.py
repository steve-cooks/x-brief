"""
posts_store.py - Simple persistent store for scraped posts.

posts.json schema: list of dicts, each:
  {
    "id": str,           # tweet/post ID
    "author": str,       # display name
    "handle": str,       # @username (no @)
    "text": str,
    "url": str,          # https://x.com/handle/status/ID
    "tab": str,          # "foryou" or "following"
    "scraped_at": str,   # ISO8601 UTC
    "seen": bool         # default False
  }
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


POSTS_FILE = "posts.json"


def _posts_path(data_dir) -> Path:
    return Path(data_dir) / POSTS_FILE


def load_posts(data_dir) -> list:
    """Load all posts from posts.json. Returns [] if file doesn't exist."""
    path = _posts_path(data_dir)
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_posts(data_dir, posts: list):
    """Write posts list to posts.json (creates dirs as needed)."""
    path = _posts_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(posts, indent=2))


def append_posts(data_dir, new_posts: list) -> int:
    """Append new_posts to posts.json, deduping by id. Returns count of posts actually added."""
    existing = load_posts(data_dir)
    existing_ids = {post["id"] for post in existing}
    added = 0

    for post in new_posts:
        if post["id"] not in existing_ids:
            existing.append(post)
            existing_ids.add(post["id"])
            added += 1

    save_posts(data_dir, existing)
    return added


def mark_seen(data_dir, post_ids: list):
    """Mark the given post IDs as seen=True in posts.json."""
    posts = load_posts(data_dir)
    id_set = set(post_ids)

    for post in posts:
        if post["id"] in id_set:
            post["seen"] = True

    save_posts(data_dir, posts)


def get_unseen(data_dir) -> list:
    """Return all posts where seen=False."""
    return [post for post in load_posts(data_dir) if not post.get("seen", False)]


def clear_posts(data_dir):
    """Clear posts.json to empty array (midnight reset)."""
    save_posts(data_dir, [])


def ingest_scan_file(scan_path, data_dir, tab: str) -> int:
    """
    Read a timeline_scans/*.json file and append its posts to posts.json.
    tab: 'foryou' or 'following'
    Returns count of new posts added.
    """
    scan_data = json.loads(Path(scan_path).read_text())

    raw_posts = scan_data.get("timeline") or scan_data.get("posts") or []
    now = datetime.now(timezone.utc).isoformat()
    normalized = []

    for post in raw_posts:
        post_id = str(post.get("id") or post.get("status_id") or post.get("tweetId") or "")
        if not post_id:
            continue

        handle = (
            post.get("authorUsername") or post.get("author_handle") or post.get("screen_name") or post.get("handle") or ""
        ).lstrip("@")
        author = post.get("authorName") or post.get("author_name") or post.get("name") or handle
        text = post.get("text") or post.get("full_text") or ""
        url = post.get("postUrl") or post.get("url") or f"https://x.com/{handle}/status/{post_id}"

        normalized.append(
            {
                "id": post_id,
                "author": author,
                "handle": handle,
                "text": text,
                "url": url,
                "tab": tab,
                "scraped_at": post.get("scraped_at") or post.get("created_at") or now,
                "seen": False,
            }
        )

    return append_posts(data_dir, normalized)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="posts_store CLI")
    parser.add_argument("--clear", action="store_true", help="Clear posts.json (midnight reset)")
    parser.add_argument("--ingest", metavar="SCAN_FILE", help="Ingest a scan file")
    parser.add_argument("--tab", default="foryou", help="Tab name for ingested posts (foryou/following)")
    parser.add_argument("--data-dir", default="data", help="Data directory")
    args = parser.parse_args()

    if args.clear:
        clear_posts(args.data_dir)
        print(f"Cleared posts.json in {args.data_dir}")
    elif args.ingest:
        count = ingest_scan_file(args.ingest, args.data_dir, args.tab)
        print(f"Added {count} new posts from {args.ingest}")
    else:
        posts = load_posts(args.data_dir)
        unseen = get_unseen(args.data_dir)
        print(f"Total: {len(posts)} posts, Unseen: {len(unseen)}")
