import asyncio
import json
import re
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

from x_brief import pipeline
from x_brief.models import Briefing, BriefingItem, BriefingSection, Post, PostMetrics, User, UserConfig


def make_post(
    post_id: str,
    author_id: str = "alice",
    *,
    text: str = "Meaningful post text for briefing coverage",
    created_at: datetime | None = None,
) -> Post:
    return Post(
        id=post_id,
        text=text,
        author_id=author_id,
        author_username=author_id,
        author_name=author_id.title(),
        created_at=created_at or datetime.now(timezone.utc) - timedelta(hours=2),
        metrics=PostMetrics(
            likes=120,
            reposts=18,
            replies=4,
            views=12_000,
            bookmarks=7,
        ),
    )


def make_briefing(post: Post) -> Briefing:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return Briefing(
        generated_at=now,
        period_start=now - timedelta(hours=24),
        period_end=now,
        sections=[
            BriefingSection(
                title="TOP STORIES",
                emoji="📌",
                items=[
                    BriefingItem(
                        post=post,
                        summary="Summary for pipeline coverage",
                        category="top_story",
                        score=42.0,
                    )
                ],
            )
        ],
        stats={"accounts_tracked": 1, "posts_analyzed": 1},
    )


def install_fake_enrichment(monkeypatch) -> list[str]:
    calls: list[str] = []
    module = types.ModuleType("x_brief.enrichment")

    def enrich_with_syndication(json_path: str) -> None:
        calls.append(json_path)

    module.enrich_with_syndication = enrich_with_syndication
    monkeypatch.setitem(sys.modules, "x_brief.enrichment", module)
    return calls


def isolate_pipeline_data_dir(monkeypatch, tmp_path: Path) -> Path:
    fake_module_file = tmp_path / "pkg" / "pipeline.py"
    monkeypatch.setattr(pipeline, "__file__", str(fake_module_file))
    return tmp_path / "data"


def test_run_briefing_from_scans_happy_path_writes_json_output(tmp_path: Path, monkeypatch) -> None:
    data_dir = isolate_pipeline_data_dir(monkeypatch, tmp_path)
    enrichment_calls = install_fake_enrichment(monkeypatch)

    post = make_post("101")
    expected_briefing = make_briefing(post)
    saved_history: dict[str, object] = {}

    def fake_curate_briefing(posts, users, interests, hours, search_posts):
        assert posts == [post]
        assert search_posts == [post]
        assert interests == ["AI"]
        assert hours == 36
        assert users["alice"].verified is True
        assert users["alice"].verified_type == "blue"
        return expected_briefing

    def fake_save_brief_history(history_path, history, new_posts) -> None:
        saved_history["history_path"] = history_path
        saved_history["history"] = history
        saved_history["post_ids"] = [item.id for item in new_posts]

    monkeypatch.setattr(
        pipeline,
        "load_user_config",
        lambda _: UserConfig(tracked_accounts=["alice"], recent_interests=["AI"]),
    )
    monkeypatch.setattr(pipeline, "load_scan_posts", lambda scan_dir, hours: ([post], {"alice": True}))
    monkeypatch.setattr(
        pipeline,
        "load_brief_history",
        lambda history_path: {"posts": {}, "last_cleanup": "2026-03-08T00:00:00+00:00"},
    )
    monkeypatch.setattr(pipeline, "filter_already_briefed", lambda posts, history: posts)
    monkeypatch.setattr(pipeline, "curate_briefing", fake_curate_briefing)
    monkeypatch.setattr(pipeline, "format_markdown", lambda briefing: "Brief output")
    monkeypatch.setattr(pipeline, "save_brief_history", fake_save_brief_history)

    output = asyncio.run(
        pipeline.run_briefing_from_scans(
            config_path=str(tmp_path / "config.json"),
            scan_dir=str(tmp_path / "timeline_scans"),
            hours=36,
        )
    )

    json_path = data_dir / "latest-briefing.json"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    exported_post = payload["sections"][0]["posts"][0]

    assert output == "Brief output"
    assert payload["sections"][0]["title"] == "TOP STORIES"
    assert payload["stats"] == {"accounts_tracked": 1, "posts_analyzed": 1}
    assert exported_post["postUrl"] == "https://x.com/alice/status/101"
    assert re.fullmatch(r"\d+[mhd]", exported_post["timestamp"])
    assert exported_post["verified"] == "blue"
    assert exported_post["createdAt"] == post.created_at.isoformat()
    assert saved_history == {
        "history_path": str(data_dir / "brief_history.json"),
        "history": {"posts": {}, "last_cleanup": "2026-03-08T00:00:00+00:00"},
        "post_ids": ["101"],
    }
    assert enrichment_calls == [str(json_path)]


