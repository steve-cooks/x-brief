"""Content curation and briefing assembly for X Brief."""
import re
from collections import Counter
from datetime import datetime, timezone
from x_brief.models import Post, User, Briefing, BriefingSection, BriefingItem
from x_brief.scorer import deduplicate, score_post, rank_posts, is_mega_viral
from x_brief.analyzer import categorize_posts, detect_breakout_posts

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
    hours: int = 24,
    search_posts: list[Post] | None = None,
) -> Briefing:
    """Build a structured briefing from fetched posts."""
    now = datetime.now(timezone.utc)
    
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
            # TOP STORIES requires meaningful engagement
            m = p.metrics
            if m.likes < 50 and m.reposts < 10 and m.views < 5000:
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
    
    # Section 2: YOUR CIRCLE — posts from tracked accounts by category
    circle_items = []
    for interest, cat_posts in categorized.items():
        if interest == "General":
            continue
        for p in cat_posts[:3]:
            if p.id not in used_ids:
                user = users.get(p.author_id)
                s = score_post(p, user.followers_count if user else 100)
                circle_items.append(BriefingItem(
                    post=p,
                    summary=clean_summary(p.text),
                    category=interest,
                    score=s,
                ))
                used_ids.add(p.id)
    circle_items.sort(key=lambda x: x.score, reverse=True)
    if circle_items:
        sections.append(BriefingSection(title="YOUR CIRCLE", emoji="👥", items=circle_items[:10]))
    
    # Section 3: TRENDING IN YOUR NICHES — from search results (already filtered by engagement & score > 0)
    search_scored = cap_posts_per_account(search_scored)
    trend_items = []
    for p, s in search_scored[:8]:
        if p.id not in used_ids:
            trend_items.append(BriefingItem(
                post=p,
                summary=clean_summary(p.text),
                category="Trending",
                score=s,
            ))
            used_ids.add(p.id)
    if trend_items:
        sections.append(BriefingSection(title="TRENDING IN YOUR NICHES", emoji="🔥", items=trend_items))
    
    # Section 3.5: ARTICLES & THREADS — posts with external URLs or long text
    article_items = []
    article_authors: set[str] = set()
    for p, s in scored:
        if p.id in used_ids:
            continue
        if p.author_id in article_authors:
            continue  # cap 1 per account
        m = p.metrics
        # Must meet minimum engagement: 500 likes or 50K views
        if m.likes < 500 and m.views < 50_000:
            continue
        # Detect articles: external URLs (not x.com/twitter.com)
        external_urls = [
            u for u in p.urls
            if 'x.com' not in u and 'twitter.com' not in u and 't.co' not in u
        ]
        is_long_thread = len(p.text) > 280
        has_article = len(external_urls) > 0
        if has_article or is_long_thread:
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
