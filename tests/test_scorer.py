from datetime import datetime, timedelta, timezone

from x_brief.models import Post, PostMetrics, User
from x_brief.scorer import deduplicate, get_viral_multiplier, is_mega_viral, rank_posts, score_post


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
    created_at: datetime | None = None,
    is_repost: bool = False,
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
        ),
        is_repost=is_repost,
    )


def make_user(user_id: str, followers_count: int) -> User:
    return User(
        id=user_id,
        username=user_id,
        name=user_id,
        followers_count=followers_count,
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


def test_deduplicate_top_stories_filters_too_short_posts() -> None:
    short_post = make_post("1", text="👀 https://example.com")
    meaningful_post = make_post("2", text="This post has enough real text to survive top stories filtering.")

    unique_posts = deduplicate([short_post, meaningful_post], section="top_stories")

    assert [post.id for post in unique_posts] == ["2"]


def test_score_post_applies_mega_viral_boost_for_older_posts() -> None:
    older_viral_post = make_post(
        "1",
        likes=20_000,
        reposts=6_000,
        views=2_500_000,
        created_at=datetime.now(timezone.utc) - timedelta(hours=40),
    )
    older_normal_post = make_post(
        "2",
        likes=800,
        reposts=60,
        views=250_000,
        created_at=datetime.now(timezone.utc) - timedelta(hours=40),
    )

    assert is_mega_viral(older_viral_post) is True
    assert get_viral_multiplier(older_viral_post) == 5.0
    assert score_post(older_viral_post, followers_count=1_000_000) > score_post(
        older_normal_post, followers_count=1_000_000
    )


def test_rank_posts_prefers_breakout_from_smaller_account() -> None:
    small_account_post = make_post("1", author_id="small", likes=900, reposts=140, views=120_000)
    large_account_post = make_post("2", author_id="large", likes=900, reposts=140, views=120_000)

    ranked = rank_posts(
        [large_account_post, small_account_post],
        users_map={
            "small": make_user("small", followers_count=800),
            "large": make_user("large", followers_count=2_000_000),
        },
    )

    assert [post.id for post in ranked] == ["1", "2"]
