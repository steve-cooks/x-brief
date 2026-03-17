"""Curation engine for assembling the 3-tab X Brief output.

WHY: the product promise is "5 useful minutes, then get off the app." This
module enforces breadth (topic clustering), substance (density-aware scoring),
and anti-dopamine guards (Can't Miss quality gates) so briefs stay genuinely
useful instead of becoming another engagement feed.
"""

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

TLDR_CATEGORY_ALIASES = {
    "AI & Tech": "AI",
    "Crypto & Web3": "crypto",
    "Startups & Business": "startups",
    "Design & UI": "design",
    "Sports": "sports",
    "Self-Improvement": "self-improvement",
    "Creator Economy": "the creator economy",
}

TLDR_BLOCKLIST = STOPWORDS | {
    "amp",
    "app",
    "article",
    "breaking",
    "check",
    "content",
    "day",
    "days",
    "everyone",
    "feed",
    "good",
    "great",
    "here",
    "latest",
    "look",
    "mostly",
    "news",
    "nothing",
    "people",
    "post",
    "posts",
    "read",
    "scan",
    "story",
    "stuff",
    "thread",
    "threads",
    "timeline",
    "today",
    "tweet",
    "tweets",
    "viral",
    "week",
    "weeks",
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
    """Gate for globally important posts.

    WHY: this tab should feel rare and trustworthy. A post must clear all three
    bars: substantial content (density), extreme absolute reach, and quality
    interaction ratio (bookmarks+replies vs likes). This blocks hollow
    fame-driven virality from dominating the brief.
    """
    m = post.metrics
    density = information_density_score(post)

    # Gate 1: Must have substance (density >= 3 means has a link, thread, or real content)
    if density < 3:
        return False

    # Gate 2: Must have strong absolute engagement
    if m.likes < 10_000 or m.views < 500_000:
        return False

    # Gate 3: Quality ratio — bookmarks+replies relative to likes
    # High bookmark ratio = people saving it (useful). High reply ratio = discussion (substance).
    # Shitposts get lots of likes but few bookmarks/replies relative to likes.
    quality_signals = m.bookmarks + m.replies
    if m.likes > 0 and quality_signals / m.likes < 0.05:
        return False

    return True


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
    """Return one best post per topic cluster, globally ranked by score.

    WHY: without this step, one announcement can occupy multiple slots and
    destroy briefing breadth.
    """
    clusters = cluster_posts_by_topic(posts)
    winners = [_select_cluster_best(cluster, scores) for cluster in clusters]
    return sorted(winners, key=lambda p: scores.get(p.id, 0.0), reverse=True)


def _topic_labels_for_post(post: Post) -> list[str]:
    text = (post.text or "").lower()
    labels: list[str] = []

    for category, keywords in INTEREST_KEYWORDS.items():
        for keyword in keywords:
            normalized = keyword.lower().strip()
            if not normalized:
                continue
            if len(normalized) <= 3 and normalized.isalpha():
                matched = re.search(rf"\b{re.escape(normalized)}\b", text)
            else:
                matched = normalized in text
            if matched:
                labels.append(TLDR_CATEGORY_ALIASES.get(category, category.lower()))
                break

    for hashtag in re.findall(r"#(\w+)", text):
        if hashtag and hashtag not in TLDR_BLOCKLIST:
            labels.append(f"#{hashtag}")

    for mention in re.findall(r"@(\w+)", text):
        if mention and mention not in TLDR_BLOCKLIST:
            labels.append(f"@{mention}")

    words = re.findall(r"[a-zA-Z][a-zA-Z0-9']{3,}", text)
    for word in words:
        normalized = word.strip("'").lower()
        if normalized and normalized not in TLDR_BLOCKLIST and not normalized.startswith("http"):
            labels.append(normalized)

    unique_labels: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        unique_labels.append(label)
        if len(unique_labels) >= 5:
            break

    return unique_labels


def _join_tldr_topics(topics: list[str]) -> str:
    if not topics:
        return "whatever the timeline is doing"
    if len(topics) == 1:
        return topics[0]
    return f"{topics[0]} and {topics[1]}"


_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+")
_TLDR_TRIM_PREFIXES = (
    "new:",
    "breaking:",
    "update:",
    "thread:",
    "psa:",
    "note:",
)
_TLDR_ANNOUNCEMENT_WORDS = (
    "announce",
    "announced",
    "announcing",
    "launch",
    "launched",
    "launching",
    "release",
    "released",
    "rolling out",
    "rolled out",
    "ship",
    "shipped",
    "drop",
    "dropped",
    "open source",
    "open-sourced",
    "double",
    "doubled",
    "delay",
    "delayed",
    "raise",
    "raised",
)
_TLDR_DEBATE_WORDS = (
    "arguing",
    "debate",
    "discourse",
    "fighting",
    "mad about",
    "whether",
    "vs",
)
_TLDR_OPINION_WORDS = (
    "i think",
    "i believe",
    "hot take",
    "unpopular opinion",
    "opinion",
    "take:",
)


def _tldr_author_label(post: Post) -> str:
    author_name = (post.author_name or "").replace(" (pinned)", "").strip()
    if author_name:
        return author_name

    username = (post.author_username or "").replace(" (pinned)", "").strip().lstrip("@")
    if username:
        return f"@{username}"

    return "Someone"


def _clean_tldr_source_text(text: str) -> str:
    cleaned = clean_summary(text, max_len=180)
    cleaned = _EMOJI_RE.sub("", cleaned)
    cleaned = re.sub(r"^(@\w+\s+)+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;.!?\"'")

    for prefix in _TLDR_TRIM_PREFIXES:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" -,:;")
            break

    return cleaned


