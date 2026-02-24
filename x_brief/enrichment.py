"""
Syndication API enrichment for X Brief.

Fetches rich media data (photos, videos, GIFs, quote tweets, link cards)
from X's public syndication endpoint and enriches the briefing JSON.

Usage:
    python3 -m x_brief.enrichment [path_to_briefing.json]
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from typing import Optional


SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x"
MAX_POSTS_PER_RUN = 30
REQUEST_DELAY_SEC = 1.0


def _extract_tweet_id(post_url: str) -> Optional[str]:
    """Extract numeric tweet ID from a post URL like https://x.com/user/status/123."""
    match = re.search(r"/status/(\d+)", post_url or "")
    return match.group(1) if match else None


def _fetch_syndication(tweet_id: str) -> Optional[dict]:
    """Fetch tweet data from the syndication API. Returns None on failure."""
    url = SYNDICATION_URL.format(tweet_id=tweet_id)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def _best_mp4_variant(video_info: dict) -> Optional[str]:
    """Pick the highest-bitrate MP4 variant from video_info."""
    variants = video_info.get("variants", [])
    mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
    if not mp4s:
        return None
    # Sort by bitrate descending, pick best
    mp4s.sort(key=lambda v: v.get("bitrate", 0), reverse=True)
    return mp4s[0].get("url")


def _extract_media(data: dict) -> list[dict]:
    """Extract media items from syndication response."""
    media_items = []
    for detail in data.get("mediaDetails", []):
        media_type = detail.get("type", "photo")
        media_url = detail.get("media_url_https", "")

        if media_type == "photo":
            media_items.append({
                "type": "photo",
                "url": media_url,
            })
        elif media_type == "video":
            video_url = None
            vi = detail.get("video_info")
            if vi:
                video_url = _best_mp4_variant(vi)
            media_items.append({
                "type": "video",
                "url": media_url,
                "preview_image_url": media_url,
                "video_url": video_url,
            })
        elif media_type == "animated_gif":
            video_url = None
            vi = detail.get("video_info")
            if vi:
                video_url = _best_mp4_variant(vi)
            media_items.append({
                "type": "animated_gif",
                "url": media_url,
                "preview_image_url": media_url,
                "video_url": video_url,
            })

    return media_items


def _extract_quoted_post(data: dict) -> Optional[dict]:
    """Extract quoted tweet data from syndication response."""
    qt = data.get("quoted_tweet")
    if not qt:
        return None

    user = qt.get("user", {})
    screen_name = user.get("screen_name", "")
    tweet_id = qt.get("id_str", "")

    avatar_url = user.get("profile_image_url_https", "")
    if avatar_url:
        avatar_url = avatar_url.replace("_normal", "_400x400")

    verified = None
    if user.get("is_blue_verified"):
        verified = "blue"

    quoted = {
        "authorName": user.get("name", ""),
        "authorUsername": screen_name,
        "authorAvatarUrl": avatar_url or None,
        "verified": verified,
        "text": qt.get("text", ""),
        "postUrl": f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name and tweet_id else None,
        "media": _extract_media(qt),
    }
    return quoted


def _extract_link_card(data: dict) -> Optional[dict]:
    """Extract link card data from syndication response card."""
    card = data.get("card")
    if not card:
        return None

    bv = card.get("binding_values", {})
    if not bv:
        return None

    title = bv.get("title", {}).get("string_value", "")
    if not title:
        return None

    description = bv.get("description", {}).get("string_value", "")

    # Try multiple thumbnail sources
    thumbnail = None
    for key in ("summary_photo_image_large", "photo_image_full_size_large",
                "summary_photo_image", "thumbnail_image_large"):
        img_val = bv.get(key, {}).get("image_value", {})
        if img_val.get("url"):
            thumbnail = img_val["url"]
            break

    domain = (
        bv.get("vanity_url", {}).get("string_value", "")
        or bv.get("domain", {}).get("string_value", "")
    )

    card_url = bv.get("card_url", {}).get("string_value", "")

    return {
        "title": title,
        "description": description,
        "thumbnail": thumbnail,
        "domain": domain,
        "url": card_url,
    }


def _upgrade_avatar(data: dict) -> Optional[str]:
    """Get high-res avatar URL from syndication user data."""
    user = data.get("user", {})
    avatar = user.get("profile_image_url_https", "")
    if avatar:
        return avatar.replace("_normal", "_400x400")
    return None


def enrich_with_syndication(json_path: str) -> None:
    """
    Enrich a briefing JSON file with rich media data from X's syndication API.

    For each post, fetches photos, videos, GIFs, quoted tweets, and link cards.
    Additive only — never removes existing data.

    Args:
        json_path: Path to the briefing JSON file (e.g., data/latest-briefing.json)
    """
    # Read existing JSON
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ File not found: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in: {json_path}")
        return

    # Collect all posts across sections
    all_posts: list[tuple[dict, str]] = []  # (post_dict, section_title)
    for section in data.get("sections", []):
        for post in section.get("posts", []):
            all_posts.append((post, section.get("title", "")))

    if not all_posts:
        print("⚠️ No posts found in briefing JSON.")
        return

    print(f"🔍 Enriching {len(all_posts)} posts via syndication API...")

    enriched = 0
    skipped = 0
    errors = 0

    for i, (post, section_title) in enumerate(all_posts):
        if i >= MAX_POSTS_PER_RUN:
            print(f"  ⏸️  Hit max posts limit ({MAX_POSTS_PER_RUN}), stopping.")
            break

        post_url = post.get("postUrl", "")
        tweet_id = _extract_tweet_id(post_url)
        username = post.get("authorUsername", "unknown")

        if not tweet_id:
            skipped += 1
            continue

        # Rate limiting
        if i > 0:
            time.sleep(REQUEST_DELAY_SEC)

        # Fetch syndication data
        tweet_data = _fetch_syndication(tweet_id)
        if not tweet_data:
            errors += 1
            print(f"  ⚠️ Failed to fetch @{username} ({tweet_id})")
            continue

        changes = []

        # Enrich media (only if currently empty)
        if not post.get("media"):
            media = _extract_media(tweet_data)
            if media:
                post["media"] = media
                changes.append(f"{len(media)} media")

        # Enrich quoted post (only if currently null/missing)
        if not post.get("quotedPost"):
            quoted = _extract_quoted_post(tweet_data)
            if quoted:
                post["quotedPost"] = quoted
                changes.append("quote")

        # Enrich link card (new field, only if not already present)
        if not post.get("linkCard"):
            link_card = _extract_link_card(tweet_data)
            if link_card:
                post["linkCard"] = link_card
                changes.append("linkCard")

        # Upgrade avatar URL to real CDN image
        new_avatar = _upgrade_avatar(tweet_data)
        if new_avatar:
            old_avatar = post.get("authorAvatarUrl", "")
            if not old_avatar or "unavatar.io" in old_avatar or "pbs.twimg.com" not in old_avatar:
                post["authorAvatarUrl"] = new_avatar
                changes.append("avatar")

        if changes:
            enriched += 1
            print(f"  ✅ @{username}: {', '.join(changes)}")
        else:
            skipped += 1

    # Write enriched data back
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n📊 Enrichment complete: {enriched} enriched, {skipped} unchanged, {errors} errors")


def main():
    """CLI entry point."""
    # Default to data/latest-briefing.json relative to project root
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(project_root, "data", "latest-briefing.json")

    print(f"📄 Enriching: {json_path}")
    enrich_with_syndication(json_path)


if __name__ == "__main__":
    main()