def test_run_briefing_from_scans_returns_all_posts_already_briefed(tmp_path: Path, monkeypatch) -> None:
    data_dir = isolate_pipeline_data_dir(monkeypatch, tmp_path)
    enrichment_calls = install_fake_enrichment(monkeypatch)

    post = make_post("101")
    monkeypatch.setattr(
        pipeline,
        "load_user_config",
        lambda _: UserConfig(tracked_accounts=["alice"], recent_interests=["AI"]),
    )
    monkeypatch.setattr(pipeline, "load_scan_posts", lambda scan_dir, hours: ([post], {"alice": True}))
    monkeypatch.setattr(
        pipeline,
        "load_brief_history",
        lambda history_path: {"posts": {"101": {}}, "last_cleanup": "2026-03-08T00:00:00+00:00"},
    )
    monkeypatch.setattr(pipeline, "filter_already_briefed", lambda posts, history: [])
    monkeypatch.setattr(
        pipeline,
        "curate_briefing",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("curate_briefing should not run")),
    )
    monkeypatch.setattr(
        pipeline,
        "save_brief_history",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("save_brief_history should not run")),
    )

    output = asyncio.run(
        pipeline.run_briefing_from_scans(
            config_path=str(tmp_path / "config.json"),
            scan_dir=str(tmp_path / "timeline_scans"),
        )
    )

    assert output == "All posts already briefed."
    assert not (data_dir / "latest-briefing.json").exists()
    assert enrichment_calls == []


def test_run_briefing_from_scans_skip_dedup_keeps_posts_and_skips_history_save(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = isolate_pipeline_data_dir(monkeypatch, tmp_path)
    enrichment_calls = install_fake_enrichment(monkeypatch)

    all_posts = [make_post("101"), make_post("202", author_id="bob")]
    expected_briefing = make_briefing(all_posts[0])
    save_calls: list[tuple] = []

    def fake_curate_briefing(posts, users, interests, hours, search_posts):
        assert posts == all_posts
        assert search_posts == all_posts
        assert set(users) == {"alice", "bob"}
        return expected_briefing

    monkeypatch.setattr(
        pipeline,
        "load_user_config",
        lambda _: UserConfig(tracked_accounts=["alice", "bob"], recent_interests=["AI"]),
    )
    monkeypatch.setattr(
        pipeline,
        "load_scan_posts",
        lambda scan_dir, hours: (all_posts, {"alice": True, "bob": False}),
    )
    monkeypatch.setattr(
        pipeline,
        "load_brief_history",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("load_brief_history should not run")),
    )
    monkeypatch.setattr(
        pipeline,
        "filter_already_briefed",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("filter_already_briefed should not run")),
    )
    monkeypatch.setattr(pipeline, "curate_briefing", fake_curate_briefing)
    monkeypatch.setattr(pipeline, "format_markdown", lambda briefing: "Web output")
    monkeypatch.setattr(pipeline, "save_brief_history", lambda *args, **kwargs: save_calls.append(args))

    output = asyncio.run(
        pipeline.run_briefing_from_scans(
            config_path=str(tmp_path / "config.json"),
            scan_dir=str(tmp_path / "timeline_scans"),
            skip_dedup=True,
        )
    )

    assert output == "Web output"
    assert (data_dir / "latest-briefing.json").exists()
    assert save_calls == []
    assert enrichment_calls == [str(data_dir / "latest-briefing.json")]


def test_run_briefing_from_scans_returns_no_posts_when_scan_data_empty(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = isolate_pipeline_data_dir(monkeypatch, tmp_path)
    enrichment_calls = install_fake_enrichment(monkeypatch)

    monkeypatch.setattr(
        pipeline,
        "load_user_config",
        lambda _: UserConfig(tracked_accounts=["alice"], recent_interests=["AI"]),
    )
    monkeypatch.setattr(pipeline, "load_scan_posts", lambda scan_dir, hours: ([], {}))
    monkeypatch.setattr(
        pipeline,
        "curate_briefing",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("curate_briefing should not run")),
    )
    monkeypatch.setattr(
        pipeline,
        "save_brief_history",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("save_brief_history should not run")),
    )

    output = asyncio.run(
        pipeline.run_briefing_from_scans(
            config_path=str(tmp_path / "config.json"),
            scan_dir=str(tmp_path / "timeline_scans"),
        )
    )

    assert output == "No posts found in scan data."
    assert not (data_dir / "latest-briefing.json").exists()
    assert enrichment_calls == []
