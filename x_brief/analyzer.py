"""Interest inference and post categorization for X Brief."""
import re
from collections import Counter
from x_brief.models import Post, User

# Keyword mappings for interest detection
INTEREST_KEYWORDS = {
    "AI & Tech": ["ai", "artificial intelligence", "llm", "gpt", "claude", "machine learning", "deep learning", "neural", "model", "openai", "anthropic", "agent", "coding", "developer", "software", "engineering", "api", "open source", "cursor", "copilot", "codex", "programming", "tech"],
    "Crypto & Web3": ["crypto", "bitcoin", "ethereum", "web3", "nft", "defi", "blockchain", "token", "sol", "solana", "wallet", "onchain"],
    "Startups & Business": ["startup", "founder", "building", "launch", "saas", "revenue", "growth", "product", "yc", "fundraise", "investor", "venture", "business", "entrepreneur", "ship"],
    "Design & UI": ["design", "ui", "ux", "figma", "css", "animation", "frontend", "pixel", "typography", "visual"],
    "Sports": ["tennis", "football", "basketball", "athlete", "match", "tournament", "grand slam", "atp", "nba", "nfl"],
    "Self-Improvement": ["mindset", "discipline", "focus", "productivity", "habits", "routine", "grind", "growth", "motivation", "quotes"],
    "Creator Economy": ["creator", "content", "audience", "community", "newsletter", "youtube", "podcast", "monetize", "whop"],
}

def infer_interests(users: list[User]) -> list[str]:
    """Infer interest categories from followed users' descriptions."""
    scores = Counter()
    for user in users:
        text = f"{user.description or ''} {user.name or ''}".lower()
        for interest, keywords in INTEREST_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    scores[interest] += 1
                    break
    # Return interests with at least 2 matching users, sorted by frequency
    return [interest for interest, count in scores.most_common() if count >= 2] or list(INTEREST_KEYWORDS.keys())[:5]

def categorize_posts(posts: list[Post], interests: list[str]) -> dict[str, list[Post]]:
    """Assign posts to interest categories based on text content."""
    categorized = {interest: [] for interest in interests}
    categorized["General"] = []
    
    for post in posts:
        text = post.text.lower()
        matched = False
        for interest in interests:
            keywords = INTEREST_KEYWORDS.get(interest, [])
            if any(kw in text for kw in keywords):
                categorized[interest].append(post)
                matched = True
        if not matched:
            categorized["General"].append(post)
    
    return {k: v for k, v in categorized.items() if v}

def detect_breakout_posts(posts: list[Post], threshold: float = 2.0) -> list[Post]:
    """Find posts with unusually high engagement."""
    if not posts:
        return []
    
    # Group by author
    by_author: dict[str, list[Post]] = {}
    for p in posts:
        by_author.setdefault(p.author_id, []).append(p)
    
    breakouts = []
    for author_id, author_posts in by_author.items():
        if len(author_posts) < 2:
            continue
        engagements = []
        for p in author_posts:
            m = p.metrics
            eng = (m.likes + m.reposts * 3 + m.replies * 2 + m.quotes * 4)
            engagements.append((p, eng))
        
        median_eng = sorted(e for _, e in engagements)[len(engagements) // 2]
        if median_eng == 0:
            median_eng = 1
        
        for p, eng in engagements:
            if eng > median_eng * threshold:
                breakouts.append(p)
    
    return breakouts

def build_search_queries(interests: list[str]) -> list[str]:
    """Convert interest categories into X API search queries with quality filters."""
    # Base filters for all queries:
    # - min_faves:10 = minimum 10 likes (filter low-quality at API level)
    # - -is:retweet = no retweets
    # - -is:reply = no replies, only original posts
    # - lang:en = English only
    # Note: min_followers not widely supported in X API basic search, so we filter in curator
    
    base_filters = "lang:en -is:retweet -is:reply min_faves:10"
    
    query_templates = {
        "AI & Tech": f"(AI OR LLM OR GPT OR Claude OR \"machine learning\" OR \"artificial intelligence\") {base_filters}",
        "Crypto & Web3": f"(crypto OR bitcoin OR ethereum OR web3 OR solana OR defi) {base_filters}",
        "Startups & Business": f"(startup OR founder OR \"just launched\" OR saas OR YC) {base_filters}",
        "Design & UI": f"(UI OR UX OR design OR figma OR \"frontend\") {base_filters}",
        "Sports": f"(tennis OR \"grand slam\" OR ATP OR match) {base_filters}",
        "Self-Improvement": f"(mindset OR discipline OR productivity OR habits) {base_filters}",
        "Creator Economy": f"(creator OR community OR newsletter OR audience) {base_filters}",
    }
    queries = []
    for interest in interests:
        if interest in query_templates:
            queries.append(query_templates[interest])
    return queries
