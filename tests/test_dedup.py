import json
from datetime import datetime, timedelta, timezone

from x_brief import dedup
from x_brief.dedup import cleanup_history, filter_already_briefed, load_brief_history, save_brief_history
from x_brief.models import Post, PostMetrics
from x_brief.scorer import raw_engagement_score


def make_post(
    post_id: str,
    author_username: str = "author",
    *,
    likes: int = 10,
    reposts: int = 1,
    replies: int = 0,
    views: int = 100,
    bookmarks: int = 0,
) -> Post:
    return Post(
        id=post_id,
        text=f"Post {post_id}",
        author_id=author_username,
        author_username=author_username,
        author_name=author_username,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        metrics=PostMetrics(likes=likes, reposts=reposts, replies=replies, views=views, bookmarks=bookmarks),
    )


def test_load_brief_history_returns_default_shape_for_missing_file(tmp_path) -> None:
    history = load_brief_history(str(tmp_path / "brief-history.json"))

    assert history["posts"] == {}
    assert "last_cleanup" in history


def test_save_history_and_filter_already_briefed_round_trip(tmp_path) -> None:
    history_path = tmp_path / "brief-history.json"
    history = load_brief_history(str(history_path))
    first_post = make_post("1", author_username="alice")
    second_post = make_post("2", author_username="bob")

    save_brief_history(str(history_path), history, [first_post], max_age_hours=48)

    saved_history = json.loads(history_path.read_text())
    remaining_posts, reemergent = filter_already_briefed([first_post, second_post], saved_history, max_age_hours=48)

    assert "1" in saved_history["posts"]
    assert saved_history["posts"]["1"]["url"] == "https://x.com/alice/status/1"
    assert saved_history["posts"]["1"]["engagement_raw"] == raw_engagement_score(first_post)
    assert [post.id for post in remaining_posts] == ["2"]
    assert reemergent == set()


def test_filter_already_briefed_only_blocks_recent_window() -> None:
    now = datetime.now(timezone.utc)
    history = {
        "posts": {
            "old": {"briefed_at": (now - timedelta(hours=72)).isoformat(), "engagement_raw": 100},
            "fresh": {"briefed_at": (now - timedelta(hours=4)).isoformat(), "engagement_raw": 100},
        },
        "last_cleanup": now.isoformat(),
    }

    posts = [make_post("old"), make_post("fresh"), make_post("new")]
    remaining, _ = filter_already_briefed(posts, history, max_age_hours=48)

    assert {p.id for p in remaining} == {"old", "new"}


def test_reemergence_allows_return_when_engagement_10x_and_cant_miss() -> None:
    now = datetime.now(timezone.utc)
    post = make_post("boom", likes=20_000, reposts=6_000, views=1_500_000)
    history = {
        "posts": {
            "boom": {
                "briefed_at": (now - timedelta(hours=3)).isoformat(),
                "engagement_raw": raw_engagement_score(make_post("old-boom", likes=100, reposts=10, views=5_000)),
            }
        },
        "last_cleanup": now.isoformat(),
    }

    remaining, reemergent = filter_already_briefed([post], history, max_age_hours=48)

    assert [p.id for p in remaining] == ["boom"]
    assert reemergent == {"boom"}


def test_cleanup_history_prunes_entries_older_than_cutoff() -> None:
    now = datetime.now(timezone.utc)
    history = {
        "posts": {
            "old": {"briefed_at": (now - timedelta(days=8)).isoformat()},
            "fresh": {"briefed_at": (now - timedelta(hours=12)).isoformat()},
        },
        "last_cleanup": now.isoformat(),
    }

    cleaned = cleanup_history(history, max_age_hours=48)

    assert set(cleaned["posts"]) == {"fresh"}
    assert "last_cleanup" in cleaned


def test_save_brief_history_skips_cleanup_when_last_cleanup_recent(tmp_path, monkeypatch) -> None:
    history_path = tmp_path / "brief-history.json"
    history = {
        "posts": {},
        "last_cleanup": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
    }

    calls: list[bool] = []

    def fail_if_called(*args, **kwargs):
        calls.append(True)
        return history

    monkeypatch.setattr(dedup, "cleanup_history", fail_if_called)
    save_brief_history(str(history_path), history, [make_post("3", author_username="charlie")], max_age_hours=48)

    assert calls == []


def test_save_brief_history_runs_cleanup_when_last_cleanup_stale(tmp_path, monkeypatch) -> None:
    history_path = tmp_path / "brief-history.json"
    history = {
        "posts": {},
        "last_cleanup": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat(),
    }

    calls: list[bool] = []

    def mark_called(current_history, max_age_hours=48):
        calls.append(True)
        return current_history

    monkeypatch.setattr(dedup, "cleanup_history", mark_called)
    save_brief_history(str(history_path), history, [make_post("4", author_username="dana")], max_age_hours=48)

    assert calls == [True]
