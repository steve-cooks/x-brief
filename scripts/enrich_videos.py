#!/usr/bin/env python3
"""
Enrich posts.json video entries with real playable video URLs using yt-dlp.
Run after ingest: python3 scripts/enrich_videos.py
"""
import json, subprocess, sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
POSTS_FILE = DATA_DIR / "posts.json"
YTDLP = str(Path.home() / ".local/bin/yt-dlp")

def get_video_url(post_url: str) -> str | None:
    try:
        result = subprocess.run(
            [YTDLP, "-f", "best[height<=720]", "--get-url", "--no-playlist", post_url],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            url = result.stdout.strip().splitlines()[0]
            if url.startswith("https://"):
                return url
    except Exception:
        pass
    return None

def main():
    posts = json.loads(POSTS_FILE.read_text())
    changed = 0
    
    for post in posts:
        for media_item in post.get("media", []):
            if media_item.get("type") == "video" and not media_item.get("video_url"):
                post_url = post.get("url", "")
                if not post_url:
                    continue
                print(f"Fetching video URL for @{post.get('handle', '?')}...")
                video_url = get_video_url(post_url)
                if video_url:
                    media_item["video_url"] = video_url
                    changed += 1
                    print(f"  OK {video_url[:60]}")
                else:
                    print(f"  FAILED")
    
    if changed:
        POSTS_FILE.write_text(json.dumps(posts, ensure_ascii=False))
        print(f"\nEnriched {changed} video(s)")
    else:
        print("No videos needed enrichment")

if __name__ == "__main__":
    main()
