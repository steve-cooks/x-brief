"""Content curation and briefing assembly for X Brief."""
import re
from datetime import datetime, timezone
from x_brief.models import Post, User, Briefing, BriefingSection, BriefingItem
from x_brief.scorer import deduplicate, score_post, rank_posts
from x_brief.analyzer import categorize_posts, detect_breakout_posts

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
    
    # Section 1: TOP STORIES — highest scored overall (filter short posts)
    top_candidates = deduplicate([p for p, s in scored], section="top_stories")
    top_items = []
    for p in top_candidates:
        if p.id not in used_ids:
            # TOP STORIES requires meaningful engagement
            m = p.metrics
            if m.likes < 50 and m.reposts < 10 and m.views < 5000:
                continue
            user = users.get(p.author_id)
            followers = user.followers_count if user else 100
            s = score_post(p, followers)
            top_items.append(BriefingItem(
                post=p,
                summary=clean_summary(p.text),
                category="Top",
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
    
    # Section 4: WORTH A LOOK — breakout posts + interesting outliers
    worth_items = []
    for p, s in scored:
        if p.id not in used_ids and (p.id in breakouts or s > 0):
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
