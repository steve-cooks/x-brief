"""Tests for x_brief.posts_store."""
import pytest

from x_brief.posts_store import append_posts, clear_posts, get_unseen, load_posts, mark_seen, save_posts


def make_post(post_id: str, seen: bool = False, tab: str = "foryou") -> dict:
    return {
        "id": post_id,
        "author": f"Author {post_id}",
        "handle": f"handle{post_id}",
        "text": f"Post text {post_id}",
        "url": f"https://x.com/handle{post_id}/status/{post_id}",
        "tab": tab,
        "scraped_at": "2026-03-27T00:00:00+00:00",
        "seen": seen,
    }


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path)


def test_load_posts_empty(data_dir):
    """load_posts returns [] when file doesn't exist."""
    assert load_posts(data_dir) == []


def test_save_and_load(data_dir):
    """save_posts + load_posts round-trips correctly."""
    posts = [make_post("1"), make_post("2")]
    save_posts(data_dir, posts)
    loaded = load_posts(data_dir)
    assert len(loaded) == 2
    assert loaded[0]["id"] == "1"


def test_append_posts_basic(data_dir):
    """append_posts adds new posts."""
    count = append_posts(data_dir, [make_post("1"), make_post("2")])
    assert count == 2
    assert len(load_posts(data_dir)) == 2


def test_append_posts_dedup(data_dir):
    """append_posts does not add duplicate IDs."""
    append_posts(data_dir, [make_post("1"), make_post("2")])
    count = append_posts(data_dir, [make_post("2"), make_post("3")])
    assert count == 1
    assert len(load_posts(data_dir)) == 3


def test_mark_seen(data_dir):
    """mark_seen sets seen=True for given IDs."""
    append_posts(data_dir, [make_post("1"), make_post("2"), make_post("3")])
    mark_seen(data_dir, ["1", "3"])
    posts = load_posts(data_dir)
    seen_ids = {post["id"] for post in posts if post["seen"]}
    assert seen_ids == {"1", "3"}
    unseen_ids = {post["id"] for post in posts if not post["seen"]}
    assert unseen_ids == {"2"}


def test_get_unseen(data_dir):
    """get_unseen returns only unseen posts."""
    append_posts(data_dir, [make_post("1"), make_post("2", seen=True), make_post("3")])
    unseen = get_unseen(data_dir)
    assert len(unseen) == 2
    assert all(not post["seen"] for post in unseen)


def test_clear_posts(data_dir):
    """clear_posts resets to empty array."""
    append_posts(data_dir, [make_post("1"), make_post("2")])
    clear_posts(data_dir)
    assert load_posts(data_dir) == []


def test_append_preserves_seen_state(data_dir):
    """append_posts does not reset seen=True on existing posts."""
    append_posts(data_dir, [make_post("1")])
    mark_seen(data_dir, ["1"])
    count = append_posts(data_dir, [make_post("1")])
    assert count == 0
    posts = load_posts(data_dir)
    assert posts[0]["seen"] is True


def test_get_unseen_empty(data_dir):
    """get_unseen returns [] when no posts or all seen."""
    assert get_unseen(data_dir) == []
    append_posts(data_dir, [make_post("1", seen=True)])
    assert get_unseen(data_dir) == []
