import json
from datetime import datetime, timedelta, timezone

from x_brief.dedup import cleanup_history, filter_already_briefed, load_brief_history, save_brief_history
from x_brief.models import Post, PostMetrics


def make_post(post_id: str, author_username: str = "author") -> Post:
    return Post(
        id=post_id,
        text=f"Post {post_id}",
        author_id=author_username,
        author_username=author_username,
        author_name=author_username,
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        metrics=PostMetrics(likes=10, reposts=1, replies=0, views=100),
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

    save_brief_history(str(history_path), history, [first_post])

    saved_history = json.loads(history_path.read_text())
    remaining_posts = filter_already_briefed([first_post, second_post], saved_history)

    assert "1" in saved_history["posts"]
    assert saved_history["posts"]["1"]["url"] == "https://x.com/alice/status/1"
    assert [post.id for post in remaining_posts] == ["2"]


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
