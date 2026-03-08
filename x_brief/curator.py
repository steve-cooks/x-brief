"""Content curation and briefing assembly for X Brief."""

from datetime import datetime, timezone
import re

from x_brief.models import Briefing, BriefingItem, BriefingSection, Post, User
from x_brief.scorer import deduplicate, score_post


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


def detect_network_amplification(posts: list[Post], search_posts: list[Post]) -> dict[str, float]:
    """
    Detect when multiple followed accounts reference the same post/URL.
    Returns a dict of post_id -> boost multiplier for network-amplified posts.
    """
    _ = search_posts
    url_references: dict[str, list[str]] = {}

    for post in posts:
        quoted_matches = re.findall(r"https://(?:twitter|x)\.com/(\w+)/status/(\d+)", post.text)
        for _, status_id in quoted_matches:
            ref_key = f"status:{status_id}"
            if ref_key not in url_references:
                url_references[ref_key] = []
            if post.author_id not in url_references[ref_key]:
                url_references[ref_key].append(post.author_id)

        for url in post.urls:
            if "twitter.com" in url or "x.com" in url:
                continue
            if url not in url_references:
                url_references[url] = []
            if post.author_id not in url_references[url]:
                url_references[url].append(post.author_id)

    amplified_boosts: dict[str, float] = {}
    for ref_key, author_ids in url_references.items():
        if len(author_ids) >= 3 and ref_key.startswith("status:"):
            amplified_boosts[ref_key.replace("status:", "")] = 3.0

    return amplified_boosts


