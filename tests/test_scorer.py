from datetime import datetime, timedelta, timezone

from x_brief.models import Post, PostMetrics
from x_brief.scorer import (
    deduplicate,
    information_density_score,
    normalize_engagement_scores,
    raw_engagement_score,
    score_post,
)


def make_post(
    post_id: str,
    author_id: str = "author-1",
    text: str = "Meaningful post text for scoring coverage",
    *,
    likes: int = 10,
    reposts: int = 2,
    replies: int = 1,
    views: int = 500,
    quotes: int = 0,
    bookmarks: int = 0,
    created_at: datetime | None = None,
    is_repost: bool = False,
    urls: list[str] | None = None,
    media: list[dict] | None = None,
    is_article: bool = False,
    thread_posts: list[dict] | None = None,
) -> Post:
    return Post(
        id=post_id,
        text=text,
        author_id=author_id,
        author_username=author_id,
        author_name=author_id,
        created_at=created_at or datetime.now(timezone.utc) - timedelta(hours=1),
        metrics=PostMetrics(
            likes=likes,
            reposts=reposts,
            replies=replies,
            views=views,
            quotes=quotes,
            bookmarks=bookmarks,
        ),
        is_repost=is_repost,
        urls=urls or [],
        media=media or [],
        is_article=is_article,
        thread_posts=thread_posts or [],
    )


def test_deduplicate_skips_reposts_and_keeps_highest_scored_quote() -> None:
    quote_url = "https://x.com/original/status/999"
    repost = make_post("1", text="RT @someone: forwarded", is_repost=True)
    lower_quote = make_post("2", text=f"First take {quote_url}", likes=20, reposts=2)
    higher_quote = make_post(
        "3",
        text=f"Better take on this {quote_url}",
        likes=120,
        reposts=12,
        created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )

    unique_posts = deduplicate([repost, lower_quote, higher_quote])
    unique_ids = [post.id for post in unique_posts]

    assert repost.id not in unique_ids
    assert lower_quote.id not in unique_ids
    assert unique_ids == [higher_quote.id]


def test_raw_engagement_and_normalization() -> None:
    low = make_post("low", likes=100, reposts=10, replies=5, bookmarks=2, views=10000)
    high = make_post("high", likes=1000, reposts=100, replies=40, bookmarks=20, views=100000)

    assert raw_engagement_score(high) > raw_engagement_score(low)

    normalized = normalize_engagement_scores([low, high])
    assert normalized["high"] == 100.0
    assert 0.0 <= normalized["low"] < 100.0


def test_density_scoring_caps_at_20_and_applies_hot_take_penalty() -> None:
    dense = make_post(
        "dense",
        text="A" * 600,
        urls=["https://example.com/article/123"],
        is_article=True,
        media=[{"type": "photo"}],
        thread_posts=[{"text": "1"}, {"text": "2"}],
    )
    hot_take = make_post("hot", text="this sucks", urls=[], media=[])

    assert information_density_score(dense) == 17.0
    assert information_density_score(hot_take) == 0.0


def test_final_tab_scores_weight_density_for_for_you() -> None:
    post = make_post("p1", text="A" * 300, urls=["https://example.com"], bookmarks=10)
    engagement = 80.0

    cant_miss_score = score_post(post, engagement, tab="cant_miss")
    for_you_score = score_post(post, engagement, tab="for_you")
    following_score = score_post(post, engagement, tab="following")

    # Can't Miss now uses 0.7*engagement + 0.3*density
    # Post has 300 chars (+2 density) + URL (+3 density) = 5 density
    # 80 * 0.7 + 5 * 0.3 = 56 + 1.5 = 57.5
    assert cant_miss_score == 57.5
    assert for_you_score < cant_miss_score
    assert following_score < cant_miss_score
