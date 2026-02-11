# 𝕏 Brief

AI-powered X/Twitter timeline curator and briefing generator.

## What Was Built (Phase 1 - Core Engine)

### ✅ Complete Files

1. **pyproject.toml** - Python package configuration
   - Package name: `x-brief`
   - Dependencies: httpx, sqlite-utils, pydantic, click, jinja2
   - CLI entry point: `x-brief`

2. **x_brief/__init__.py** - Package initialization (v0.1.0)

3. **x_brief/models.py** - Pydantic data models
   - `Post` - Tweet/post with metrics, author info, references
   - `User` - X/Twitter user profile
   - `PostMetrics` - Engagement metrics (likes, reposts, replies, views, quotes)
   - `BriefingItem` - Single item in briefing with post + summary
   - `BriefingSection` - Section with title, emoji, items
   - `Briefing` - Complete briefing document
   - `UserConfig` - User configuration

4. **x_brief/config.py** - Configuration management
   - `XBriefConfig` - System config (API keys, cache paths)
   - Environment variable support (X_BRIEF_BEARER_TOKEN, X_BRIEF_ANTHROPIC_KEY)
   - Load/save user config from JSON

5. **x_brief/fetcher.py** - X API v2 async client
   - `XClient` - Async HTTP client with bearer token auth
   - Rate limit handling (checks headers, raises RateLimitError)
   - `get_user_by_username()` - Fetch user by username
   - `get_users_by_usernames()` - Batch fetch users (max 100)
   - `get_user_tweets()` - Fetch user timeline with pagination
   - `search_tweets()` - Search recent tweets with pagination
   - Proper X API v2 response parsing (data + includes + expansions)

6. **x_brief/cache.py** - SQLite caching layer
   - `Cache` - SQLite database for posts and users
   - TTL-based expiry (posts: 48h, users: 7d)
   - `cache_post()`, `cache_posts()` - Cache operations
   - `get_post()`, `get_user_by_id()`, `get_user_by_username()` - Retrieval
   - `get_or_fetch_user_id()` - Cache-first user lookup helper
   - `cleanup_expired()` - Remove old entries

7. **x_brief/scorer.py** - Content scoring and deduplication
   - `deduplicate()` - Remove exact duplicates, group reposts/quotes
   - `score_post()` - Engagement velocity scoring formula:
     - `(views*0.1 + likes*1 + reposts*3 + replies*2 + quotes*4) / followers`
     - Boosts for high absolute engagement
   - `rank_posts()` - Sort posts by score

8. **x_brief/formatter.py** - Output formatting
   - `format_markdown()` - Telegram-friendly markdown
   - `format_html()` - Email-ready HTML with styling
   - `format_plain()` - Plain text output
   - Jinja2 templates with post links (https://x.com/{username}/status/{id})
   - Includes briefing stats at bottom

9. **x_brief/cli.py** - Click CLI
   - `x-brief init` - Create example config.json
   - `x-brief fetch --config config.json --hours 24` - Fetch and cache posts
   - `x-brief brief --config config.json --hours 24 --format markdown` - Generate briefing
   - `x-brief accounts --config config.json` - List tracked accounts
   - All commands properly async with error handling

10. **configs/example.json** - Example configuration
    - Sample tracked accounts (elonmusk, openai, etc.)
    - Sample interests (AI, technology, etc.)
    - Delivery configuration structure

## Installation

```bash
cd ~/projects/x-brief
pip install -e .
```

## Usage

### 1. Set up environment

```bash
export X_BRIEF_BEARER_TOKEN="your_twitter_bearer_token"
export X_BRIEF_ANTHROPIC_KEY="your_anthropic_key"  # optional
```

### 2. Initialize config

```bash
x-brief init --output config.json
# Edit config.json with your settings
```

### 3. Fetch posts

```bash
x-brief fetch --config config.json --hours 24
```

### 4. Generate briefing

```bash
x-brief brief --config config.json --hours 24 --format markdown
```

## Architecture

```
Fetch (X API) → Cache (SQLite) → Deduplicate → Score → [AI Analyze] → Format → Deliver
```

### Current Status: ✅ Phase 1 Complete

- ✅ X API v2 client with async, rate limiting, pagination
- ✅ SQLite caching layer with TTL
- ✅ Scoring and deduplication
- ✅ Markdown/HTML formatters
- ✅ CLI tool for fetch + brief generation

### Phase 2: Not Yet Implemented

- ⏳ **analyzer.py** - AI content analysis (Claude integration)
- ⏳ **curator.py** - AI-powered content curation and summarization
- ⏳ **delivery.py** - Delivery backends (Telegram, email, webhook)
- ⏳ OpenClaw skill integration
- ⏳ Tests

## Technical Notes

### X API v2 Integration
- Uses bearer token authentication (no OAuth required)
- Handles rate limits via response headers
- Supports pagination with next_token
- Parses expansions (author_id, referenced_tweets)
- Fetches tweet fields: id, text, created_at, public_metrics, entities, referenced_tweets, author_id, conversation_id, lang
- Fetches user fields: id, username, name, description, public_metrics, verified

### Scoring Algorithm
Posts are scored using engagement velocity normalized by author followers:
```
score = (views*0.1 + likes*1 + reposts*3 + replies*2 + quotes*4) / followers
```
With boosts for viral content (>1000 likes = 1.5x, >500 reposts = 1.3x)

### Data Models
All models use Pydantic v2 for validation and serialization. Key models:
- `Post` - Complete tweet data with metrics and metadata
- `User` - Author profile with follower count
- `Briefing` - Structured output with sections and stats

## Next Steps

1. **Implement analyzer.py** - Claude API integration for content analysis
2. **Implement curator.py** - AI-powered briefing generation
3. **Add delivery.py** - Telegram, email, webhook delivery
4. **Package as OpenClaw skill** - Full agent integration
5. **Add tests** - Unit and integration tests

## Dependencies

- **httpx** - Async HTTP client
- **sqlite-utils** - SQLite database helpers
- **pydantic** - Data validation and models
- **click** - CLI framework
- **jinja2** - Template engine

## License

MIT

## Project Details
- **Vision:** SaaS product — no user X credentials needed, uses X API v2 (pay-per-usage)
- **Two modes:** OpenClaw skill (chat delivery) + Standalone (email newsletter)
- **Architecture:** ARCHITECTURE.md — 4 phases from MVP to ML personalization
- **Steve's following list:** ~/projects/second-brain/steve_following.json
- **Must fetch ALL accounts Steve follows** — use X API pagination for complete list
- **UI mimics X's tab layout** — "For You" and "Following" style tabs
- **Crons:** auto-update OpenClaw (4AM CT / 10:00 UTC)
- **Claude Code:** v2.1.38, authenticated
