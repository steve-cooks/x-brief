"""Content curation and briefing assembly for X Brief."""
import re
from datetime import datetime, timezone
from x_brief.models import Post, User, Briefing, BriefingSection, BriefingItem
from x_brief.scorer import deduplicate, score_post, is_mega_viral


INTEREST_KEYWORDS = {
    "AI & Tech": [
        "ai",
        "artificial intelligence",
        "llm",
        "gpt",
        "claude",
        "machine learning",
        "deep learning",
        "neural",
        "model",
        "openai",
        "anthropic",
        "agent",
        "coding",
        "developer",
        "software",
        "engineering",
        "api",
        "open source",
        "cursor",
        "copilot",
        "codex",
        "programming",
        "tech",
    ],
    "Crypto & Web3": [
        "crypto",
        "bitcoin",
        "ethereum",
        "web3",
        "nft",
        "defi",
        "blockchain",
        "token",
        "sol",
        "solana",
        "wallet",
        "onchain",
    ],
    "Startups & Business": [
        "startup",
        "founder",
        "building",
        "launch",
        "saas",
        "revenue",
        "growth",
        "product",
        "yc",
        "fundraise",
        "investor",
        "venture",
        "business",
        "entrepreneur",
        "ship",
    ],
    "Design & UI": [
        "design",
        "ui",
        "ux",
        "figma",
        "css",
        "animation",
        "frontend",
        "pixel",
        "typography",
        "visual",
    ],
    "Sports": ["tennis", "football", "basketball", "athlete", "match", "tournament", "grand slam", "atp", "nba", "nfl"],
    "Self-Improvement": ["mindset", "discipline", "focus", "productivity", "habits", "routine", "grind", "growth", "motivation", "quotes"],
    "Creator Economy": ["creator", "content", "audience", "community", "newsletter", "youtube", "podcast", "monetize", "whop"],
}


def categorize_posts(posts: list[Post], interests: list[str]) -> dict[str, list[Post]]:
    """Assign posts to interest categories based on text content."""
    categorized = {interest: [] for interest in interests}
    categorized["General"] = []

    for post in posts:
        text = post.text.lower()
        matched = False
        for interest in interests:
            keywords = INTEREST_KEYWORDS.get(interest, [])
            if any(keyword in text for keyword in keywords):
                categorized[interest].append(post)
                matched = True
        if not matched:
            categorized["General"].append(post)

    return {key: value for key, value in categorized.items() if value}


