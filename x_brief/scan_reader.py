"""
Read and parse Rabbit timeline scan JSON files into Post objects.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from x_brief.models import Post, PostMetrics, PostMedia, QuotedPost, ThreadPost, User


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

ARTICLE_URL_RE = re.compile(r'https?://(?:www\.)?(?:x|twitter)\.com/[^/\s]+/article/[A-Za-z0-9_-]+', re.IGNORECASE)
THREAD_MARKER_RE = re.compile(r'(?:\b\d+\s*/\s*\d+\b|\bthread\b|🧵)', re.IGNORECASE)


def extract_post_id(url: str) -> Optional[str]:
    """Extract post/article ID from X/Twitter URL."""
    if not url:
        return None
    status_match = re.search(r'/status/(\d+)', url)
    if status_match:
        return status_match.group(1)

    article_match = re.search(r'/article/([A-Za-z0-9_-]+)', url)
    if article_match:
        return f"article:{article_match.group(1)}"

    return None


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


def parse_posted_at(posted_at: str, scan_time: datetime) -> Optional[datetime]:
    """
    Parse relative/absolute time strings from scan data into actual datetimes.

    Handles:
    - Relative: "57m ago", "2h ago", "3d ago", "57 minutes ago", "2 hours ago"
    - Short relative: "2h", "30m", "3d" (no "ago" suffix)
    - Absolute month-day: "Feb 23", "Jan 5"
    - ISO-ish: "2026-02-23", "2026-02-23T10:00:00Z"
    """
    if not posted_at or not isinstance(posted_at, str):
        return None

    posted_at = posted_at.strip()
    if not posted_at:
        return None

    # --- Relative: "Xm ago", "X minutes ago", "Xh ago", "X hours ago", "Xd ago", "X days ago" ---
    rel_match = re.match(
        r'^(\d+)\s*(?:(m|min|mins|minute|minutes)|(h|hr|hrs|hour|hours)|(d|day|days))\s*(?:ago)?$',
        posted_at, re.IGNORECASE
    )
    if rel_match:
        amount = int(rel_match.group(1))
        if rel_match.group(2):  # minutes
            return scan_time - timedelta(minutes=amount)
        elif rel_match.group(3):  # hours
            return scan_time - timedelta(hours=amount)
        elif rel_match.group(4):  # days
            return scan_time - timedelta(days=amount)

    # --- "just now" / "now" ---
    if posted_at.lower() in ("just now", "now"):
        return scan_time

    # --- Absolute month-day: "Feb 23", "January 5" ---
    month_day_match = re.match(
        r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})$',
        posted_at, re.IGNORECASE
    )
    if month_day_match:
        try:
            month_str = month_day_match.group(1)
            day = int(month_day_match.group(2))
            # Use scan_time's year, handle year rollover
            candidate = datetime.strptime(f"{month_str} {day} {scan_time.year}", "%b %d %Y")
            candidate = candidate.replace(tzinfo=timezone.utc)
            # If candidate is in the future, it's probably last year
            if candidate > scan_time:
                candidate = candidate.replace(year=scan_time.year - 1)
            return candidate
        except ValueError:
            pass

    # --- ISO date/datetime: "2026-02-23" or "2026-02-23T10:00:00Z" ---
    try:
        parsed = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        pass

    return None


def sanitize_pinned(value: str) -> str:
    """Strip '(pinned)' artifacts from scraped author data."""
    if not value:
        return value
    return value.replace(" (pinned)", "").replace("(pinned)", "").strip()


def normalize_source(value: object) -> Optional[str]:
    """Normalize scan source to for_you/following/None."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"for_you", "foryou"}:
        return "for_you"
    if normalized == "following":
        return "following"
    return None


def detect_article_url(post_url: str, urls: list[str]) -> Optional[str]:
    """Find first X article URL in post or linked URLs."""
    candidates = [post_url, *urls]
    for candidate in candidates:
        if candidate and ARTICLE_URL_RE.search(candidate):
            return candidate
    return None


def build_post_url(post: Post) -> str:
    """Build a stable URL for a post/article."""
    if post.is_article and post.article_url:
        return post.article_url
    if post.id.startswith("article:") and post.article_url:
        return post.article_url
    return f"https://x.com/{post.author_username}/status/{post.id}"


def _thread_connected(prev: Post, cur: Post) -> bool:
    """Heuristic for adjacent posts likely being part of same thread."""
    if prev.author_id != cur.author_id:
        return False

    if prev.conversation_id and cur.conversation_id and prev.conversation_id == cur.conversation_id:
        return True

    age_diff_minutes = abs((prev.created_at - cur.created_at).total_seconds()) / 60
    if age_diff_minutes > 90:
        return False

    if THREAD_MARKER_RE.search(prev.text) or THREAD_MARKER_RE.search(cur.text):
        return True

    # Fallback: same author + near-adjacent + both substantive text
    return len(prev.text.strip()) > 40 and len(cur.text.strip()) > 40


