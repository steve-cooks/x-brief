from datetime import datetime, timedelta, timezone

from x_brief.curator import curate_briefing, detect_network_amplification
from x_brief.models import Post, PostMetrics, User


def make_post(
    post_id: str,
    author_id: str,
    text: str,
    *,
    likes: int,
    reposts: int,
    views: int,
    replies: int = 2,
    quotes: int = 0,
    urls: list[str] | None = None,
    created_at: datetime | None = None,
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
        urls=urls or [],
    )


def make_user(user_id: str, followers_count: int = 10_000) -> User:
    return User(
        id=user_id,
        username=user_id,
        name=user_id,
        followers_count=followers_count,
    )


def test_detect_network_amplification_requires_three_unique_referrers() -> None:
    referenced_status = "https://x.com/source/status/999"
    posts = [
        make_post("1", "a1", f"Look at this {referenced_status}", likes=20, reposts=4, views=500),
        make_post("2", "a2", f"Also seeing this {referenced_status}", likes=21, reposts=3, views=550),
        make_post("3", "a3", f"Third mention {referenced_status}", likes=18, reposts=5, views=530),
    ]

    boosts = detect_network_amplification(posts, search_posts=[])

    assert boosts == {"999": 3.0}


def test_curate_briefing_builds_expected_sections_from_mixed_posts() -> None:
    posts = [
        make_post(
            "top-1",
            "tracked-top",
            "Detailed product launch with meaningful context for top stories readers.",
            likes=1_800,
            reposts=240,
            views=180_000,
        ),
        make_post(
            "circle-1",
            "tracked-circle",
            "Claude and OpenAI coding workflows keep improving for small teams.",
            likes=18,
            reposts=3,
            views=350,
        ),
        make_post(
            "article-1",
            "tracked-article",
            "Read this https://example.com/deep-dive",
            likes=900,
            reposts=70,
            views=75_000,
            urls=["https://example.com/deep-dive"],
        ),
        make_post(
            "worth-1",
            "tracked-worth",
            "Quiet but useful workflow tip that still deserves to show up later.",
            likes=12,
            reposts=2,
            views=240,
        ),
    ]
    search_posts = [
        make_post(
            "viral-1",
            "search-viral",
            "Huge launch day post.",
            likes=25_000,
            reposts=7_000,
            views=3_000_000,
        ),
        make_post(
            "trend-1",
            "search-trend",
            "Design systems are changing quickly this month.",
            likes=80,
            reposts=12,
            views=9_000,
        ),
    ]
    users = {
        "tracked-top": make_user("tracked-top", followers_count=40_000),
        "tracked-circle": make_user("tracked-circle", followers_count=2_500),
        "tracked-article": make_user("tracked-article", followers_count=15_000),
        "tracked-worth": make_user("tracked-worth", followers_count=1_200),
        "search-viral": make_user("search-viral", followers_count=900_000),
        "search-trend": make_user("search-trend", followers_count=30_000),
    }

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=["tracked-circle", "tracked-top", "tracked-article", "tracked-worth"],
        hours=24,
        search_posts=search_posts,
    )

    titles = [section.title for section in briefing.sections]

    assert titles == [
        "VIRAL 🔥",
        "TOP STORIES",
        "YOUR CIRCLE",
        "TRENDING IN YOUR NICHES",
        "ARTICLES & THREADS",
        "WORTH A LOOK",
    ]
    assert briefing.sections[0].items[0].post.id == "viral-1"
    assert briefing.sections[1].items[0].post.id == "top-1"
    assert briefing.sections[2].items[0].post.id == "circle-1"
    assert briefing.sections[3].items[0].post.id == "trend-1"
    assert briefing.sections[4].items[0].post.id == "article-1"
    assert briefing.sections[5].items[0].post.id == "worth-1"
    assert briefing.stats["accounts_tracked"] == len(users)


def test_curate_briefing_scan_mode_uses_tracked_accounts_for_your_circle() -> None:
    posts = [
        make_post(
            "circle-scan",
            "tracked-person",
            "Non-keyword update that should still land in circle.",
            likes=55,
            reposts=5,
            views=6500,
        )
    ]
    users = {"tracked-person": make_user("tracked-person", followers_count=8_000)}

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=["tracked-person"],
        hours=24,
        search_posts=posts,
    )

    your_circle = next((s for s in briefing.sections if s.title == "YOUR CIRCLE"), None)
    assert your_circle is not None
    assert any(item.post.id == "circle-scan" for item in your_circle.items)


def test_curate_briefing_articles_include_external_urls_from_search_posts() -> None:
    posts = [
        make_post(
            "top-regular",
            "author-a",
            "Internal post",
            likes=1000,
            reposts=120,
            views=200000,
        )
    ]
    search_posts = [
        make_post(
            "search-article",
            "author-b",
            "Long read https://example.org/essay",
            likes=700,
            reposts=60,
            views=70000,
            urls=["https://example.org/essay"],
        )
    ]
    users = {
        "author-a": make_user("author-a", followers_count=90_000),
        "author-b": make_user("author-b", followers_count=20_000),
    }

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=[],
        hours=24,
        search_posts=search_posts,
    )

    articles = next((s for s in briefing.sections if s.title == "ARTICLES & THREADS"), None)
    assert articles is not None
    assert any(item.post.id == "search-article" for item in articles.items)