def _first_meaningful_clause(text: str, max_len: int = 60) -> str:
    if not text or text == "(media post)":
        return ""

    sentence = re.split(r"[.!?]", text, maxsplit=1)[0].strip()
    clause = sentence

    for separator in (",", ";", " - ", " — ", ": "):
        index = clause.find(separator)
        if 0 < index <= max_len:
            clause = clause[:index].strip()
            break

    if len(clause) > max_len:
        clause = clause[:max_len].rsplit(" ", 1)[0].strip()

    return clause.strip(" -,:;.!?\"'")


def _rewrite_lead_clause(author: str, post: Post) -> str:
    clause = _first_meaningful_clause(_clean_tldr_source_text(post.text))
    if not clause:
        return ""

    lower_clause = clause.lower()
    author_variants = {
        author.lower(),
        author.lower().lstrip("@"),
        f"@{post.author_username.lower().lstrip('@')}",
        post.author_username.lower().lstrip("@"),
    }
    for variant in sorted((v for v in author_variants if v), key=len, reverse=True):
        if lower_clause.startswith(f"{variant} "):
            clause = clause[len(variant):].strip(" -,:;")
            lower_clause = clause.lower()
            break

    rewrites = (
        (r"^announcing\s+", "announced "),
        (r"^introducing\s+", "introduced "),
        (r"^launching\s+", "launched "),
        (r"^dropping\s+", "dropped "),
        (r"^shipping\s+", "shipped "),
        (r"^rolling out\s+", "rolled out "),
        (r"^doubling\s+", "doubled "),
        (r"^delaying\s+", "delayed "),
    )
    for pattern, replacement in rewrites:
        updated = re.sub(pattern, replacement, clause, count=1, flags=re.IGNORECASE)
        if updated != clause:
            clause = updated
            lower_clause = clause.lower()
            break

    if lower_clause.startswith("i think "):
        rest = clause[len("i think "):].strip()
        return f"{author} says {rest}" if rest else f"{author} says something worth a look"

    if lower_clause.startswith("i believe "):
        rest = clause[len("i believe "):].strip()
        return f"{author} says {rest}" if rest else f"{author} says something worth a look"

    if lower_clause.startswith("i "):
        rest = clause[2:].strip()
        return f"{author} says they {rest}" if rest else f"{author} says something worth a look"

    if lower_clause.startswith(("we ", "we're ", "we are ", "our ")):
        return f"{author} says {clause}"

    return f"{author} {clause}"


