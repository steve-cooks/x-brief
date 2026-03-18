"""
Syndication API enrichment for X Brief.

Fetches rich media data (photos, videos, GIFs, quote tweets, link cards)
from X's public syndication endpoint and enriches the briefing JSON.

Usage:
    python3 -m x_brief.enrichment [path_to_briefing.json]
"""

import asyncio
import html
import json
import os
import re
import sys
import urllib.request
import urllib.error
from typing import Optional


SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result?id={tweet_id}&token=x"
MAX_POSTS_PER_RUN = 30
REQUEST_DELAY_SEC = 0.5
MAX_CONCURRENT_REQUESTS = 5


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


def _fetch_fxtwitter_data(tweet_id: str) -> dict:
    """Fetch enriched tweet data from fxtwitter API.

    Returns a dict with keys:
      - text: Optional[str] — full untruncated post text (HTML-unescaped, t.co stripped)
      - community_note: Optional[dict] — {text: str, url: Optional[str]} if note exists

    Tries fxtwitter first, falls back to vxtwitter. Returns empty dict on failure.
    """
    endpoints = [
        f"https://api.fxtwitter.com/status/{tweet_id}",
        f"https://api.vxtwitter.com/status/{tweet_id}",
    ]
    result: dict = {}
    for url in endpoints:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; x-brief/1.0)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            continue

        tweet = data.get("tweet") or data.get("data", {})

        # Extract full text
        text = tweet.get("text", "")
        if text:
            text = html.unescape(text)
            text = re.sub(r'\s*https://t\.co/\S+\s*$', '', text).strip()
            if text:
                result["text"] = text

        # Extract community note if present
        cn = tweet.get("community_note")
        if cn and cn.get("text"):
            cn_text = cn["text"]
            # Resolve any t.co URL in entities to get a clean link
            cn_url: Optional[str] = None
            for entity in cn.get("entities", []):
                ref = entity.get("ref", {})
                resolved = ref.get("url", "")
                if resolved and resolved.startswith("http"):
                    cn_url = resolved
                    break
            result["community_note"] = {"text": cn_text, "url": cn_url}

        # We got data from this endpoint; stop trying others
        if result:
            return result

    return result


def _fetch_full_text_via_scrape(username: str, tweet_id: str) -> Optional[str]:
    """Fetch full post text for long posts (note_tweets) via fxtwitter API.

    Thin wrapper around _fetch_fxtwitter_data for backward compatibility.
    Returns clean, HTML-unescaped text with trailing t.co URLs stripped,
    or None on failure.
    """
    return _fetch_fxtwitter_data(tweet_id).get("text")


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

    # Resolve t.co URLs in quoted post text
    qt_text = qt.get("text", "")
    qt_entities = qt.get("entities", {})
    qt_urls = qt_entities.get("urls", [])
    for url_entity in qt_urls:
        tco = url_entity.get("url", "")
        display = url_entity.get("display_url", "")
        expanded = url_entity.get("expanded_url", "")
        if tco and display:
            qt_text = qt_text.replace(tco, display)

    # Extract link card from quoted tweet entities (for articles/links)
    qt_link_card = None
    if qt_urls:
        first_url = qt_urls[0]
        expanded = first_url.get("expanded_url", "")
        display = first_url.get("display_url", "")
        if expanded:
            domain = re.sub(r"^https?://", "", expanded).split("/")[0]
            qt_link_card = {
                "title": display,
                "description": None,
                "thumbnail": None,
                "domain": domain,
                "url": expanded,
            }

    quoted = {
        "authorName": user.get("name", ""),
        "authorUsername": screen_name,
        "authorAvatarUrl": avatar_url or None,
        "verified": verified,
        "text": qt_text,
        "postUrl": f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name and tweet_id else None,
        "media": _extract_media(qt),
    }
    if qt_link_card:
        quoted["linkCard"] = qt_link_card
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


