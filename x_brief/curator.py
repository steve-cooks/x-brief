"""Content curation and briefing assembly for X Brief."""

from collections import Counter
from datetime import datetime, timezone
import re

from x_brief.models import Briefing, BriefingItem, BriefingSection, Post, User
from x_brief.scorer import deduplicate, information_density_score, normalize_engagement_scores, score_post


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

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "at", "with", "from", "by", "is", "it", "this", "that",
    "as", "be", "are", "was", "were", "will", "can", "just", "your", "you", "we", "they", "our", "their", "about", "into",
    "new", "how", "why", "what", "when", "than", "then", "over", "under", "out", "all", "any", "more", "most", "very",
}


def clean_summary(text: str, max_len: int = 120) -> str:
    """Extract a clean summary from post text."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"^(@\w+\s*)+", "", text)
    text = " ".join(text.split()).strip()
    if len(text) > max_len:
        text = text[: max_len - 3].rsplit(" ", 1)[0] + "..."
    return text or "(media post)"


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


def _is_following_post(post: Post, tracked_accounts_set: set[str]) -> bool:
    if post.source == "following":
        return True
    if post.source is None and post.author_username.lower().lstrip("@") in tracked_accounts_set:
        return True
    return False


def _is_cant_miss(post: Post) -> bool:
    m = post.metrics
    return m.views > 500_000 and m.likes > 10_000


def extract_topic_tokens(post: Post) -> tuple[set[str], set[str]]:
    """
    Extract topic tokens from URLs, @mentions, hashtags, and top non-stopword terms.
    Returns (all_tokens, normalized_urls).
    """
    tokens: set[str] = set()

    text = post.text or ""
    found_urls = set(post.urls)
    found_urls.update(re.findall(r"https?://\S+", text))
    normalized_urls = {u.rstrip("/.,)") for u in found_urls if u}
    for url in normalized_urls:
        tokens.add(f"url:{url.lower()}")

    mentions = re.findall(r"@(\w+)", text.lower())
    for mention in mentions:
        tokens.add(f"@{mention}")

    hashtags = re.findall(r"#(\w+)", text.lower())
    for hashtag in hashtags:
        tokens.add(f"#{hashtag}")

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9']{2,}", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and not w.startswith("http")]
    top_terms = [w for w, _ in Counter(filtered).most_common(5)]
    for term in top_terms:
        tokens.add(term)

    return tokens, {u.lower() for u in normalized_urls}


def _same_topic(a: Post, b: Post, token_cache: dict[str, tuple[set[str], set[str]]]) -> bool:
    a_tokens, a_urls = token_cache[a.id]
    b_tokens, b_urls = token_cache[b.id]

    if a_urls and b_urls and (a_urls & b_urls):
        return True

    shared = len(a_tokens & b_tokens)
    return shared >= 2


def cluster_posts_by_topic(posts: list[Post]) -> list[list[Post]]:
    """Cluster posts by shared topic tokens or same URL."""
    if not posts:
        return []

    token_cache = {post.id: extract_topic_tokens(post) for post in posts}
    visited: set[str] = set()
    clusters: list[list[Post]] = []

    for post in posts:
        if post.id in visited:
            continue

        cluster = []
        stack = [post]
        visited.add(post.id)

        while stack:
            current = stack.pop()
            cluster.append(current)
            for candidate in posts:
                if candidate.id in visited:
                    continue
                if _same_topic(current, candidate, token_cache):
                    visited.add(candidate.id)
                    stack.append(candidate)

        clusters.append(cluster)

    return clusters


def _select_cluster_best(cluster: list[Post], scores: dict[str, float]) -> Post:
    """Pick best scored post; if any threads exist in cluster, prefer highest-scored thread."""
    threads = [p for p in cluster if len(p.thread_posts) >= 2]
    pool = threads if threads else cluster
    return max(pool, key=lambda p: scores.get(p.id, 0.0))


def _topic_diverse_ranked(posts: list[Post], scores: dict[str, float]) -> list[Post]:
    clusters = cluster_posts_by_topic(posts)
    winners = [_select_cluster_best(cluster, scores) for cluster in clusters]
    return sorted(winners, key=lambda p: scores.get(p.id, 0.0), reverse=True)


def curate_briefing(
    posts: list[Post],
    users: dict[str, User],
    interests: list[str],
    tracked_accounts: list[str] | None = None,
    hours: int = 24,
    search_posts: list[Post] | None = None,
    reemergent_post_ids: set[str] | None = None,
) -> Briefing:
    """Build a structured briefing with 3 sections: Can't Miss, For You, Following."""
    now = datetime.now(timezone.utc)
    tracked_accounts_set = {a.lower().lstrip("@") for a in (tracked_accounts or []) if a}
    reemergent_post_ids = reemergent_post_ids or set()

    merged_posts = deduplicate([*posts, *(search_posts or [])], section="general")
    recent_posts = [p for p in merged_posts if _within_hours(p, now, 48)]

    engagement_map = normalize_engagement_scores(recent_posts)
    density_map = {p.id: information_density_score(p) for p in recent_posts}

    sections: list[BriefingSection] = []
    selected_ids: set[str] = set()

    # 1) Can't Miss 🔥 (extreme virality only)
    cant_miss_candidates = [p for p in recent_posts if _is_cant_miss(p)]
    cant_miss_scored = sorted(
        cant_miss_candidates,
        key=lambda p: score_post(p, engagement_map.get(p.id, 0.0), tab="cant_miss"),
        reverse=True,
    )
    cant_miss_items = [
        BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Can't Miss",
            score=score_post(p, engagement_map.get(p.id, 0.0), tab="cant_miss"),
        )
        for p in cant_miss_scored[:5]
    ]
    sections.append(BriefingSection(title="Can't Miss 🔥", emoji="🔥", items=cant_miss_items))
    selected_ids.update(item.post.id for item in cant_miss_items)

    # 2) For You 📌 (interest-matched, topic-diverse, one per author)
    for_you_candidates = [
        p
        for p in recent_posts
        if p.id not in selected_ids
        and p.id not in reemergent_post_ids
        and _matches_interests(p, interests)
    ]
    for_you_scores = {
        p.id: (engagement_map.get(p.id, 0.0) * 0.4) + (density_map.get(p.id, 0.0) * 0.6)
        for p in for_you_candidates
    }
    for_you_topic_winners = _topic_diverse_ranked(for_you_candidates, for_you_scores)

    for_you_selected: list[Post] = []
    seen_authors: set[str] = set()
    for post in for_you_topic_winners:
        if post.author_id in seen_authors:
            continue
        for_you_selected.append(post)
        seen_authors.add(post.author_id)
        if len(for_you_selected) >= 10:
            break

    for_you_items = [
        BriefingItem(post=p, summary=clean_summary(p.text), category="For You", score=for_you_scores.get(p.id, 0.0))
        for p in for_you_selected
    ]
    sections.append(BriefingSection(title="For You 📌", emoji="📌", items=for_you_items))
    selected_ids.update(item.post.id for item in for_you_items)

    # 3) Following 👥 (source following, lower threshold, topic-diverse)
    following_candidates = [
        p
        for p in recent_posts
        if p.id not in selected_ids
        and p.id not in reemergent_post_ids
        and _is_following_post(p, tracked_accounts_set)
        and (p.metrics.likes >= 50 or p.metrics.views >= 500)
    ]
    following_scores = {
        p.id: (engagement_map.get(p.id, 0.0) * 0.5) + (density_map.get(p.id, 0.0) * 0.5)
        for p in following_candidates
    }
    following_topic_winners = _topic_diverse_ranked(following_candidates, following_scores)
    following_items = [
        BriefingItem(post=p, summary=clean_summary(p.text), category="Following", score=following_scores.get(p.id, 0.0))
        for p in following_topic_winners[:10]
    ]
    sections.append(BriefingSection(title="Following 👥", emoji="👥", items=following_items))

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
