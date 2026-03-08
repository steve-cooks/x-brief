from datetime import datetime, timedelta, timezone

from x_brief.curator import cluster_posts_by_topic, curate_briefing, extract_topic_tokens
from x_brief.models import Post, PostMetrics, ThreadPost, User


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
    urls: list[str] | None = None,
    created_at: datetime | None = None,
    thread_len: int = 0,
) -> Post:
    thread_posts = [ThreadPost(id=f"{post_id}-{i}", text=f"part {i}") for i in range(thread_len)]
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
            bookmarks=bookmarks,
        ),
        urls=urls or [],
        source=source,
        thread_posts=thread_posts,
    )


def make_user(user_id: str, followers_count: int = 10_000) -> User:
    return User(
        id=user_id,
        username=user_id,
        name=user_id,
        followers_count=followers_count,
    )


def test_extract_topic_tokens_includes_urls_mentions_hashtags() -> None:
    post = make_post(
        "1",
        "a1",
        "@openai GPT-6 launch is wild #AI https://example.com/news",
        likes=100,
        reposts=10,
        views=1000,
        urls=["https://example.com/news"],
    )

    tokens, urls = extract_topic_tokens(post)

    assert "@openai" in tokens
    assert "#ai" in tokens
    assert any(t.startswith("url:https://example.com/news") for t in tokens)
    assert "https://example.com/news" in urls


def test_cluster_posts_by_topic_groups_by_shared_url_or_two_tokens() -> None:
    p1 = make_post(
        "1",
        "a1",
        "GPT release notes are out #AI https://example.com/r1",
        likes=100,
        reposts=10,
        views=1000,
    )
    p2 = make_post(
        "2",
        "a2",
        "Big GPT launch analysis #AI https://example.com/r1",
        likes=90,
        reposts=8,
        views=900,
    )
    p3 = make_post(
        "3",
        "a3",
        "Tennis training update from ATP tour",
        likes=80,
        reposts=7,
        views=800,
    )

    clusters = cluster_posts_by_topic([p1, p2, p3])
    cluster_sets = [set(p.id for p in c) for c in clusters]

    assert {"1", "2"} in cluster_sets
    assert {"3"} in cluster_sets


def test_curate_briefing_builds_all_three_tabs_with_priority() -> None:
    posts = [
        make_post(
            "cant-miss",
            "big-author",
            "Global event everyone is talking about",
            likes=25_000,
            reposts=7_000,
            views=3_000_000,
            bookmarks=2_000,
            source="for_you",
        ),
        make_post(
            "for-you-1",
            "builder-1",
            "Claude coding workflow breakdown with real details and implementation examples.",
            likes=300,
            reposts=40,
            views=50_000,
            bookmarks=100,
            source="for_you",
            thread_len=2,
        ),
        make_post(
            "for-you-dup-topic",
            "builder-2",
            "Claude coding workflow breakdown and benchmark notes.",
            likes=350,
            reposts=35,
            views=52_000,
            source="for_you",
        ),
        make_post(
            "follow-1",
            "tracked-person",
            "Daily update from following feed",
            likes=120,
            reposts=8,
            views=4_000,
            source="following",
        ),
    ]

    users = {
        "big-author": make_user("big-author", followers_count=900_000),
        "builder-1": make_user("builder-1", followers_count=20_000),
        "builder-2": make_user("builder-2", followers_count=25_000),
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

    assert [section.title for section in briefing.sections] == ["Can't Miss 🔥", "For You 📌", "Following 👥"]

    cant_miss_ids = {item.post.id for item in briefing.sections[0].items}
    for_you_ids = {item.post.id for item in briefing.sections[1].items}
    following_ids = {item.post.id for item in briefing.sections[2].items}

    assert "cant-miss" in cant_miss_ids
    assert "cant-miss" not in for_you_ids
    assert "cant-miss" not in following_ids
    assert "follow-1" in following_ids
    assert len(for_you_ids & {"for-you-1", "for-you-dup-topic"}) == 1


def test_curate_briefing_keeps_empty_tabs() -> None:
    posts = [
        make_post(
            "quiet-1",
            "person-a",
            "minor update",
            likes=5,
            reposts=0,
            views=40,
            source="for_you",
        )
    ]
    users = {"person-a": make_user("person-a")}

    briefing = curate_briefing(
        posts=posts,
        users=users,
        interests=["AI & Tech"],
        tracked_accounts=[],
        hours=24,
        search_posts=posts,
    )

    assert [section.title for section in briefing.sections] == ["Can't Miss 🔥", "For You 📌", "Following 👥"]
    assert briefing.sections[0].items == []
    assert briefing.sections[2].items == []


def test_reemergent_posts_only_allowed_in_cant_miss() -> None:
    post = make_post(
        "reemerge",
        "author-a",
        "AI update",
        likes=20_000,
        reposts=5_000,
        views=2_000_000,
        source="following",
    )

    briefing = curate_briefing(
        posts=[post],
        users={"author-a": make_user("author-a")},
        interests=["AI & Tech"],
        tracked_accounts=["author-a"],
        hours=24,
        search_posts=[post],
        reemergent_post_ids={"reemerge"},
    )

    assert {i.post.id for i in briefing.sections[0].items} == {"reemerge"}
    assert briefing.sections[1].items == []
    assert briefing.sections[2].items == []
