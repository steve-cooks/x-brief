"""
Content scoring and deduplication for X Brief
"""

import re
import math
from datetime import datetime, timezone
from typing import Optional
from .models import Post, User


# Mega-viral thresholds - posts meeting ANY of these are considered mega-viral
MEGA_VIRAL_VIEWS = 1_000_000
MEGA_VIRAL_LIKES = 10_000
MEGA_VIRAL_REPOSTS = 5_000

# Graduated viral thresholds for scoring boosts
VIRAL_VIEWS_100K = 100_000
VIRAL_VIEWS_1M = 1_000_000
VIRAL_VIEWS_10M = 10_000_000


def is_mega_viral(post: Post) -> bool:
    """Check if a post meets mega-viral thresholds."""
    m = post.metrics
    return (
        m.views >= MEGA_VIRAL_VIEWS or
        m.likes >= MEGA_VIRAL_LIKES or
        m.reposts >= MEGA_VIRAL_REPOSTS
    )


def get_viral_multiplier(post: Post) -> float:
    """Get the viral multiplier based on views (graduated scale)."""
    views = post.metrics.views
    if views >= VIRAL_VIEWS_10M:
        return 10.0
    elif views >= VIRAL_VIEWS_1M:
        return 5.0
    elif views >= VIRAL_VIEWS_100K:
        return 2.0
    return 1.0


def deduplicate(posts: list[Post], section: str = "general") -> list[Post]:
    """
    Remove exact duplicates and group reposts/quotes
    Returns unique posts, preferring originals over reposts
    
    Args:
        posts: List of posts to deduplicate
        section: Section name for filtering rules ("top_stories" or "general")
    """
    seen_ids = set()
    seen_text = set()
    quote_originals = {}  # Map quoted post ID to best quote-tweet
    unique_posts = []
    
    # Sort to process original posts before reposts
    sorted_posts = sorted(posts, key=lambda p: (p.is_repost, p.created_at))
    
    for post in sorted_posts:
        # Skip if we've seen this exact post ID
        if post.id in seen_ids:
            continue
        
        # Skip reposts that are just "RT @..." format
        if post.is_repost or post.text.strip().startswith("RT @"):
            continue
        
        # For TOP STORIES section: skip very short posts (just emojis/lol)
        # Check the text after removing URLs and mentions to catch posts like "👀 https://..."
        if section == "top_stories":
            # Remove URLs
            cleaned_text = re.sub(r'https?://\S+', '', post.text)
            # Remove @mentions
            cleaned_text = re.sub(r'@\w+', '', cleaned_text)
            # Clean whitespace
            cleaned_text = cleaned_text.strip()
            if len(cleaned_text) < 10:
                continue
        
        # Skip reposts if we've seen the original text
        if post.text in seen_text:
            continue
        
        # Group quote-tweets of the same original (keep highest scored one)
        # Detect if this is a quote-tweet by checking for quoted post patterns
        quoted_match = re.search(r'https://(?:twitter|x)\.com/\w+/status/(\d+)', post.text)
        if quoted_match:
            quoted_id = quoted_match.group(1)
            # Calculate score for comparison (simplified, will be refined later)
            current_score = post.metrics.likes + post.metrics.reposts * 3
            
            if quoted_id in quote_originals:
                existing_post, existing_score = quote_originals[quoted_id]
                if current_score > existing_score:
                    # Replace with higher scored quote-tweet
                    quote_originals[quoted_id] = (post, current_score)
                    # Remove the old one from unique_posts
                    if existing_post in unique_posts:
                        unique_posts.remove(existing_post)
                        seen_ids.discard(existing_post.id)
                        seen_text.discard(existing_post.text)
                else:
                    continue  # Skip this lower-scored quote-tweet
            else:
                quote_originals[quoted_id] = (post, current_score)
        
        seen_ids.add(post.id)
        seen_text.add(post.text)
        unique_posts.append(post)
    
    return unique_posts


def score_post(post: Post, followers_count: int) -> float:
    """
    Calculate engagement velocity score for a post with time decay
    
    Formula: weighted engagement with log-scale follower normalization and time decay
    - views: 0.1 weight
    - likes: 1 weight
    - reposts: 3 weight
    - replies: 2 weight
    - quotes: 4 weight
    
    Time decay factor:
    - Last 6h: 2x boost
    - 6-12h: 1.5x boost
    - 12-24h: 1x (no change)
    - 24-48h: 0.7x penalty
    
    Follower normalization uses log scale so viral posts from small accounts rank higher
    """
    metrics = post.metrics
    
    # Weighted engagement score
    engagement = (
        metrics.views * 0.1 +
        metrics.likes * 1.0 +
        metrics.reposts * 3.0 +
        metrics.replies * 2.0 +
        metrics.quotes * 4.0
    )
    
    # Log-scale follower normalization
    # A post with 100 likes from 500 followers scores higher than 100 likes from 500K followers
    # Using log10 to compress the follower scale
    followers = max(followers_count, 1)
    follower_factor = math.log10(followers + 1)  # +1 to avoid log(0)
    normalized_score = engagement / max(follower_factor, 1)
    
    # Time decay factor
    now = datetime.now(timezone.utc)
    post_age_hours = (now - post.created_at).total_seconds() / 3600
    
    if post_age_hours <= 6:
        time_factor = 2.0
    elif post_age_hours <= 12:
        time_factor = 1.5
    elif post_age_hours <= 24:
        time_factor = 1.0
    else:  # 24-48h
        time_factor = 0.7
    
    normalized_score *= time_factor
    
    # Boost for high absolute engagement
    if metrics.likes > 1000:
        normalized_score *= 1.5
    if metrics.reposts > 500:
        normalized_score *= 1.3
    
    # Apply graduated viral multiplier based on views
    viral_mult = get_viral_multiplier(post)
    normalized_score *= viral_mult
    
    # Additional 5x boost for mega-viral posts (on top of viral multiplier)
    if is_mega_viral(post):
        normalized_score *= 5.0
    
    return normalized_score


def rank_posts(posts: list[Post], users_map: dict[str, User]) -> list[Post]:
    """
    Rank posts by engagement score
    
    Args:
        posts: List of posts to rank
        users_map: Map of user_id -> User for follower counts
    
    Returns:
        Posts sorted by score (highest first)
    """
    scored_posts = []
    
    for post in posts:
        # Get author's follower count
        author = users_map.get(post.author_id)
        followers = author.followers_count if author else 1
        
        # Calculate score
        score = score_post(post, followers)
        
        # Store with score for sorting
        scored_posts.append((score, post))
    
    # Sort by score descending
    scored_posts.sort(key=lambda x: x[0], reverse=True)
    
    # Return just the posts
    return [post for score, post in scored_posts]
