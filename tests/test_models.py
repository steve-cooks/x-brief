from datetime import datetime, timezone

from x_brief.models import Briefing, BriefingSection, Post, PostMedia, PostMetrics, QuotedPost, UserConfig


def test_post_media_default_variants_are_not_shared() -> None:
    first = PostMedia(type="video")
    second = PostMedia(type="video")

    first.variants.append({"bitrate": 256_000})

    assert first.variants == [{"bitrate": 256_000}]
    assert second.variants == []


def test_post_supports_nested_quoted_post_data() -> None:
    post = Post(
        id="1",
        text="Quoting a post",
        author_id="author-1",
        author_username="author-1",
        author_name="Author 1",
        created_at=datetime.now(timezone.utc),
        metrics=PostMetrics(likes=12, reposts=3, replies=1, views=450),
        quoted_post=QuotedPost(
            id="quoted-1",
            text="Original post text",
            author_username="source",
            author_name="Source",
            metrics=PostMetrics(likes=300, reposts=40, replies=5, views=9_000),
            post_url="https://x.com/source/status/quoted-1",
        ),
    )

    dumped = post.model_dump()

    assert dumped["quoted_post"]["author_username"] == "source"
    assert dumped["quoted_post"]["metrics"]["likes"] == 300


def test_user_config_defaults_match_current_config_shape() -> None:
    config = UserConfig()

    assert config.x_handle is None
    assert config.tracked_accounts == []
    assert config.recent_interests == []
    assert config.delivery == {}
    assert config.briefing_schedule == "daily"


def test_briefing_section_defaults_to_empty_items() -> None:
    briefing = Briefing(
        generated_at=datetime.now(timezone.utc),
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
        sections=[BriefingSection(title="TOP PICKS 📌", emoji="📌")],
    )

    assert briefing.sections[0].items == []
