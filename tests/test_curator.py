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
    bookmarks: int = 0,
    source: str | None = None,
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
            bookmarks=bookmarks,
        ),
        urls=urls or [],
        source=source,
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


def test_curate_briefing_builds_three_expected_sections() -> None:
    posts = [
        make_post(
            "viral-1",
            "big-author",
            "Huge launch day post.",
            likes=25_000,
            reposts=7_000,
            views=3_000_000,
            bookmarks=4_200,
            source="for_you",
        ),
        make_post(
            "top-1",
            "niche-author",
            "Claude and OpenAI coding workflows keep improving for small teams.",
            likes=400,
            reposts=80,
            views=100_000,
            replies=380,
            bookmarks=460,
            source="for_you",
        ),
        make_post(
            "follow-1",
            "tracked-person",
            "Daily update from someone I follow.",
            likes=220,
            reposts=25,
            views=45_000,
            replies=100,
            bookmarks=140,
            source="following",
        ),
    ]
    users = {
        "big-author": make_user("big-author", followers_count=900_000),
        "niche-author": make_user("niche-author", followers_count=20_000),
        "tracked-person": make_user("tracked-person", followers_count=15_000),
    }

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=["tracked-person"],
        hours=24,
        search_posts=posts,
    )

    titles = [section.title for section in briefing.sections]

    assert titles == ["VIRAL 🔥", "TOP PICKS 📌", "FOLLOWING 👥"]
    assert briefing.sections[0].items[0].post.id == "viral-1"
    assert briefing.sections[1].items[0].post.id == "top-1"
    assert briefing.sections[2].items[0].post.id == "follow-1"
    assert briefing.stats["accounts_tracked"] == len(users)


def test_following_section_falls_back_to_tracked_accounts_when_source_missing() -> None:
    posts = [
        make_post(
            "follow-fallback",
            "tracked-person",
            "Non-keyword update that should still land in following.",
            likes=55,
            reposts=5,
            views=6500,
            source=None,
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

    following = next((s for s in briefing.sections if s.title == "FOLLOWING 👥"), None)
    assert following is not None
    assert any(item.post.id == "follow-fallback" for item in following.items)


def test_curate_briefing_enforces_tab_priority_without_duplicates() -> None:
    posts = [
        make_post(
            "overlap-post",
            "author-a",
            "AI thread with huge engagement and interest keywords.",
            likes=25_000,
            reposts=4_000,
            views=2_200_000,
            replies=1_200,
            bookmarks=900,
            source="following",
        ),
        make_post(
            "top-only",
            "author-b",
            "OpenAI and Claude workflow notes for builders.",
            likes=300,
            reposts=40,
            views=50_000,
            replies=480,
            bookmarks=510,
            source="for_you",
        ),
        make_post(
            "follow-only",
            "author-c",
            "Daily update from tracked account.",
            likes=80,
            reposts=8,
            views=7_000,
            replies=20,
            bookmarks=10,
            source="following",
        ),
    ]
    users = {
        "author-a": make_user("author-a", followers_count=20_000),
        "author-b": make_user("author-b", followers_count=12_000),
        "author-c": make_user("author-c", followers_count=10_000),
    }

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=["author-a", "author-c"],
        hours=24,
        search_posts=posts,
    )

    viral = next(s for s in briefing.sections if s.title == "VIRAL 🔥")
    top_picks = next(s for s in briefing.sections if s.title == "TOP PICKS 📌")
    following = next(s for s in briefing.sections if s.title == "FOLLOWING 👥")

    assert any(item.post.id == "overlap-post" for item in viral.items)
    assert not any(item.post.id == "overlap-post" for item in top_picks.items)
    assert not any(item.post.id == "overlap-post" for item in following.items)
    assert any(item.post.id == "top-only" for item in top_picks.items)
    assert any(item.post.id == "follow-only" for item in following.items)


def test_top_picks_prioritizes_replies_and_bookmarks() -> None:
    posts = [
        make_post(
            "high-quality",
            "author-a",
            "AI builders discussing real implementation details.",
            likes=260,
            reposts=30,
            views=70_000,
            replies=500,
            bookmarks=700,
            source="for_you",
        ),
        make_post(
            "vanity",
            "author-b",
            "AI hype post.",
            likes=900,
            reposts=130,
            views=300_000,
            replies=25,
            bookmarks=20,
            source="for_you",
        ),
    ]
    users = {
        "author-a": make_user("author-a", followers_count=12_000),
        "author-b": make_user("author-b", followers_count=50_000),
    }

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=[],
        hours=24,
        search_posts=posts,
    )

    top_picks = next((s for s in briefing.sections if s.title == "TOP PICKS 📌"), None)
    assert top_picks is not None
    assert top_picks.items[0].post.id == "high-quality"
