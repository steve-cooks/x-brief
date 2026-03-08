"""Content scoring and deduplication for X Brief."""

import re
from typing import Literal

from .models import Post


def deduplicate(posts: list[Post], section: str = "general") -> list[Post]:
    """
    Remove exact duplicates and group reposts/quotes.
    Returns unique posts, preferring originals over reposts.

    Args:
        posts: List of posts to deduplicate
        section: Section name for filtering rules ("for_you" or "general")
    """
    seen_ids = set()
    seen_text = set()
    quote_originals = {}  # Map quoted post ID to best quote-tweet
    unique_posts = []

    # Sort to process original posts before reposts
    sorted_posts = sorted(posts, key=lambda p: (p.is_repost, p.created_at))

    for post in sorted_posts:
        if post.id in seen_ids:
            continue

        # Skip reposts that are just "RT @..." format
        if post.is_repost or post.text.strip().startswith("RT @"):
            continue

        # For For You section: skip very short posts (just emojis/lol)
        if section == "for_you":
            cleaned_text = re.sub(r"https?://\S+", "", post.text)
            cleaned_text = re.sub(r"@\w+", "", cleaned_text)
            cleaned_text = cleaned_text.strip()
            if len(cleaned_text) < 10:
                continue

        if post.text in seen_text:
            continue

        # Group quote-tweets of the same original (keep highest scored one)
        quoted_match = re.search(r"https://(?:twitter|x)\.com/\w+/status/(\d+)", post.text)
        if quoted_match:
            quoted_id = quoted_match.group(1)
            current_score = raw_engagement_score(post)

            if quoted_id in quote_originals:
                existing_post, existing_score = quote_originals[quoted_id]
                if current_score > existing_score:
                    quote_originals[quoted_id] = (post, current_score)
                    if existing_post in unique_posts:
                        unique_posts.remove(existing_post)
                        seen_ids.discard(existing_post.id)
                        seen_text.discard(existing_post.text)
                else:
                    continue
            else:
                quote_originals[quoted_id] = (post, current_score)

        seen_ids.add(post.id)
        seen_text.add(post.text)
        unique_posts.append(post)

    return unique_posts


def raw_engagement_score(post: Post) -> float:
    """Raw engagement formula from the v2 spec."""
    m = post.metrics
    return (
        (m.likes * 1.0)
        + (m.reposts * 2.0)
        + (m.replies * 1.5)
        + (m.bookmarks * 3.0)
        + (m.views * 0.01)
    )


def normalize_engagement_scores(posts: list[Post]) -> dict[str, float]:
    """Normalize raw engagement scores to 0-100 within the current batch."""
    if not posts:
        return {}

    raw_scores = {post.id: raw_engagement_score(post) for post in posts}
    max_raw = max(raw_scores.values(), default=0.0)
    if max_raw <= 0:
        return {post.id: 0.0 for post in posts}

    return {post_id: min(100.0, (score / max_raw) * 100.0) for post_id, score in raw_scores.items()}


def information_density_score(post: Post) -> float:
    """Compute information density score on a 0-20 scale."""
    density = 0.0
    text = post.text or ""
    text_len = len(text.strip())
    has_link = bool(post.urls)
    has_media = bool(post.media)
    is_thread = len(post.thread_posts) >= 2

    if has_link:
        density += 3
    if post.is_article or (post.article_url and "/article/" in post.article_url):
        density += 5
    if is_thread:
        density += 4
    if text_len > 200:
        density += 2
    if text_len > 500:
        density += 2
    if has_media:
        density += 1
    if text_len < 100 and not has_link and not has_media:
        density -= 2

    return max(0.0, min(20.0, density))


def score_post(
    post: Post,
    normalized_engagement: float,
    tab: Literal["cant_miss", "for_you", "following"],
) -> float:
    """Final per-tab score from normalized engagement + density."""
    if tab == "cant_miss":
        return normalized_engagement

    density = information_density_score(post)
    if tab == "for_you":
        return (normalized_engagement * 0.4) + (density * 0.6)

    # following
    return (normalized_engagement * 0.5) + (density * 0.5)


def rank_posts(posts: list[Post]) -> list[Post]:
    """Rank posts by normalized engagement score (descending)."""
    normalized = normalize_engagement_scores(posts)
    return sorted(posts, key=lambda p: normalized.get(p.id, 0.0), reverse=True)
