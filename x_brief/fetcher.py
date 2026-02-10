"""
X API v2 async client with rate limiting and pagination support
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
import httpx

from .models import Post, User, PostMetrics


class RateLimitError(Exception):
    """Raised when rate limit is exceeded"""
    pass


class XClient:
    """Async client for X API v2"""
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def _check_rate_limit(self, response: httpx.Response):
        """Check rate limit headers and raise if exceeded"""
        remaining = response.headers.get("x-rate-limit-remaining")
        reset = response.headers.get("x-rate-limit-reset")
        
        if remaining and int(remaining) == 0:
            reset_time = datetime.fromtimestamp(int(reset), tz=timezone.utc) if reset else None
            raise RateLimitError(f"Rate limit exceeded. Resets at {reset_time}")
    
    def _parse_user(self, user_data: dict) -> User:
        """Parse X API user data into User model"""
        metrics = user_data.get("public_metrics", {})
        return User(
            id=user_data["id"],
            username=user_data["username"],
            name=user_data["name"],
            description=user_data.get("description"),
            followers_count=metrics.get("followers_count", 0),
            verified=user_data.get("verified", False),
        )
    
    def _parse_post(
        self, 
        tweet_data: dict, 
        users_map: dict[str, dict],
        tweets_map: dict[str, dict]
    ) -> Post:
        """Parse X API tweet data into Post model"""
        author_id = tweet_data["author_id"]
        author_data = users_map.get(author_id, {})
        
        # Parse metrics
        metrics_data = tweet_data.get("public_metrics", {})
        metrics = PostMetrics(
            likes=metrics_data.get("like_count", 0),
            reposts=metrics_data.get("retweet_count", 0),
            replies=metrics_data.get("reply_count", 0),
            views=metrics_data.get("impression_count", 0),
            quotes=metrics_data.get("quote_count", 0),
        )
        
        # Parse media and URLs
        entities = tweet_data.get("entities", {})
        media_urls = []
        urls = []
        
        if "urls" in entities:
            urls = [url["expanded_url"] for url in entities["urls"] if url.get("expanded_url")]
        
        # Check if repost or quote
        referenced_tweets = tweet_data.get("referenced_tweets", [])
        is_repost = any(ref["type"] == "retweeted" for ref in referenced_tweets)
        is_quote = any(ref["type"] == "quoted" for ref in referenced_tweets)
        quoted_post_id = None
        
        if is_quote:
            for ref in referenced_tweets:
                if ref["type"] == "quoted":
                    quoted_post_id = ref["id"]
                    break
        
        return Post(
            id=tweet_data["id"],
            text=tweet_data["text"],
            author_id=author_id,
            author_username=author_data.get("username", "unknown"),
            author_name=author_data.get("name", "Unknown"),
            created_at=datetime.fromisoformat(tweet_data["created_at"].replace("Z", "+00:00")),
            metrics=metrics,
            media_urls=media_urls,
            urls=urls,
            is_repost=is_repost,
            is_quote=is_quote,
            quoted_post_id=quoted_post_id,
            conversation_id=tweet_data.get("conversation_id"),
            lang=tweet_data.get("lang"),
        )
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        url = f"{self.BASE_URL}/users/by/username/{username}"
        params = {
            "user.fields": "id,username,name,description,public_metrics,verified"
        }
        
        try:
            response = await self.client.get(url, params=params)
            self._check_rate_limit(response)
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if "data" not in data:
                return None
            
            return self._parse_user(data["data"])
        
        except httpx.HTTPError as e:
            print(f"Error fetching user {username}: {e}")
            return None
    
    async def get_users_by_usernames(self, usernames: list[str]) -> list[User]:
        """Get multiple users by usernames (batch, max 100)"""
        if not usernames:
            return []
        
        # X API allows max 100 usernames per request
        if len(usernames) > 100:
            usernames = usernames[:100]
        
        url = f"{self.BASE_URL}/users/by"
        params = {
            "usernames": ",".join(usernames),
            "user.fields": "id,username,name,description,public_metrics,verified"
        }
        
        try:
            response = await self.client.get(url, params=params)
            self._check_rate_limit(response)
            response.raise_for_status()
            
            data = response.json()
            users = []
            
            if "data" in data:
                for user_data in data["data"]:
                    users.append(self._parse_user(user_data))
            
            return users
        
        except httpx.HTTPError as e:
            print(f"Error fetching users: {e}")
            return []
    
    async def get_user_tweets(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100,
    ) -> list[Post]:
        """Get tweets from a user's timeline with pagination support"""
        url = f"{self.BASE_URL}/users/{user_id}/tweets"
        
        params = {
            "max_results": min(max_results, 100),  # API max is 100
            "tweet.fields": "id,text,created_at,public_metrics,entities,referenced_tweets,author_id,conversation_id,lang",
            "user.fields": "id,username,name,description,public_metrics,verified",
            "expansions": "author_id,referenced_tweets.id",
        }
        
        if start_time:
            params["start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_time:
            params["end_time"] = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        all_posts = []
        
        try:
            while True:
                response = await self.client.get(url, params=params)
                self._check_rate_limit(response)
                response.raise_for_status()
                
                data = response.json()
                
                if "data" not in data or not data["data"]:
                    break
                
                # Build users map from includes
                users_map = {}
                tweets_map = {}
                
                if "includes" in data:
                    if "users" in data["includes"]:
                        for user in data["includes"]["users"]:
                            users_map[user["id"]] = user
                    if "tweets" in data["includes"]:
                        for tweet in data["includes"]["tweets"]:
                            tweets_map[tweet["id"]] = tweet
                
                # Parse tweets
                for tweet_data in data["data"]:
                    post = self._parse_post(tweet_data, users_map, tweets_map)
                    all_posts.append(post)
                
                # Check for pagination
                if "meta" in data and "next_token" in data["meta"]:
                    params["pagination_token"] = data["meta"]["next_token"]
                    
                    # Stop if we've reached max_results
                    if len(all_posts) >= max_results:
                        break
                else:
                    break
        
        except httpx.HTTPError as e:
            print(f"Error fetching tweets for user {user_id}: {e}")
        
        return all_posts[:max_results]
    
    async def search_tweets(
        self,
        query: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100,
    ) -> list[Post]:
        """Search tweets with pagination support"""
        url = f"{self.BASE_URL}/tweets/search/recent"
        
        params = {
            "query": query,
            "max_results": min(max_results, 100),
            "tweet.fields": "id,text,created_at,public_metrics,entities,referenced_tweets,author_id,conversation_id,lang",
            "user.fields": "id,username,name,description,public_metrics,verified",
            "expansions": "author_id,referenced_tweets.id",
        }
        
        if start_time:
            params["start_time"] = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_time:
            params["end_time"] = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        all_posts = []
        
        try:
            while True:
                response = await self.client.get(url, params=params)
                self._check_rate_limit(response)
                response.raise_for_status()
                
                data = response.json()
                
                if "data" not in data or not data["data"]:
                    break
                
                # Build users map from includes
                users_map = {}
                tweets_map = {}
                
                if "includes" in data:
                    if "users" in data["includes"]:
                        for user in data["includes"]["users"]:
                            users_map[user["id"]] = user
                    if "tweets" in data["includes"]:
                        for tweet in data["includes"]["tweets"]:
                            tweets_map[tweet["id"]] = tweet
                
                # Parse tweets
                for tweet_data in data["data"]:
                    post = self._parse_post(tweet_data, users_map, tweets_map)
                    all_posts.append(post)
                
                # Check for pagination
                if "meta" in data and "next_token" in data["meta"]:
                    params["pagination_token"] = data["meta"]["next_token"]
                    
                    # Stop if we've reached max_results
                    if len(all_posts) >= max_results:
                        break
                else:
                    break
        
        except httpx.HTTPError as e:
            print(f"Error searching tweets for query '{query}': {e}")
        
        return all_posts[:max_results]
