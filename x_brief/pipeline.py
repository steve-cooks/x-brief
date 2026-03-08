"""End-to-end briefing pipeline for X Brief."""
import argparse
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from x_brief.config import load_user_config
from x_brief.curator import curate_briefing
from x_brief.scan_reader import load_scan_posts, build_users_from_posts
from x_brief.dedup import load_brief_history, filter_already_briefed, save_brief_history


def _format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,}"


def format_markdown(briefing) -> str:
    """Render a compact Telegram-friendly markdown briefing."""
    period_hours = int((briefing.period_end - briefing.period_start).total_seconds() / 3600)
    header = f"{briefing.generated_at.strftime('%A, %B %d')} (past {period_hours}h)"
    lines = [f"🌅 **𝕏 Brief** — {header}", ""]

    for section in briefing.sections:
        lines.extend(["────────────────────", "", f"{section.emoji} **{section.title}**", ""])
        for item in section.items:
            post = item.post
            metrics = post.metrics
            engagement = []
            if metrics.likes > 0:
                engagement.append(f"❤️ {_format_number(metrics.likes)}")
            if metrics.reposts > 0:
                engagement.append(f"🔁 {_format_number(metrics.reposts)}")
            if metrics.views > 0:
                engagement.append(f"👁 {_format_number(metrics.views)}")

            lines.append(f"**{post.author_name}** · [@{post.author_username}](https://x.com/{post.author_username})")
            lines.append(item.summary)
            if engagement:
                lines.append(" ".join(engagement))
            lines.append(f"[→ View post](https://x.com/{post.author_username}/status/{post.id})")
            lines.append("")

    lines.extend(["────────────────────", "", "📊 **Stats**"])
    for key, value in briefing.stats.items():
        lines.append(f"• {key}: {value}")

    lines.extend(["", f"_Generated {briefing.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_"])
    return "\n".join(lines)