def clean_summary(text: str, max_len: int = 120) -> str:
    """Extract a clean summary from post text."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^(@\w+\s*)+", "", text)
    text = " ".join(text.split()).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return text or "(media post)"


def cap_posts_per_account(posts_with_scores: list[tuple[Post, float]], max_per_account: int = 2) -> list[tuple[Post, float]]:
    """Cap posts to max N per author_id, keeping highest scored ones."""
    from collections import defaultdict

    by_author = defaultdict(list)
    for post, score in posts_with_scores:
        by_author[post.author_id].append((post, score))

    result = []
    for author_posts in by_author.values():
        author_posts.sort(key=lambda x: x[1], reverse=True)
        result.extend(author_posts[:max_per_account])

    result.sort(key=lambda x: x[1], reverse=True)
    return result


def _within_hours(post: Post, now: datetime, hours: int) -> bool:
    age_hours = (now - post.created_at).total_seconds() / 3600
    return 0 <= age_hours <= hours


def _matches_interests(post: Post, interests: list[str]) -> bool:
    text = post.text.lower()
    for interest in interests:
        if not interest:
            continue
        keywords = INTEREST_KEYWORDS.get(interest, [interest.lower()])
        for keyword in keywords:
            normalized = keyword.lower().strip()
            if not normalized:
                continue
            if len(normalized) <= 3 and normalized.isalpha():
                if re.search(rf"\b{re.escape(normalized)}\b", text):
                    return True
            elif normalized in text:
                return True
    return False


def _is_viral_candidate(post: Post) -> bool:
    m = post.metrics
    return (
        m.views >= 500_000
        or m.likes >= 5_000
        or m.reposts >= 1_000
        or m.bookmarks >= 800
    )


def _viral_score(post: Post) -> float:
    m = post.metrics
    # absolute virality signals, no follower normalization
    return (
        m.views * 0.08
        + m.likes * 3.0
        + m.reposts * 7.0
        + m.bookmarks * 5.0
        + m.replies * 1.5
    )


def _top_picks_score(post: Post, followers: int) -> float:
    _ = followers
    m = post.metrics
    # Replies + bookmarks dominate this category by design.
    return (
        m.replies * 12.0
        + m.bookmarks * 15.0
        + m.reposts * 2.0
        + m.likes * 0.5
        + m.views * 0.005
    )


def _following_score(post: Post, followers: int) -> float:
    return _viral_score(post) * 0.7 + score_post(post, followers) * 0.3


def _is_following_post(post: Post, tracked_accounts_set: set[str]) -> bool:
    if post.source == "following":
        return True
    if post.source is None and post.author_username.lower().lstrip("@") in tracked_accounts_set:
        return True
    return False


def curate_briefing(
    posts: list[Post],
    users: dict[str, User],
    interests: list[str],
    tracked_accounts: list[str] | None = None,
    hours: int = 24,
    search_posts: list[Post] | None = None,
) -> Briefing:
    """Build a structured briefing with exactly 3 sections: VIRAL, TOP PICKS, FOLLOWING."""
    now = datetime.now(timezone.utc)
    tracked_accounts_set = {a.lower().lstrip("@") for a in (tracked_accounts or []) if a}

    # Merge all available sources and dedupe
    merged_posts = deduplicate([*posts, *(search_posts or [])], section="general")
    recent_posts = [p for p in merged_posts if _within_hours(p, now, 48)]

    sections: list[BriefingSection] = []
    remaining_posts = list(recent_posts)

    # 1) VIRAL 🔥
    viral_scored = [
        (p, _viral_score(p))
        for p in remaining_posts
        if _is_viral_candidate(p)
    ]
    viral_scored.sort(key=lambda x: x[1], reverse=True)
    viral_scored = cap_posts_per_account(viral_scored, max_per_account=2)
    viral_items = [
        BriefingItem(post=p, summary=clean_summary(p.text), category="Viral", score=s)
        for p, s in viral_scored[:10]
    ]
    if viral_items:
        sections.append(BriefingSection(title="VIRAL 🔥", emoji="🔥", items=viral_items))
        viral_ids = {item.post.id for item in viral_items}
        remaining_posts = [p for p in remaining_posts if p.id not in viral_ids]

    # 2) TOP PICKS 📌 (niche + heavy replies/bookmarks)
    top_picks_candidates = []
    for p in remaining_posts:
        if not _matches_interests(p, interests):
            continue
        user = users.get(p.author_id)
        followers = user.followers_count if user else 1000
        top_picks_candidates.append((p, _top_picks_score(p, followers)))
    top_picks_candidates.sort(key=lambda x: x[1], reverse=True)
    top_picks_candidates = cap_posts_per_account(top_picks_candidates, max_per_account=2)
    top_picks_items = [
        BriefingItem(post=p, summary=clean_summary(p.text), category="Top Picks", score=s)
        for p, s in top_picks_candidates[:10]
    ]
    if top_picks_items:
        sections.append(BriefingSection(title="TOP PICKS 📌", emoji="📌", items=top_picks_items))
        top_picks_ids = {item.post.id for item in top_picks_items}
        remaining_posts = [p for p in remaining_posts if p.id not in top_picks_ids]

    # 3) FOLLOWING 👥 (source=following; fallback tracked accounts when source missing)
    following_candidates = []
    for p in remaining_posts:
        if not _is_following_post(p, tracked_accounts_set):
            continue
        user = users.get(p.author_id)
        followers = user.followers_count if user else 1000
        following_candidates.append((p, _following_score(p, followers)))
    following_candidates.sort(key=lambda x: x[1], reverse=True)
    following_candidates = cap_posts_per_account(following_candidates, max_per_account=2)
    following_items = [
        BriefingItem(post=p, summary=clean_summary(p.text), category="Following", score=s)
        for p, s in following_candidates[:10]
    ]
    if following_items:
        sections.append(BriefingSection(title="FOLLOWING 👥", emoji="👥", items=following_items))

    from datetime import timedelta

    return Briefing(
        generated_at=now,
        period_start=now - timedelta(hours=hours),
        period_end=now,
        sections=sections,
        stats={
            "posts_scanned": len(recent_posts),
            "accounts_tracked": len(users),
            "interests_detected": len(interests),
            "breakout_posts": 0,
        },
    )
