"""
Data models for X Brief using Pydantic v2
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PostMetrics(BaseModel):
    """Engagement metrics for a post"""
    likes: int = 0
    reposts: int = 0
    replies: int = 0
    views: int = 0
    quotes: int = 0


class PostMedia(BaseModel):
    """Media attachment in a post"""
    type: str  # "photo", "video", "animated_gif"
    url: Optional[str] = None
    preview_image_url: Optional[str] = None
    video_url: Optional[str] = None  # Best quality mp4 for videos/gifs
    alt_text: Optional[str] = None
    variants: list[dict] = Field(default_factory=list)  # For videos/gifs


class QuotedPost(BaseModel):
    """Represents a quoted tweet embedded in a post"""
    id: Optional[str] = None
    text: str = ""
    author_username: str = ""
    author_name: str = ""
    metrics: Optional[PostMetrics] = None
    post_url: Optional[str] = None


class Post(BaseModel):
    """Represents a post/tweet from X"""
    id: str
    text: str
    author_id: str
    author_username: str
    author_name: str
    created_at: datetime
    metrics: PostMetrics
    media: list[PostMedia] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)  # Deprecated, kept for compatibility
    urls: list[str] = Field(default_factory=list)
    is_repost: bool = False
    is_quote: bool = False
    quoted_post_id: Optional[str] = None
    quoted_post: Optional[QuotedPost] = None
    conversation_id: Optional[str] = None
    lang: Optional[str] = None


class User(BaseModel):
    """Represents a user/account on X"""
    id: str
    username: str
    name: str
    description: Optional[str] = None
    followers_count: int = 0
    verified: bool = False
    verified_type: Optional[str] = None  # "blue", "business", "government"
    profile_image_url: Optional[str] = None


class BriefingItem(BaseModel):
    """Single item in a briefing section"""
    post: Post
    summary: str
    category: str
    score: float


class BriefingSection(BaseModel):
    """Section of a briefing (e.g., Top Stories, Your Circle)"""
    title: str
    emoji: str
    items: list[BriefingItem] = Field(default_factory=list)


class Briefing(BaseModel):
    """Complete briefing document"""
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    sections: list[BriefingSection] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class UserConfig(BaseModel):
    """User configuration for X Brief"""
    x_handle: Optional[str] = None
    tracked_accounts: list[str] = Field(default_factory=list)
    recent_interests: list[str] = Field(default_factory=list, description="Optional topics not covered by followings")
    delivery: dict = Field(default_factory=dict)
    briefing_schedule: str = "daily"
