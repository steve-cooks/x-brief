"""
Read and parse Rabbit timeline scan JSON files into Post objects.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from x_brief.models import Post, PostMetrics, PostMedia, QuotedPost, User


# Known-verified accounts fallback (major accounts that are verified on X)
# Used when scan data doesn't include verification status
KNOWN_VERIFIED_ACCOUNTS: dict[str, str] = {
    # AI companies
    "anthropic": "business",
    "anthropicai": "business",
    "claudeai": "business",
    "openai": "business",
    "google": "business",
    "googleai": "business",
    "googledeepmind": "business",
    "deepmind": "business",
    "microsoft": "business",
    "xai": "business",
    "meta": "business",
    "metaai": "business",
    "nvidia": "business",
    "huggingface": "business",
    "midaborney": "business",
    "stability_ai": "business",
    "peraborney_ai": "business",
    "coaborney": "business",
    "cursor_ai": "business",
    "replitai": "business",
    "replit": "business",
    "vercel": "business",
    "github": "business",
    "amazonsci": "business",
    "apple": "business",
    # AI people
    "elonmusk": "blue",
    "sama": "blue",
    "daborney": "blue",
    "karpaborney": "blue",
    "ilyasut": "blue",
    "demaborney": "blue",
    "ylecun": "blue",
    "jeffdean": "blue",
    "drjimfan": "blue",
    "emollick": "blue",
    "hardmaru": "blue",
    # Tech people
    "steipete": "blue",
    "alexfinn": "blue",
    "levelsio": "blue",
    "marc_louvion": "blue",
    "dhh": "blue",
    "natfriedman": "blue",
    "rauchg": "blue",
    "swyx": "blue",
    "simonw": "blue",
    "karpaborney": "blue",
    # Media / news
    "techcrunch": "business",
    "theverge": "business",
    "wired": "business",
    "reuters": "business",
    "bloomberg": "business",
    "wsj": "business",
    "nytimes": "business",
    "twistartups": "business",
}

# Fix duplicates/typos in the verified list (Playwright scraper artifacts)
# Keep clean lowercase usernames only
KNOWN_VERIFIED_ACCOUNTS = {k.lower().strip(): v for k, v in KNOWN_VERIFIED_ACCOUNTS.items()}


def extract_post_id(url: str) -> Optional[str]:
    """Extract post ID from X/Twitter URL."""
    match = re.search(r'/status/(\d+)', url)
    return match.group(1) if match else None


def extract_username(handle_or_url: str) -> str:
    """Extract username from @handle or URL."""
    # Strip all leading @ signs (handles @@username from some scan formats)
    cleaned = handle_or_url.lstrip('@')
    if cleaned != handle_or_url:
        return cleaned
    # Extract from URL if it's a URL
    match = re.search(r'x\.com/([^/]+)', handle_or_url)
    if match:
        return match.group(1)
    return handle_or_url.strip('@')


def parse_human_number(value) -> int:
    """Parse human-readable numbers like '129K', '1.2M', '61K' into integers."""
    if isinstance(value, (int, float)):
        return int(value)
    if not isinstance(value, str):
        return 0
    value = value.strip().replace(',', '')
    multipliers = {'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}
    for suffix, mult in multipliers.items():
        if value.upper().endswith(suffix):
            try:
                return int(float(value[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def sanitize_pinned(value: str) -> str:
    """Strip '(pinned)' artifacts from scraped author data."""
    if not value:
        return value
    return value.replace(" (pinned)", "").replace("(pinned)", "").strip()


def extract_media_from_post(post_data: dict, text: str) -> list[PostMedia]:
    """
    Extract media items from scan post data.
    
    Handles:
    - media field as string (e.g., "video", "photo") from older scan formats
    - media field as list of dicts from future scan formats  
    - Image URLs extracted from tweet text (pbs.twimg.com)
    """
    media_items: list[PostMedia] = []
    
    raw_media = post_data.get('media')
    
    if isinstance(raw_media, str) and raw_media:
        # Older scan format: media is a simple type string like "video", "photo"
        media_items.append(PostMedia(type=raw_media))
    elif isinstance(raw_media, list):
        # Future/richer scan format: list of media objects
        for m in raw_media:
            if isinstance(m, dict):
                media_items.append(PostMedia(
                    type=m.get('type', 'photo'),
                    url=m.get('url') or m.get('media_url') or m.get('src'),
                    preview_image_url=m.get('preview_image_url') or m.get('thumbnail'),
                    video_url=m.get('video_url'),
                    alt_text=m.get('alt_text') or m.get('alt'),
                ))
            elif isinstance(m, str):
                # Simple string type in a list
                media_items.append(PostMedia(type=m))
    elif isinstance(raw_media, dict):
        # Single media object
        media_items.append(PostMedia(
            type=raw_media.get('type', 'photo'),
            url=raw_media.get('url') or raw_media.get('media_url'),
            preview_image_url=raw_media.get('preview_image_url'),
            video_url=raw_media.get('video_url'),
            alt_text=raw_media.get('alt_text'),
        ))
    
    # Extract image URLs from tweet text (pbs.twimg.com)
    if text:
        pbs_urls = re.findall(r'https?://pbs\.twimg\.com/media/[^\s"\']+', text)
        for url in pbs_urls:
            # Avoid duplicates
            if not any(m.url == url for m in media_items):
                media_items.append(PostMedia(type="photo", url=url))
    
    return media_items


def extract_quoted_post(post_data: dict) -> Optional[QuotedPost]:
    """
    Extract quoted tweet data if present in scan data.
    
    Handles various possible field names from scan data.
    """
    # Try various field names for quoted content
    quoted = (
        post_data.get('quoted_tweet')
        or post_data.get('quote_tweet')
        or post_data.get('quoted')
        or post_data.get('quotedPost')
    )
    
    if not quoted or not isinstance(quoted, dict):
        return None
    
    quoted_text = quoted.get('text', '')
    if not quoted_text:
        return None
    
    quoted_author = sanitize_pinned(quoted.get('author', '') or quoted.get('author_username', ''))
    quoted_author_name = sanitize_pinned(quoted.get('author_name', '') or quoted_author)
    quoted_username = extract_username(quoted_author) if quoted_author else ''
    
    # Extract quoted post URL and ID
    quoted_url = quoted.get('url', '')
    quoted_id = extract_post_id(quoted_url) if quoted_url else None
    
    # Parse quoted metrics if available
    quoted_metrics = None
    q_metrics = quoted.get('metrics') or quoted.get('engagement')
    if q_metrics and isinstance(q_metrics, dict):
        quoted_metrics = PostMetrics(
            likes=parse_human_number(q_metrics.get('likes', 0)),
            reposts=parse_human_number(q_metrics.get('reposts', 0) or q_metrics.get('retweets', 0)),
            replies=parse_human_number(q_metrics.get('replies', 0)),
            views=parse_human_number(q_metrics.get('views', 0)),
        )
    
    return QuotedPost(
        id=quoted_id,
        text=quoted_text,
        author_username=quoted_username,
        author_name=quoted_author_name,
        metrics=quoted_metrics,
        post_url=quoted_url or None,
    )


def parse_scan_post(post_data: dict, scan_time: datetime) -> Optional[Post]:
    """Convert a scan post dict to a Post object."""
    try:
        # Extract post ID from URL
        url = post_data.get('url', '')
        post_id = extract_post_id(url)
        if not post_id:
            return None
        
        # Extract author info — sanitize "(pinned)" at ingest time
        author = sanitize_pinned(post_data.get('author', ''))
        author_username = extract_username(author)
        # Also strip (pinned) from username in case it leaked there
        author_username = sanitize_pinned(author_username)
        author_name = sanitize_pinned(post_data.get('author_name', '') or author_username)
        
        # Parse metrics — handle both 'metrics' and 'engagement' keys
        # Also handle top-level metric fields
        metrics_data = post_data.get('metrics') or post_data.get('engagement') or {}
        
        # Fall back to top-level fields if metrics dict is empty
        likes = parse_human_number(
            metrics_data.get('likes', 0)
            or post_data.get('likes', 0)
        )
        reposts = parse_human_number(
            metrics_data.get('reposts', 0)
            or metrics_data.get('retweets', 0)
            or post_data.get('reposts', 0)
            or post_data.get('retweets', 0)
        )
        replies = parse_human_number(
            metrics_data.get('replies', 0)
            or post_data.get('replies', 0)
        )
        views = parse_human_number(
            metrics_data.get('views', 0)
            or post_data.get('views', 0)
        )
        bookmarks = parse_human_number(
            metrics_data.get('bookmarks', 0)
            or post_data.get('bookmarks', 0)
        )
        
        metrics = PostMetrics(
            likes=likes,
            reposts=reposts,
            replies=replies,
            views=views,
            quotes=0,
            bookmarks=bookmarks,
        )
        
        # Extract media
        text = post_data.get('text', '')
        media_items = extract_media_from_post(post_data, text)
        
        # Extract quoted tweet
        quoted_post = extract_quoted_post(post_data)
        is_quote = quoted_post is not None
        quoted_post_id = quoted_post.id if quoted_post else None
        
        # Extract URLs from text
        urls = re.findall(r'https?://\S+', text)
        
        # Create Post object
        post = Post(
            id=post_id,
            text=text,
            author_id=author_username,  # Use username as ID since we don't have real IDs
            author_username=author_username,
            author_name=author_name,
            created_at=scan_time,  # Use scan time as proxy for post time
            metrics=metrics,
            media=media_items,
            urls=urls,
            is_repost=False,
            is_quote=is_quote,
            quoted_post_id=quoted_post_id,
            quoted_post=quoted_post,
        )
        
        return post
    except Exception as e:
        print(f"  ⚠️ Error parsing post: {e}")
        return None


def load_scan_posts(scan_dir: str, hours: int = 48) -> tuple[list[Post], dict[str, bool]]:
    """
    Load posts from Rabbit timeline scan JSON files.
    
    Args:
        scan_dir: Directory containing scan JSON files (YYYY-MM-DD-HH.json format)
        hours: Only load scans from the last N hours
    
    Returns:
        Tuple of (list of Post objects deduplicated by post ID, dict of username->verified from scan data)
    """
    scan_path = Path(scan_dir).expanduser()
    if not scan_path.exists():
        print(f"⚠️ Scan directory not found: {scan_path}")
        return [], {}
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    posts_by_id: dict[str, Post] = {}  # Deduplicate by post ID
    scan_verified: dict[str, bool] = {}  # Collect verification data
    scans_loaded = 0
    
    print(f"📁 Loading scans from {scan_path}")
    print(f"   Cutoff: {cutoff_time.isoformat()} ({hours}h ago)")
    
    # Find all JSON files matching the pattern
    json_files = sorted(scan_path.glob("*.json"))
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                scan_data = json.load(f)
            
            # Parse scan time
            scan_time_str = scan_data.get('scan_time')
            if not scan_time_str:
                continue
            
            scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))
            
            # Skip if too old
            if scan_time < cutoff_time:
                continue
            
            scans_loaded += 1
            
            # Process viral_alerts and notable_posts
            for section in ('viral_alerts', 'notable_posts'):
                for post_data in scan_data.get(section, []):
                    # Collect verification data from scan
                    verified_val = post_data.get('verified')
                    if verified_val is not None:
                        author = sanitize_pinned(post_data.get('author', ''))
                        username = extract_username(author).lower()
                        if username:
                            scan_verified[username] = bool(verified_val)
                    
                    post = parse_scan_post(post_data, scan_time)
                    if post and post.id not in posts_by_id:
                        posts_by_id[post.id] = post
        
        except Exception as e:
            print(f"  ⚠️ Error loading {json_file.name}: {e}")
            continue
    
    posts = list(posts_by_id.values())
    print(f"✅ Loaded {len(posts)} unique posts from {scans_loaded} scan files")
    
    return posts, scan_verified


def build_users_from_posts(
    posts: list[Post],
    scan_verified: dict[str, bool] | None = None,
) -> dict[str, User]:
    """
    Build a minimal users dictionary from post data.
    
    Since scan data doesn't include full user profiles, we create minimal
    User objects with just the info we have from posts.
    Uses known-verified accounts fallback when scan data lacks verification info.
    
    Args:
        posts: List of Post objects
        scan_verified: Optional dict of username -> verified bool from scan data
    
    Returns:
        Dict mapping author_id (username) to User object
    """
    scan_verified = scan_verified or {}
    users_map: dict[str, User] = {}
    
    for post in posts:
        if post.author_id not in users_map:
            username_lower = post.author_username.lower()
            
            # Determine verification status:
            # 1. Check scan data first
            # 2. Fall back to known-verified list
            is_verified = False
            verified_type = None
            
            if username_lower in scan_verified:
                is_verified = scan_verified[username_lower]
                verified_type = "blue" if is_verified else None
            elif username_lower in KNOWN_VERIFIED_ACCOUNTS:
                is_verified = True
                verified_type = KNOWN_VERIFIED_ACCOUNTS[username_lower]
            
            users_map[post.author_id] = User(
                id=post.author_id,
                username=post.author_username,
                name=post.author_name,
                description=None,
                followers_count=1000,  # Default moderate count for scoring
                verified=is_verified,
                verified_type=verified_type,
                profile_image_url=None,
            )
    
    return users_map
