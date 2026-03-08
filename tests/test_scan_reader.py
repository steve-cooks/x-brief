import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from x_brief.scan_reader import build_users_from_posts, load_scan_posts


def make_scan_post(
    post_id: str | None,
    author: str,
    *,
    text: str = "Useful scan post text",
    posted_at: str = "2h ago",
    verified: bool | None = None,
    avatar_url: str | None = None,
    url: str | None = None,
    metrics: dict | None = None,
) -> dict:
    username = author.lstrip("@")
    data = {
        "author": author,
        "author_name": username.title(),
        "text": text,
        "posted_at": posted_at,
        "url": url or (f"https://x.com/{username}/status/{post_id}" if post_id else ""),
        "metrics": metrics or {
            "likes": "10",
            "reposts": "2",
            "replies": "1",
            "views": "200",
        },
    }
    if verified is not None:
        data["verified"] = verified
    if avatar_url is not None:
        data["avatar_url"] = avatar_url
    return data


def write_scan_file(
    scan_dir: Path,
    filename: str,
    *,
    scan_time: datetime,
    posts: list[dict],
) -> None:
    scan_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "scan_time": scan_time.isoformat().replace("+00:00", "Z"),
        "posts": posts,
    }
    (scan_dir / filename).write_text(json.dumps(payload), encoding="utf-8")


def test_load_scan_posts_reads_recent_scans_deduplicates_and_filters_invalid_urls(tmp_path: Path) -> None:
    scan_dir = tmp_path / "timeline_scans"
    now = datetime.now(timezone.utc).replace(microsecond=0)

    write_scan_file(
        scan_dir,
        "2026-03-08-09.json",
        scan_time=now - timedelta(hours=2),
        posts=[
            make_scan_post(
                "100",
                "@alice",
                posted_at="2h ago",
                verified=True,
                metrics={
                    "likes": "1.2K",
                    "reposts": "45",
                    "replies": "12",
                    "views": "3M",
                },
            ),
            make_scan_post(
                None,
                "@invalid",
                url="https://x.com/invalid",
                posted_at="1h ago",
            ),
        ],
    )
    write_scan_file(
        scan_dir,
        "2026-03-08-10.json",
        scan_time=now - timedelta(hours=1),
        posts=[
            make_scan_post(
                "100",
                "@alice",
                text="Duplicate later scan should not replace the first post",
                posted_at="30m ago",
                verified=True,
            ),
            make_scan_post(
                "200",
                "@bob",
                posted_at="2026-03-07T10:15:00Z",
                verified=False,
            ),
        ],
    )
    write_scan_file(
        scan_dir,
        "2026-03-05-10.json",
        scan_time=now - timedelta(hours=72),
        posts=[make_scan_post("300", "@carol", posted_at="15m ago", verified=True)],
    )

    posts, scan_verified = load_scan_posts(str(scan_dir), hours=24)

    posts_by_id = {post.id: post for post in posts}

    assert set(posts_by_id) == {"100", "200"}
    assert posts_by_id["100"].text == "Useful scan post text"
    assert posts_by_id["100"].metrics.likes == 1_200
    assert posts_by_id["100"].metrics.views == 3_000_000
    assert posts_by_id["100"].created_at == now - timedelta(hours=4)
    assert posts_by_id["200"].created_at == datetime(2026, 3, 7, 10, 15, tzinfo=timezone.utc)
    assert scan_verified == {"alice": True, "bob": False}


def test_load_scan_posts_keeps_avatar_from_scan_data(tmp_path: Path) -> None:
    scan_dir = tmp_path / "timeline_scans"
    scan_time = datetime.now(timezone.utc).replace(microsecond=0)
    avatar = "https://pbs.twimg.com/profile_images/example/alice_normal.jpg"

    write_scan_file(
        scan_dir,
        "2026-03-08-11.json",
        scan_time=scan_time,
        posts=[
            make_scan_post("101", "@alice", posted_at="30m ago", avatar_url=avatar, verified=True),
        ],
    )

    posts, scan_verified = load_scan_posts(str(scan_dir), hours=24)
    users = build_users_from_posts(posts, scan_verified=scan_verified)

    assert posts[0].author_avatar_url == avatar
    assert users["alice"].profile_image_url == avatar


def test_load_scan_posts_parses_relative_and_absolute_posted_at_values(tmp_path: Path) -> None:
    scan_dir = tmp_path / "timeline_scans"
    scan_time = datetime.now(timezone.utc).replace(microsecond=0)

    write_scan_file(
        scan_dir,
        "2026-03-08-11.json",
        scan_time=scan_time,
        posts=[
            make_scan_post("101", "@delta", posted_at="2h ago"),
            make_scan_post("102", "@echo", posted_at="2026-03-07"),
            make_scan_post("103", "@foxtrot", posted_at="2026-03-07T08:30:00Z"),
        ],
    )

    posts, _ = load_scan_posts(str(scan_dir), hours=24)

    posts_by_id = {post.id: post for post in posts}

    assert posts_by_id["101"].created_at == scan_time - timedelta(hours=2)
    assert posts_by_id["102"].created_at == datetime(2026, 3, 7, 0, 0, tzinfo=timezone.utc)
    assert posts_by_id["103"].created_at == datetime(2026, 3, 7, 8, 30, tzinfo=timezone.utc)


def test_load_scan_posts_raises_on_invalid_json(tmp_path: Path) -> None:
    scan_dir = tmp_path / "timeline_scans"
    scan_dir.mkdir(parents=True)
    (scan_dir / "2026-03-08-11.json").write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSON in scan file"):
        load_scan_posts(str(scan_dir), hours=24)
