"""
CLI for X Brief
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import click

from . import __version__
from .config import load_user_config, save_user_config, load_system_config
from .models import UserConfig, Briefing, BriefingSection, BriefingItem
from .fetcher import XClient
from .cache import Cache, get_or_fetch_user_id
from .scorer import deduplicate, rank_posts
from .formatter import format_markdown, format_html, format_plain


@click.group()
@click.version_option(version=__version__)
def main():
    """𝕏 Brief - AI-powered X/Twitter timeline curator"""
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
        x_handle="yourusername",
        tracked_accounts=[
            "elonmusk",
            "openai",
            "AnthropicAI",
            "steipete",
        ],
        interests=[
            "AI",
            "technology",
            "startups",
            "crypto",
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
    click.echo("2. Set X_BRIEF_BEARER_TOKEN environment variable")
    click.echo("3. Run: x-brief fetch --config config.json")


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
    default=24,
    help="Hours of history to fetch",
)
def fetch(config: str, hours: int):
    """Fetch and cache posts from tracked accounts"""
    asyncio.run(_fetch(config, hours))


async def _fetch(config_path: str, hours: int):
    """Async implementation of fetch command"""
    # Load configs
    user_config = load_user_config(Path(config_path))
    system_config = load_system_config()
    
    if not system_config.x_api_bearer_token:
        click.echo("❌ Error: X_BRIEF_BEARER_TOKEN environment variable not set", err=True)
        return
    
    # Initialize cache and client
    cache = Cache(system_config.db_path)
    
    async with XClient(system_config.x_api_bearer_token) as client:
        # Time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        click.echo(f"📡 Fetching posts from {len(user_config.tracked_accounts)} accounts...")
        click.echo(f"   Time range: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
        
        all_posts = []
        all_users = []
        
        # Fetch posts from tracked accounts
        for username in user_config.tracked_accounts:
            click.echo(f"   Fetching @{username}...")
            
            # Get user ID
            user_id = await get_or_fetch_user_id(cache, username, client)
            if not user_id:
                click.echo(f"   ⚠️  User @{username} not found, skipping")
                continue
            
            # Fetch user's tweets
            posts = await client.get_user_tweets(
                user_id,
                start_time=start_time,
                end_time=end_time,
                max_results=100,
            )
            
            all_posts.extend(posts)
            click.echo(f"   ✓ Fetched {len(posts)} posts from @{username}")
        
        # Fetch users data for all authors
        author_usernames = list(set(post.author_username for post in all_posts))
        if author_usernames:
            click.echo(f"\n👥 Fetching user data for {len(author_usernames)} authors...")
            
            # Batch fetch users (100 at a time)
            for i in range(0, len(author_usernames), 100):
                batch = author_usernames[i:i+100]
                users = await client.get_users_by_usernames(batch)
                all_users.extend(users)
        
        # Cache everything
        click.echo(f"\n💾 Caching {len(all_posts)} posts and {len(all_users)} users...")
        cache.cache_posts(all_posts)
        cache.cache_users(all_users)
        
        # Cleanup expired entries
        cache.cleanup_expired()
        
        click.echo(f"✅ Done! Cached {len(all_posts)} posts from last {hours} hours")


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
    default=24,
    help="Hours to include in briefing",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "html", "plain"]),
    default="markdown",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (prints to stdout if not specified)",
)
def brief(config: str, hours: int, format: str, output: str):
    """Generate a briefing from cached posts"""
    asyncio.run(_brief(config, hours, format, output))


async def _brief(config_path: str, hours: int, output_format: str, output_file: str):
    """Async implementation of brief command"""
    # Load configs
    user_config = load_user_config(Path(config_path))
    system_config = load_system_config()
    
    if not system_config.x_api_bearer_token:
        click.echo("❌ Error: X_BRIEF_BEARER_TOKEN environment variable not set", err=True)
        return
    
    # Initialize cache
    cache = Cache(system_config.db_path)
    
    click.echo(f"📊 Generating briefing for last {hours} hours...")
    
    # Time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    # For now, create a simple briefing from cache
    # TODO: This should use the AI analyzer/curator modules (Phase 2)
    
    # Fetch posts from cache and score them
    # This is a simplified version - in reality we'd query the cache by time range
    async with XClient(system_config.x_api_bearer_token) as client:
        all_posts = []
        all_users = []
        
        # Re-fetch recent posts (in production, we'd query cache)
        for username in user_config.tracked_accounts[:5]:  # Limit for demo
            user_id = await get_or_fetch_user_id(cache, username, client)
            if user_id:
                posts = await client.get_user_tweets(
                    user_id,
                    start_time=start_time,
                    end_time=end_time,
                    max_results=20,
                )
                all_posts.extend(posts)
                
                # Get user data
                user = cache.get_user_by_username(username)
                if user:
                    all_users.append(user)
    
    # Deduplicate and score
    unique_posts = deduplicate(all_posts)
    
    # Build users map
    users_map = {user.id: user for user in all_users}
    
    # Rank posts
    ranked_posts = rank_posts(unique_posts, users_map)
    
    # Create briefing sections
    sections = []
    
    # Top stories (top 5 posts)
    top_posts = ranked_posts[:5]
    if top_posts:
        top_items = []
        for post in top_posts:
            author = users_map.get(post.author_id)
            score = None
            if author:
                from .scorer import score_post
                score = score_post(post, author.followers_count)
            
            top_items.append(BriefingItem(
                post=post,
                summary=post.text[:200] + "..." if len(post.text) > 200 else post.text,
                category="top",
                score=score or 0.0,
            ))
        
        sections.append(BriefingSection(
            title="TOP STORIES",
            emoji="📌",
            items=top_items,
        ))
    
    # Create briefing
    briefing = Briefing(
        generated_at=end_time,
        period_start=start_time,
        period_end=end_time,
        sections=sections,
        stats={
            "posts_scanned": len(all_posts),
            "unique_posts": len(unique_posts),
            "accounts_tracked": len(user_config.tracked_accounts),
            "time_range_hours": hours,
        }
    )
    
    # Format output
    if output_format == "markdown":
        formatted = format_markdown(briefing)
    elif output_format == "html":
        formatted = format_html(briefing)
    else:
        formatted = format_plain(briefing)
    
    # Output
    if output_file:
        Path(output_file).write_text(formatted)
        click.echo(f"✅ Briefing saved to: {output_file}")
    else:
        click.echo("\n" + formatted)


@main.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to config file",
)
def accounts(config: str):
    """List tracked accounts"""
    user_config = load_user_config(Path(config))
    
    click.echo(f"📋 Tracked accounts ({len(user_config.tracked_accounts)}):\n")
    
    for username in user_config.tracked_accounts:
        click.echo(f"  • @{username}")
    
    if user_config.recent_interests:
        click.echo(f"\n🔍 Interest topics ({len(user_config.recent_interests)}):\n")
        for interest in user_config.recent_interests:
            click.echo(f"  • {interest}")


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
    default=24,
    help="Hours of history to include",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (prints to stdout if not specified)",
)
def run(config: str, hours: int, output: str):
    """Run the complete briefing pipeline (fetch + analyze + curate + format)"""
    asyncio.run(_run(config, hours, output))


async def _run(config_path: str, hours: int, output_file: str):
    """Async implementation of run command"""
    from .pipeline import run_briefing
    
    try:
        # Run the complete pipeline
        briefing_text = await run_briefing(config_path, hours)
        
        # Output to file or stdout
        if output_file:
            Path(output_file).write_text(briefing_text)
            click.echo(f"\n✅ Briefing saved to: {output_file}")
        else:
            click.echo("\n" + "="*60)
            click.echo(briefing_text)
            click.echo("="*60)
    
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        raise click.Abort()


if __name__ == "__main__":
    main()
