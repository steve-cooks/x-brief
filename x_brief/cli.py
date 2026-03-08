"""
CLI for X Brief
"""

import asyncio
from pathlib import Path
import click

from . import __version__
from .config import save_user_config
from .models import UserConfig


@click.group()
@click.version_option(version=__version__)
def main():
    """𝕏 Brief - scan-only X/Twitter timeline curator"""
    pass


@main.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="config.json",
    help="Output config file path",
)
def init(output: str):
    """Create an example config file"""
    example_config = UserConfig(
        x_handle="your_handle",
        tracked_accounts=[
            "example_org",
            "example_project",
            "community_news",
        ],
        recent_interests=[
            "developer tools",
            "open source",
            "engineering blogs",
        ],
        delivery={
            "type": "telegram",
            "enabled": True,
        },
        briefing_schedule="daily",
    )
    
    output_path = Path(output)
    save_user_config(example_config, output_path)
    
    click.echo(f"✅ Created example config at: {output_path}")
    click.echo("\nNext steps:")
    click.echo("1. Edit config.json with your settings")
    click.echo("2. Put scan JSON files in ./timeline_scans or set X_BRIEF_SCAN_DIR")
    click.echo("3. Run: x-brief run --config config.json --hours 36")


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to config file",
)
@click.option(
    "--hours",
    "-h",
    type=int,
    default=36,
    help="Hours of scan history to include",
)
@click.option(
    "--scan-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Override the scan input directory",
)
@click.option(
    "--skip-dedup",
    is_flag=True,
    help="Ignore brief history and include already-briefed posts",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (prints to stdout if not specified)",
)
def brief(config: str, hours: int, scan_dir: Path | None, skip_dedup: bool, output: str | None):
    """Generate a briefing from browser scan files."""
    asyncio.run(_run_scan_pipeline(config, hours, scan_dir, skip_dedup, output))


async def _run_scan_pipeline(
    config_path: str,
    hours: int,
    scan_dir: Path | None,
    skip_dedup: bool,
    output_file: str | None,
) -> None:
    """Async implementation shared by scan-only commands."""
    from .pipeline import run_briefing_from_scans

    briefing_text = await run_briefing_from_scans(
        config_path,
        scan_dir=str(scan_dir) if scan_dir else None,
        hours=hours,
        skip_dedup=skip_dedup,
    )
    if output_file:
        Path(output_file).write_text(briefing_text, encoding="utf-8")
        click.echo(f"✅ Briefing saved to: {output_file}")


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to config file",
)
@click.option(
    "--hours",
    "-h",
    type=int,
    default=36,
    help="Hours of scan history to include",
)
@click.option(
    "--scan-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Override the scan input directory",
)
@click.option(
    "--skip-dedup",
    is_flag=True,
    help="Ignore brief history and include already-briefed posts",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (prints to stdout if not specified)",
)
def run(config: str, hours: int, scan_dir: Path | None, skip_dedup: bool, output: str | None):
    """Run the scan-only briefing pipeline and export latest-briefing.json."""
    asyncio.run(_run(config, hours, scan_dir, skip_dedup, output))


async def _run(
    config_path: str,
    hours: int,
    scan_dir: Path | None,
    skip_dedup: bool,
    output_file: str | None,
) -> None:
    """Async implementation of run command."""
    try:
        await _run_scan_pipeline(config_path, hours, scan_dir, skip_dedup, output_file)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()


if __name__ == "__main__":
    main()