def detect_breakout_posts(posts: list[Post], threshold: float = 2.0) -> list[Post]:
    """Find posts with unusually high engagement for an author."""
    if not posts:
        return []

    by_author: dict[str, list[Post]] = {}
    for post in posts:
        by_author.setdefault(post.author_id, []).append(post)

    breakouts = []
    for author_posts in by_author.values():
        if len(author_posts) < 2:
            continue

        engagements = []
        for post in author_posts:
            metrics = post.metrics
            engagement = metrics.likes + metrics.reposts * 3 + metrics.replies * 2 + metrics.quotes * 4
            engagements.append((post, engagement))

        median_engagement = sorted(score for _, score in engagements)[len(engagements) // 2] or 1
        for post, engagement in engagements:
            if engagement > median_engagement * threshold:
                breakouts.append(post)

    return breakouts


def detect_network_amplification(posts: list[Post], search_posts: list[Post]) -> dict[str, float]:
    """
    Detect when multiple followed accounts reference the same post/URL.
    Returns a dict of post_id -> boost multiplier for network-amplified posts.
    
    If 3+ posts from followed accounts quote-tweet or reference the same external
    post/URL, that referenced post gets a 3x score boost.
    """
    # Track references to external posts/URLs
    url_references: dict[str, list[str]] = {}  # URL/post_id -> list of referring post author_ids
    
    for post in posts:
        # Look for quoted post URLs (twitter.com or x.com status links)
        quoted_matches = re.findall(r'https://(?:twitter|x)\.com/(\w+)/status/(\d+)', post.text)
        for username, status_id in quoted_matches:
            ref_key = f"status:{status_id}"
            if ref_key not in url_references:
                url_references[ref_key] = []
            if post.author_id not in url_references[ref_key]:
                url_references[ref_key].append(post.author_id)
        
        # Also track other URLs being shared
        for url in post.urls:
            # Skip twitter/x.com links (handled above)
            if 'twitter.com' in url or 'x.com' in url:
                continue
            if url not in url_references:
                url_references[url] = []
            if post.author_id not in url_references[url]:
                url_references[url].append(post.author_id)
    
    # Find network-amplified content (3+ unique authors referencing same thing)
    amplified_boosts: dict[str, float] = {}
    for ref_key, author_ids in url_references.items():
        if len(author_ids) >= 3:
            # This content is being amplified by the network
            if ref_key.startswith("status:"):
                post_id = ref_key.replace("status:", "")
                amplified_boosts[post_id] = 3.0
    
    return amplified_boosts


def _is_external_url(url: str) -> bool:
    """True for non-X links (including generic external domains)."""
    normalized = (url or "").lower()
    return (
        normalized.startswith("http://") or normalized.startswith("https://")
    ) and all(domain not in normalized for domain in ("x.com", "twitter.com", "t.co"))


def clean_summary(text: str, max_len: int = 120) -> str:
    """Extract a clean summary from tweet text."""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove @mentions at start
    text = re.sub(r'^(@\w+\s*)+', '', text)
    # Clean whitespace
    text = ' '.join(text.split()).strip()
    if len(text) > max_len:
        text = text[:max_len-3].rsplit(' ', 1)[0] + '...'
    return text or "(media post)"

def cap_posts_per_account(posts_with_scores: list[tuple[Post, float]], max_per_account: int = 2) -> list[tuple[Post, float]]:
    """
    Cap posts to max N per author_id, keeping highest scored ones.

    Args:
        posts_with_scores: List of (post, score) tuples
        max_per_account: Maximum posts per author (default 2)

    Returns:
        Filtered list with max N posts per author_id
    """
    from collections import defaultdict

    # Group by author_id
    by_author = defaultdict(list)
    for post, score in posts_with_scores:
        by_author[post.author_id].append((post, score))

    # Sort each author's posts by score and keep top N
    result = []
    for author_id, author_posts in by_author.items():
        author_posts.sort(key=lambda x: x[1], reverse=True)
        result.extend(author_posts[:max_per_account])

    # Re-sort by score
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def curate_briefing(
    posts: list[Post],
    users: dict[str, User],
    interests: list[str],
    tracked_accounts: list[str] | None = None,
    hours: int = 24,
    search_posts: list[Post] | None = None,
) -> Briefing:
    """Build a structured briefing from fetched posts."""
    now = datetime.now(timezone.utc)
    tracked_accounts_set = {a.lower().lstrip('@') for a in (tracked_accounts or []) if a}

    # Deduplicate
    posts = deduplicate(posts, section="general")
    all_search = deduplicate(search_posts or [], section="general")
    
    # Filter search posts by minimum engagement thresholds
    # Require: (10 likes OR 5 reposts) AND 100 views
    filtered_search = []
    for p in all_search:
        meets_engagement = (p.metrics.likes >= 10 or p.metrics.reposts >= 5)
        meets_views = p.metrics.views >= 100
        if meets_engagement and meets_views:
            filtered_search.append(p)
    
    # Score all posts
    scored = []
    for p in posts:
        user = users.get(p.author_id)
        followers = user.followers_count if user else 100
        s = score_post(p, followers)
        scored.append((p, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # Score search posts (with user lookup for better normalization)
    search_scored = []
    for p in filtered_search:
        user = users.get(p.author_id)
        followers = user.followers_count if user else 1000  # default moderate count
        s = score_post(p, followers)
        # Only include posts with score > 0
        if s > 0:
            search_scored.append((p, s))
    search_scored.sort(key=lambda x: x[1], reverse=True)
    
    # Breakout detection
    breakouts = set(p.id for p in detect_breakout_posts(posts))
    
    # Categorize
    categorized = categorize_posts(posts, interests)
    
    sections = []
    used_ids = set()
    
    # Detect network amplification
    network_boosts = detect_network_amplification(posts, filtered_search)
    
    # Apply network amplification boosts to search scored
    for i, (p, s) in enumerate(search_scored):
        if p.id in network_boosts:
            search_scored[i] = (p, s * network_boosts[p.id])
    search_scored.sort(key=lambda x: x[1], reverse=True)
    
    # Section 0: VIRAL 🔥 — mega-viral posts from search (appears first when found)
    # Only posts meeting mega-viral thresholds, max 3, regardless of author
    all_search_for_viral = deduplicate(search_posts or [], section="general")
    viral_posts = []
    for p in all_search_for_viral:
        if is_mega_viral(p) and p.id not in used_ids:
            user = users.get(p.author_id)
            followers = user.followers_count if user else 1000
            s = score_post(p, followers)
            viral_posts.append((p, s))
    
    # Sort by score, cap per account, and take top 3
    viral_posts.sort(key=lambda x: x[1], reverse=True)
    viral_posts = cap_posts_per_account(viral_posts)
    viral_items = []
    for p, s in viral_posts[:3]:
        viral_items.append(BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Viral",
            score=s,
        ))
        used_ids.add(p.id)
    
    # Only add VIRAL section if we have mega-viral posts
    if viral_items:
        sections.append(BriefingSection(title="VIRAL 🔥", emoji="🔥", items=viral_items))
    
    # Section 1: TOP STORIES — highest scored overall (filter short posts)
    top_candidates = deduplicate([p for p, s in scored], section="top_stories")
    top_scored = []
    for p in top_candidates:
        if p.id not in used_ids:
            # TOP STORIES requires meaningful engagement and excludes article/thread candidates
            m = p.metrics
            if m.likes < 100 and m.reposts < 20 and m.views < 10_000:
                continue
            if any(_is_external_url(u) for u in p.urls) or len(p.text) > 280:
                continue
            user = users.get(p.author_id)
            followers = user.followers_count if user else 100
            s = score_post(p, followers)
            top_scored.append((p, s))
    top_scored = cap_posts_per_account(top_scored)
    top_items = []
    for p, s in top_scored:
        top_items.append(BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Top Stories",
            score=s,
        ))
        used_ids.add(p.id)
        if len(top_items) >= 5:
            break
    if top_items:
        sections.append(BriefingSection(title="TOP STORIES", emoji="📌", items=top_items))
    
    # Section 2: YOUR CIRCLE — tracked accounts from config (works in scan-only mode)
    circle_items = []
    circle_candidates = [
        (p, s)
        for p, s in scored
        if p.id not in used_ids
        and p.author_username.lower().lstrip('@') in tracked_accounts_set
        and (p.metrics.likes >= 15 or p.metrics.reposts >= 3 or p.metrics.views >= 300)
        and not any(_is_external_url(u) for u in p.urls)
        and len(p.text) <= 280
    ]
    circle_candidates = cap_posts_per_account(circle_candidates)
    for p, s in circle_candidates:
        category = "General"
        for interest, cat_posts in categorized.items():
            if interest == "General":
                continue
            if any(cp.id == p.id for cp in cat_posts):
                category = interest
                break
        circle_items.append(BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category=category,
            score=s,
        ))
        used_ids.add(p.id)
        if len(circle_items) >= 10:
            break
    if circle_items:
        sections.append(BriefingSection(title="YOUR CIRCLE", emoji="👥", items=circle_items))
    
    # Section 3: TRENDING IN YOUR NICHES — from search results (already filtered by engagement & score > 0)
    search_scored = cap_posts_per_account(search_scored)
    trend_items = []
    for p, s in search_scored[:8]:
        if p.id in used_ids:
            continue
        if any(_is_external_url(u) for u in p.urls) or len(p.text) > 280:
            continue
        trend_items.append(BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Trending",
            score=s,
        ))
        used_ids.add(p.id)
    if trend_items:
        sections.append(BriefingSection(title="TRENDING IN YOUR NICHES", emoji="🔥", items=trend_items))
    
    # Section 3.5: ARTICLES & THREADS — external URLs or long-form posts (scan + search)
    article_items = []
    article_authors: set[str] = set()
    article_pool = {p.id: (p, s) for p, s in scored}
    for p, s in search_scored:
        article_pool.setdefault(p.id, (p, s))

    for p, s in sorted(article_pool.values(), key=lambda x: x[1], reverse=True):
        if p.id in used_ids:
            continue
        if p.author_id in article_authors:
            continue  # cap 1 per account
        m = p.metrics
        # Must meet minimum engagement: 500 likes or 50K views
        if m.likes < 500 and m.views < 50_000:
            continue
        external_urls = [u for u in p.urls if _is_external_url(u)]
        is_long_thread = len(p.text) > 280
        if external_urls or is_long_thread:
            article_items.append(BriefingItem(
                post=p,
                summary=clean_summary(p.text),
                category="Articles & Threads",
                score=s,
            ))
            article_authors.add(p.author_id)
            used_ids.add(p.id)
            if len(article_items) >= 4:
                break
    if article_items:
        sections.append(BriefingSection(title="ARTICLES & THREADS", emoji="📰", items=article_items))

    # Section 4: WORTH A LOOK — breakout posts + interesting outliers
    worth_scored = [(p, s) for p, s in scored if p.id not in used_ids and (p.id in breakouts or s > 0)]
    worth_scored = cap_posts_per_account(worth_scored)
    worth_items = []
    for p, s in worth_scored:
        worth_items.append(BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Worth a Look",
            score=s,
        ))
        used_ids.add(p.id)
        if len(worth_items) >= 5:
            break
    if worth_items:
        sections.append(BriefingSection(title="WORTH A LOOK", emoji="💡", items=worth_items))
    
    from datetime import timedelta
    return Briefing(
        generated_at=now,
        period_start=now - timedelta(hours=hours),
        period_end=now,
        sections=sections,
        stats={
            "posts_scanned": len(posts) + len(filtered_search),
            "accounts_tracked": len(users),
            "interests_detected": len(interests),
            "breakout_posts": len(breakouts),
        },
    )