def _resolve_data_dir() -> Path:
    """Resolve where generated briefing artifacts should be written."""
    env_data_dir = os.environ.get("X_BRIEF_DATA_DIR")
    data_dir = Path(env_data_dir) if env_data_dir else Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def _utc_now_iso() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _read_last_success(status_path: Path) -> str | None:
    """Read the previous successful pipeline timestamp if available."""
    if not status_path.exists():
        return None
    try:
        with open(status_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("last_success")
    except Exception:
        return None


def _write_pipeline_status(status_path: Path, payload: dict) -> None:
    """
    Persist pipeline health status for frontend/API consumption.

    Frontend API hint: expose `/api/pipeline-status` that reads this file.
    """
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


async def run_briefing_from_scans(
    config_path: str,
    scan_dir: str = None,
    hours: int = 36,
    skip_dedup: bool = False,
) -> str:
    """
    Pipeline that reads timeline scan data and generates a briefing.

    Args:
        config_path: Path to user config (for interests, tracked accounts)
        scan_dir: Directory with scan JSONs (default: X_BRIEF_SCAN_DIR or ./timeline_scans/)
        hours: Only include posts from scans within the last N hours (default 48)
    """
    if scan_dir is None:
        scan_dir = os.environ.get("X_BRIEF_SCAN_DIR", "./timeline_scans/")

    data_dir = _resolve_data_dir()
    history_path = str(data_dir / "brief_history.json")
    status_path = data_dir / "pipeline-status.json"
    last_attempt = _utc_now_iso()

    def fail_pipeline(error_message: str) -> str:
        status_payload = {
            "status": "error",
            "error": error_message,
            "last_success": _read_last_success(status_path),
            "last_attempt": last_attempt,
        }
        _write_pipeline_status(status_path, status_payload)
        print(f"❌ Pipeline error: {error_message}")
        return error_message

    try:
        scan_path = Path(scan_dir).expanduser()
        if not scan_path.exists():
            return fail_pipeline(f"Scan directory not found: {scan_path}")

        scan_files = list(scan_path.glob("*.json"))
        if not scan_files:
            return fail_pipeline(f"No scan files found in {scan_path}")

        user_config = load_user_config(config_path)
        interests = user_config.recent_interests or [
            "AI", "Machine Learning", "LLMs", "Claude", "OpenAI", "Cursor",
            "OpenClaw", "Startups", "Building", "SaaS", "Design", "Trading bots",
        ]
        print(f"📋 Config loaded. Interests: {', '.join(interests)}")

        print(f"📂 Reading scans from {scan_dir} (last {hours}h)...")
        all_posts, scan_verified = load_scan_posts(scan_dir, hours=hours)

        if not all_posts:
            return fail_pipeline("No posts found in scan data.")

        if skip_dedup:
            print("⏭️  Skipping dedup (web app mode)")
            fresh_posts = all_posts
            history = None
        else:
            print("🔄 Checking brief history for duplicates...")
            history = load_brief_history(history_path)
            fresh_posts = filter_already_briefed(all_posts, history)

            if not fresh_posts:
                return fail_pipeline("Zero posts after processing (all scanned posts already briefed).")

        users_map = build_users_from_posts(fresh_posts, scan_verified=scan_verified)
        print(f"👥 Built {len(users_map)} user profiles from scan data")

        print("🎯 Curating briefing...")
        briefing = curate_briefing(
            posts=fresh_posts,
            users=users_map,
            interests=interests,
            tracked_accounts=user_config.tracked_accounts,
            hours=hours,
            search_posts=fresh_posts,  # Treat all scan posts as potential search results too
        )

        if not briefing.sections:
            return fail_pipeline("Zero sections produced by curator.")

        output = format_markdown(briefing)
        print(f"\n{'='*60}")
        print(output)
        print(f"{'='*60}")

        json_data = export_briefing_json(briefing, users_map, hours)
        json_path = str(data_dir / "latest-briefing.json")
        with open(json_path, "w") as f:
            json.dump(json_data, f, indent=2, default=str)
        print(f"📄 JSON exported to {json_path}")

        from x_brief.enrichment import enrich_with_syndication_async
        print("🎨 Enriching with syndication API...")
        await enrich_with_syndication_async(json_path)

        if not skip_dedup and history is not None:
            briefed_posts = []
            for section in briefing.sections:
                for item in section.items:
                    briefed_posts.append(item.post)
            save_brief_history(history_path, history, briefed_posts)

        status_payload = {
            "status": "ok",
            "last_success": _utc_now_iso(),
            "posts_processed": len(fresh_posts),
            "sections": len(briefing.sections),
        }
        _write_pipeline_status(status_path, status_payload)

        return output
    except Exception as exc:
        return fail_pipeline(str(exc) or exc.__class__.__name__)


def export_briefing_json(briefing, users_map: dict, hours: int) -> dict:
    """Export briefing as JSON for the web frontend."""
    sections = []
    for section in briefing.sections:
        posts = []
        for item in section.items:
            post = item.post
            user = users_map.get(post.author_id)
            avatar_url = user.profile_image_url if user else None
            # Get higher res avatar (replace _normal with _bigger or _400x400)
            if avatar_url:
                avatar_url = avatar_url.replace("_normal", "_400x400")

            verified_type = user.verified_type if user else None

            # Format media for frontend
            media_items = []
            for media in post.media:
                media_item = {
                    "type": media.type,
                    "url": media.url,
                    "preview_image_url": media.preview_image_url,
                    "video_url": media.video_url,
                    "alt_text": media.alt_text,
                }
                media_items.append(media_item)

            # Strip "(pinned)" artifacts from scraped author data
            clean_author_name = (post.author_name or (user.name if user else post.author_username) or "").replace(" (pinned)", "")
            clean_author_username = (post.author_username or (user.username if user else "unknown") or "").replace(" (pinned)", "")
            clean_avatar_url = avatar_url.replace(" (pinned)", "") if avatar_url else None
            # Fallback to unavatar.io if no avatar URL from scraper
            if not clean_avatar_url and clean_author_username:
                clean_avatar_url = f"https://unavatar.io/twitter/{clean_author_username}"

            # Build quoted post data if present
            quoted_post_data = None
            if post.quoted_post:
                qp = post.quoted_post
                quoted_post_data = {
                    "authorName": qp.author_name,
                    "authorUsername": qp.author_username,
                    "text": qp.text,
                    "postUrl": qp.post_url,
                }
                if qp.metrics:
                    quoted_post_data["metrics"] = {
                        "likes": qp.metrics.likes,
                        "reposts": qp.metrics.reposts,
                        "views": qp.metrics.views,
                        "replies": qp.metrics.replies,
                        "bookmarks": qp.metrics.bookmarks,
                    }

            posts.append({
                "authorName": clean_author_name,
                "authorUsername": clean_author_username,
                "authorAvatarUrl": clean_avatar_url,
                "verified": verified_type,
                "text": post.text,
                "media": media_items,
                "quotedPost": quoted_post_data,
                "metrics": {
                    "likes": post.metrics.likes,
                    "reposts": post.metrics.reposts,
                    "views": post.metrics.views,
                    "replies": post.metrics.replies,
                    "bookmarks": post.metrics.bookmarks,
                },
                "postUrl": f"https://x.com/{clean_author_username}/status/{post.id}",
                "timestamp": _relative_time(post.created_at),
                "createdAt": post.created_at.isoformat() if post.created_at else None,
                "category": item.category,
            })
        sections.append({
            "title": section.title,
            "emoji": section.emoji,
            "posts": posts,
        })

    return {
        "generated_at": briefing.generated_at.isoformat(),
        "period_hours": hours,
        "sections": sections,
        "stats": briefing.stats,
    }


def enrich_briefing_json(json_path: str) -> None:
    """
    Enrich an existing briefing JSON with missing avatar URLs.

    Uses unavatar.io to fetch real Twitter avatars without API access.
    Can be called after the scan pipeline generates the JSON.

    Args:
        json_path: Path to the latest-briefing.json file
    """
    import json as json_mod

    # Read existing JSON
    try:
        with open(json_path, "r") as f:
            data = json_mod.load(f)
    except FileNotFoundError:
        print(f"⚠️ File not found: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"⚠️ Invalid JSON in: {json_path}")
        return

    enriched_count = 0

    # Process each section
    for section in data.get("sections", []):
        for post in section.get("posts", []):
            # Skip if avatar already present and valid
            current_avatar = post.get("authorAvatarUrl")
            if current_avatar and "pbs.twimg.com" in current_avatar:
                continue

            # Get username and construct unavatar URL
            username = post.get("authorUsername")
            if username:
                # unavatar.io provides real Twitter avatars without API
                avatar_url = f"https://unavatar.io/twitter/{username}"
                post["authorAvatarUrl"] = avatar_url
                enriched_count += 1

    # Write back enriched JSON
    with open(json_path, "w") as f:
        json_mod.dump(data, f, indent=2, default=str)

    print(f"✅ Enriched {enriched_count} posts with avatar URLs in {json_path}")


def _relative_time(dt) -> str:
    """Convert datetime to relative time string."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    diff = now - dt
    hours = diff.total_seconds() / 3600
    if hours < 1:
        return f"{int(diff.total_seconds() / 60)}m"
    elif hours < 24:
        return f"{int(hours)}h"
    else:
        return f"{int(hours / 24)}d"


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for the scan-only pipeline."""
    parser = argparse.ArgumentParser(
        prog="python -m x_brief.pipeline",
        description="Generate an X Brief briefing from browser timeline scans.",
    )
    parser.add_argument("config_path", help="Path to the user config JSON file")
    parser.add_argument("--hours", type=int, default=36, help="Only include scans from the last N hours")
    parser.add_argument("--scan-dir", help="Override the scan input directory")
    parser.add_argument("--skip-dedup", action="store_true", help="Ignore brief_history.json and include already-briefed posts")
    parser.add_argument(
        "--from-scans",
        action="store_true",
        help="Compatibility flag; scan mode is the only supported mode.",
    )
    args = parser.parse_args(argv)

    asyncio.run(
        run_briefing_from_scans(
            args.config_path,
            scan_dir=args.scan_dir,
            hours=args.hours,
            skip_dedup=args.skip_dedup,
        )
    )


if __name__ == "__main__":
    main()