def annotate_threads(posts: list[Post]) -> None:
    """Populate thread_posts for likely thread chains from same author."""
    if len(posts) < 2:
        return

    by_author: dict[str, list[Post]] = {}
    for post in posts:
        by_author.setdefault(post.author_id, []).append(post)

    for author_posts in by_author.values():
        if len(author_posts) < 2:
            continue

        ordered = sorted(author_posts, key=lambda p: p.created_at)
        i = 0
        while i < len(ordered) - 1:
            chain = [ordered[i]]
            j = i + 1
            while j < len(ordered) and _thread_connected(chain[-1], ordered[j]):
                chain.append(ordered[j])
                j += 1

            if len(chain) >= 2:
                for idx, post in enumerate(chain):
                    connected: list[ThreadPost] = []
                    for k, part in enumerate(chain):
                        if k == idx:
                            continue
                        connected.append(
                            ThreadPost(
                                id=part.id,
                                text=part.text,
                                url=build_post_url(part),
                            )
                        )
                    post.thread_posts = connected
            i = j if len(chain) >= 2 else i + 1


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
        # Extract post/article ID from URL
        url = post_data.get('url', '')
        post_id = extract_post_id(url)
        if not post_id:
            return None
        
        # Extract author info — sanitize "(pinned)" at ingest time
        # Support both 'author' (legacy) and 'author_handle' (Rabbit scan format)
        author = sanitize_pinned(post_data.get('author', '') or post_data.get('author_handle', ''))
        # If still empty, try to extract from URL
        if not author:
            author = extract_username(url)
        author_username = extract_username(author)
        # Also strip (pinned) from username in case it leaked there
        author_username = sanitize_pinned(author_username)
        author_name = sanitize_pinned(post_data.get('author_name', '') or author_username)
        author_avatar_url = sanitize_pinned(post_data.get('avatar_url', '') or post_data.get('author_avatar_url', '') or '') or None
        
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
        
        # Extract URLs from text (plus explicit URL fields if present)
        urls = re.findall(r'https?://\S+', text)
        explicit_urls = post_data.get('urls') if isinstance(post_data.get('urls'), list) else []
        for u in explicit_urls:
            if isinstance(u, str) and u not in urls:
                urls.append(u)

        # Parse posted_at for accurate post time
        posted_at_str = post_data.get('posted_at') or post_data.get('time') or ''
        parsed_time = parse_posted_at(posted_at_str, scan_time) or scan_time

        source = normalize_source(post_data.get('source'))
        article_url = detect_article_url(url, urls)
        is_article = article_url is not None

        # Create Post object
        post = Post(
            id=post_id,
            text=text,
            author_id=author_username,  # Use username as ID since we don't have real IDs
            author_username=author_username,
            author_name=author_name,
            author_avatar_url=author_avatar_url,
            created_at=parsed_time,  # Use parsed posted_at, fall back to scan_time
            metrics=metrics,
            media=media_items,
            urls=urls,
            source=source,
            is_article=is_article,
            article_url=article_url,
            is_repost=False,
            is_quote=is_quote,
            quoted_post_id=quoted_post_id,
            quoted_post=quoted_post,
            conversation_id=post_data.get('conversation_id') or post_data.get('conversationId'),
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
            with open(json_file, 'r', encoding='utf-8') as f:
                scan_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in scan file {json_file.name}: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed reading scan file {json_file.name}: {e}") from e

        # Parse scan time — accept both 'scan_time' and 'timestamp' keys
        scan_time_str = scan_data.get('scan_time') or scan_data.get('timestamp')
        if not scan_time_str:
            continue

        scan_time = datetime.fromisoformat(scan_time_str.replace('Z', '+00:00'))

        # Skip if too old
        if scan_time < cutoff_time:
            continue

        scans_loaded += 1

        # Process viral_alerts, notable_posts, and top-level posts list (newer format)
        for section in ('viral_alerts', 'notable_posts', 'posts'):
            for post_data in scan_data.get(section, []):
                # Collect verification data from scan
                verified_val = post_data.get('verified')
                if verified_val is not None:
                    author = sanitize_pinned(post_data.get('author', '') or post_data.get('author_handle', ''))
                    username = extract_username(author).lower()
                    if username:
                        scan_verified[username] = bool(verified_val)

                post = parse_scan_post(post_data, scan_time)
                if post and post.id not in posts_by_id:
                    posts_by_id[post.id] = post
    
    posts = list(posts_by_id.values())
    annotate_threads(posts)
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
                profile_image_url=post.author_avatar_url,
            )
    
    return users_map