def _classify_tldr_fragment(fragment: str) -> str:
    lower = fragment.lower()
    if any(word in lower for word in _TLDR_DEBATE_WORDS) or "?" in fragment:
        return "debate"
    if any(word in lower for word in _TLDR_OPINION_WORDS):
        return "opinion"
    if any(word in lower for word in _TLDR_ANNOUNCEMENT_WORDS):
        return "announcement"
    return "neutral"


def _rank_tldr_items(
    cant_miss_items: list[BriefingItem],
    for_you_items: list[BriefingItem],
    following_items: list[BriefingItem],
) -> list[BriefingItem]:
    ranked: list[tuple[int, float, BriefingItem]] = []
    for priority, items in enumerate((cant_miss_items, for_you_items, following_items)):
        for item in items:
            ranked.append((priority, item.score, item))

    return [item for _, _, item in sorted(ranked, key=lambda row: (row[0], -row[1]))]


def _join_tldr_fragments(fragments: list[str]) -> str:
    if not fragments:
        return "Slow day - not much worth recapping."

    if len(fragments) == 1:
        return f"Slow day - {fragments[0]}."

    if len(fragments) < 3:
        return f"Slow day - {fragments[0]} and {fragments[1]}."

    third_kind = _classify_tldr_fragment(fragments[2])
    if third_kind == "debate":
        return f"{fragments[0]}, {fragments[1]}, while {fragments[2]}."

    second_kind = _classify_tldr_fragment(fragments[1])
    if second_kind == "debate":
        return f"{fragments[0]}, while {fragments[1]}, and {fragments[2]}."

    return f"{fragments[0]}, {fragments[1]}, and {fragments[2]}."


def _build_tldr(
    cant_miss_items: list[BriefingItem],
    for_you_items: list[BriefingItem],
    following_items: list[BriefingItem],
) -> str:
    ranked_items = _rank_tldr_items(cant_miss_items, for_you_items, following_items)

    fragments: list[str] = []
    seen_fragments: set[str] = set()
    for item in ranked_items:
        author = _tldr_author_label(item.post)
        fragment = _rewrite_lead_clause(author, item.post)
        if not fragment:
            continue

        normalized = fragment.lower()
        if normalized in seen_fragments:
            continue

        seen_fragments.add(normalized)
        fragments.append(fragment)
        if len(fragments) >= 3:
            break

    return _join_tldr_fragments(fragments)


def curate_briefing(
    posts: list[Post],
    users: dict[str, User],
    interests: list[str],
    tracked_accounts: list[str] | None = None,
    hours: int = 24,
    search_posts: list[Post] | None = None,
    reemergent_post_ids: set[str] | None = None,
) -> Briefing:
    """Build the final 3-tab briefing contract consumed by the web UI.

    WHY this order matters:
    1) Can't Miss claims the rare globally significant items first.
    2) For You then fills with interest-matched, topic-diverse substance.
    3) Following rounds out with posts from intentionally tracked voices.

    Selected IDs are excluded from later tabs so users do not re-read the same
    post across sections.
    """
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
    # Max 1 per author in Can't Miss
    cant_miss_selected: list[Post] = []
    cant_miss_authors: set[str] = set()
    for p in cant_miss_scored:
        if p.author_id in cant_miss_authors:
            continue
        cant_miss_selected.append(p)
        cant_miss_authors.add(p.author_id)
        if len(cant_miss_selected) >= 5:
            break

    cant_miss_items = [
        BriefingItem(
            post=p,
            summary=clean_summary(p.text),
            category="Can't Miss",
            score=score_post(p, engagement_map.get(p.id, 0.0), tab="cant_miss"),
        )
        for p in cant_miss_selected
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
        tldr=_build_tldr(cant_miss_items, for_you_items, following_items),
    )