async def enrich_with_syndication_async(json_path: str) -> None:
    """Async enrichment with bounded concurrency and request pacing."""
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"⚠️ File not found: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in: {json_path}")
        return

    all_posts: list[dict] = []
    for section in data.get("sections", []):
        for post in section.get("posts", []):
            all_posts.append(post)

    if not all_posts:
        print("⚠️ No posts found in briefing JSON.")
        return

    selected_posts = all_posts[:MAX_POSTS_PER_RUN]
    if len(all_posts) > MAX_POSTS_PER_RUN:
        print(f"  ⏸️  Hit max posts limit ({MAX_POSTS_PER_RUN}), stopping.")

    print(f"🔍 Enriching {len(selected_posts)} posts via syndication API...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    pace_lock = asyncio.Lock()
    pace_state = {"last_call": 0.0}

    async def _process(post: dict) -> tuple[str, str, int]:
        post_url = post.get("postUrl", "")
        tweet_id = _extract_tweet_id(post_url)
        username = post.get("authorUsername", "unknown")

        if not tweet_id:
            return ("skipped", username, 0)

        async with semaphore:
            async with pace_lock:
                now = asyncio.get_running_loop().time()
                wait_for = REQUEST_DELAY_SEC - (now - pace_state["last_call"])
                if wait_for > 0:
                    await asyncio.sleep(wait_for)
                pace_state["last_call"] = asyncio.get_running_loop().time()

            tweet_data = await asyncio.to_thread(_fetch_syndication, tweet_id)

        if not tweet_data:
            return ("error", username, 0)

        changes = 0

        # Always use syndication text — it's the authoritative full version.
        # Timeline scrapes are truncated previews; syndication gives the real post.
        synd_text = tweet_data.get("text", "")
        if synd_text:
            # Resolve t.co URLs to real URLs
            for entity_url in tweet_data.get("entities", {}).get("urls", []):
                tco = entity_url.get("url", "")
                display = entity_url.get("expanded_url") or entity_url.get("display_url", "")
                if tco and display:
                    synd_text = synd_text.replace(tco, display)
            # Strip any remaining trailing t.co links
            synd_text = re.sub(r'\s*https://t\.co/\S+\s*$', '', synd_text).strip()
            # Decode HTML entities (e.g. &gt; → >, &amp; → &)
            synd_text = html.unescape(synd_text)

            # Long posts (note_tweets): syndication truncates at ~280 chars.
            # Fetch full text via fxtwitter API when note_tweet key is present.
            # Also extract community notes from the same API response.
            if "note_tweet" in tweet_data:
                username_for_fetch = post.get("authorUsername", "")
                if username_for_fetch and tweet_id:
                    # Extra pacing between fxtwitter requests (200ms)
                    await asyncio.sleep(0.2)
                    fx_data = await asyncio.to_thread(
                        _fetch_fxtwitter_data, tweet_id
                    )
                    full_text = fx_data.get("text")
                    if full_text and len(full_text) > len(synd_text):
                        print(f"    📝 Full text fetched for @{username_for_fetch}/{tweet_id} ({len(full_text)} chars)")
                        synd_text = full_text
                    else:
                        print(f"    ⚠️  Full text fetch failed for @{username_for_fetch}/{tweet_id}, using syndication text")

                    # Store community note if found and not already present
                    cn = fx_data.get("community_note")
                    if cn and not post.get("communityNote"):
                        post["communityNote"] = cn
                        changes += 1
                        print(f"    📋 Community note found for @{username_for_fetch}/{tweet_id}")

            if synd_text and synd_text != post.get("text", ""):
                post["text"] = synd_text
                changes += 1
        else:
            # Syndication didn't return text — clean up existing text
            current_text = post.get("text", "")
            if "https://t.co/" in current_text:
                current_text = re.sub(r'\s*https://t\.co/\S+\s*$', '', current_text).strip()
                post["text"] = current_text

        existing_media = post.get("media") or []
        media_needs_enrichment = not existing_media or all(
            not m.get("url") for m in existing_media if isinstance(m, dict)
        )
        if media_needs_enrichment:
            media = _extract_media(tweet_data)
            if media:
                post["media"] = media
                changes += 1

        if not post.get("quotedPost"):
            quoted = _extract_quoted_post(tweet_data)
            if quoted:
                post["quotedPost"] = quoted
                changes += 1

        if not post.get("linkCard"):
            link_card = _extract_link_card(tweet_data)
            if link_card:
                post["linkCard"] = link_card
                changes += 1

        new_avatar = _upgrade_avatar(tweet_data)
        if new_avatar:
            old_avatar = post.get("authorAvatarUrl", "")
            if not old_avatar or "unavatar.io" in old_avatar or "pbs.twimg.com" not in old_avatar:
                post["authorAvatarUrl"] = new_avatar
                changes += 1

        if changes > 0:
            return ("enriched", username, changes)
        return ("skipped", username, 0)

    results = await asyncio.gather(*[_process(post) for post in selected_posts])

    enriched = 0
    skipped = 0
    errors = 0
    for status, username, change_count in results:
        if status == "enriched":
            enriched += 1
            print(f"  ✅ @{username}: {change_count} updates")
        elif status == "error":
            errors += 1
            print(f"  ⚠️ Failed to fetch @{username}")
        else:
            skipped += 1

    with open(json_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n📊 Enrichment complete: {enriched} enriched, {skipped} unchanged, {errors} errors")


def enrich_with_syndication(json_path: str) -> None:
    """Sync wrapper for CLI compatibility."""
    asyncio.run(enrich_with_syndication_async(json_path))


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
