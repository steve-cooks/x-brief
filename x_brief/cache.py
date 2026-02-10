"""
SQLite caching layer for X Brief
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .models import Post, User, PostMetrics


class Cache:
    """SQLite-based cache for posts and user lookups"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Posts cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at INTEGER NOT NULL
                )
            """)
            
            # Users cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    data TEXT NOT NULL,
                    cached_at INTEGER NOT NULL
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_cached_at 
                ON posts(cached_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_cached_at 
                ON users(cached_at)
            """)
            
            conn.commit()
    
    def cache_post(self, post: Post):
        """Cache a single post"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO posts (id, data, cached_at)
                VALUES (?, ?, ?)
            """, (
                post.id,
                post.model_dump_json(),
                int(datetime.now(timezone.utc).timestamp())
            ))
            
            conn.commit()
    
    def cache_posts(self, posts: list[Post]):
        """Cache multiple posts"""
        if not posts:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            now = int(datetime.now(timezone.utc).timestamp())
            
            cursor.executemany("""
                INSERT OR REPLACE INTO posts (id, data, cached_at)
                VALUES (?, ?, ?)
            """, [
                (post.id, post.model_dump_json(), now)
                for post in posts
            ])
            
            conn.commit()
    
    def get_post(self, post_id: str) -> Optional[Post]:
        """Get a cached post by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM posts WHERE id = ?
            """, (post_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Post.model_validate_json(row[0])
    
    def cache_user(self, user: User):
        """Cache a user"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO users (id, username, data, cached_at)
                VALUES (?, ?, ?, ?)
            """, (
                user.id,
                user.username,
                user.model_dump_json(),
                int(datetime.now(timezone.utc).timestamp())
            ))
            
            conn.commit()
    
    def cache_users(self, users: list[User]):
        """Cache multiple users"""
        if not users:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            now = int(datetime.now(timezone.utc).timestamp())
            
            cursor.executemany("""
                INSERT OR REPLACE INTO users (id, username, data, cached_at)
                VALUES (?, ?, ?, ?)
            """, [
                (user.id, user.username, user.model_dump_json(), now)
                for user in users
            ])
            
            conn.commit()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a cached user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return User.model_validate_json(row[0])
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a cached user by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT data FROM users WHERE username = ?
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return User.model_validate_json(row[0])
    
    def cleanup_expired(self, posts_ttl_hours: int = 48, users_ttl_days: int = 7):
        """Remove expired entries from cache"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            now = datetime.now(timezone.utc)
            
            # Clean up old posts (48h default)
            posts_cutoff = int((now - timedelta(hours=posts_ttl_hours)).timestamp())
            cursor.execute("""
                DELETE FROM posts WHERE cached_at < ?
            """, (posts_cutoff,))
            
            # Clean up old users (7d default)
            users_cutoff = int((now - timedelta(days=users_ttl_days)).timestamp())
            cursor.execute("""
                DELETE FROM users WHERE cached_at < ?
            """, (users_cutoff,))
            
            conn.commit()


async def get_or_fetch_user_id(
    cache: Cache,
    username: str,
    fetcher,  # XClient instance
) -> Optional[str]:
    """
    Get user ID from cache or fetch from API
    
    Args:
        cache: Cache instance
        username: Username to look up
        fetcher: XClient instance for API calls
    
    Returns:
        User ID or None if not found
    """
    # Check cache first
    cached_user = cache.get_user_by_username(username)
    if cached_user:
        return cached_user.id
    
    # Fetch from API
    user = await fetcher.get_user_by_username(username)
    if user:
        cache.cache_user(user)
        return user.id
    
    return None
