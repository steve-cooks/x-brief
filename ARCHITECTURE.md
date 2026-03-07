# 𝕏 Brief — Architecture & Plan

## Vision
A tool that curates your 𝕏 experience without requiring your login. Like having a smart friend who reads 𝕏 for you and sends you what matters.

## The Problem
- Scrolling 𝕏 is time-consuming and addictive
- You miss important posts from people you follow
- You miss big trends in your niches even if you don't follow those specific accounts
- No good way to get a "what happened while I was away" summary

## The Solution
𝕏 Brief fetches, analyzes, and curates content from:
1. **Your following list** — what your people are posting/engaging with
2. **Your interest niches** — broader trends in topics you care about (tech, crypto, etc.)
3. **Breakout content** — viral/important posts you'd want to see regardless

Delivered as a structured briefing via OpenClaw, email, or webhook.

## How It Works (No User Credentials Needed)

### Data Collection (X API v2)
- **User timelines** — `GET /2/users/:id/tweets` for each followed account
- **Full-archive search** — `GET /2/tweets/search/all` for niche/topic queries
- **Filtered stream** — real-time streaming with up to 1,000 rules (future)
- Users provide: their X handle OR a list of handles they want to track
- Interests are AUTO-INFERRED from their followings (no manual input needed)
- Optional: "Recent Interests" — topics they care about but don't follow anyone in yet
- We resolve handles → user IDs via `GET /2/users/by/username/:username`
- All public data, no OAuth from the end user

### Content Pipeline
```
Fetch (X API) → Deduplicate → Score → Analyze (AI) → Curate → Format → Deliver
```

1. **Fetch**: Pull last 24-48h of posts from tracked accounts + niche searches
2. **Deduplicate**: Remove reposts, quote-tweets of same content
3. **Score**: Engagement velocity, follower ratio, reply quality
4. **Analyze**: AI categorizes content, detects themes, identifies breakout stories
5. **Curate**: Select top content per category, write summaries
6. **Format**: Structure into readable briefing sections
7. **Deliver**: Send via configured channel

### Briefing Structure
```
🌅 𝕏 Brief — Monday, Feb 10, 2026

📌 TOP STORIES
[3-5 biggest things that happened]

👥 YOUR CIRCLE
[What the people you follow are talking about]

🔥 TRENDING IN YOUR NICHES
[Broader trends in tech/crypto/etc.]

💡 WORTH A LOOK
[Interesting posts that don't fit above]

📊 STATS
- X posts scanned: 1,247
- Accounts tracked: 50
- Topics monitored: 5
```

## Two Modes

### 1. OpenClaw Mode (Skill/Plugin)
- Install as OpenClaw skill
- Runs as cron job or on-demand
- Delivers briefing directly in chat (Telegram, Discord, etc.)
- Can be queried conversationally: "what's happening in tech?" "what did your account post today?"
- Deep integration with agent memory/second brain

### 2. Standalone Mode (Email/Webhook)
- User provides: email + X handle + interests
- Daily email newsletter format
- No OpenClaw required
- Simple web dashboard for configuration
- Webhook option for custom integrations

## Tech Stack

### Core (Python)
- `x-brief/` — main package
  - `config.py` — user configuration management
  - `fetcher.py` — X API v2 client (async, rate-limit aware)
  - `scorer.py` — engagement scoring & dedup
  - `analyzer.py` — AI content analysis (Claude API)
  - `curator.py` — content selection & briefing generation
  - `formatter.py` — output formatting (markdown, HTML, plain)
  - `delivery.py` — delivery backends (OpenClaw, email, webhook)
  - `models.py` — data models (Post, User, Briefing, etc.)
  - `cache.py` — local cache to avoid re-fetching

### OpenClaw Integration
- `skill/` — OpenClaw skill package
  - `SKILL.md` — skill definition
  - `scripts/` — briefing generation scripts
  
### Standalone
- `server/` — lightweight API (FastAPI)
  - Email delivery via SMTP
  - Simple web config page

### Storage
- SQLite for post cache + user configs (portable, no server needed)
- Optional: ChromaDB for semantic search over historical posts

## X API Usage & Cost Estimate
- Pay-per-usage model (no monthly subscription)
- User timeline: ~50 accounts × 1 request each = 50 requests/day
- Search queries: ~5-10 niche searches/day
- User lookups: minimal (cached after first resolve)
- Estimated cost: very low for personal use, scales with users for SaaS

## Project Phases

### Phase 1: Core Engine (MVP) ← NOW
- [ ] X API client with auth + rate limiting
- [ ] User timeline fetching (batch)
- [ ] Basic scoring (engagement metrics)
- [ ] AI analysis & curation (Claude via sub-agent)
- [ ] Markdown briefing formatter
- [ ] CLI tool: `x-brief generate --config config.json`
- [ ] Test with a sample set of 50 tracked accounts

### Phase 2: OpenClaw Integration
- [ ] Package as OpenClaw skill
- [ ] Cron job for daily briefing
- [ ] Conversational queries ("what's your account up to?")
- [ ] Second brain integration (ingest interesting posts)

### Phase 3: Standalone & SaaS
- [ ] Email delivery backend
- [ ] Web configuration dashboard
- [ ] Multi-user support
- [ ] Webhook delivery
- [ ] Billing integration

### Phase 4: Advanced
- [ ] Filtered stream (real-time alerts for breaking news)
- [ ] Personalization ML (learn what user engages with)
- [ ] Thread reconstruction & summarization
- [ ] Cross-platform (Bluesky, Mastodon, LinkedIn)

## What We Need from You
1. **X API key** — Create app at https://console.x.com, get Bearer Token
   - App permissions: Read (that's all we need)
   - We need: API Key, API Secret, Bearer Token
2. **Anthropic API key** — for AI analysis layer (or use OpenClaw's built-in)

## File Structure
```
~/projects/x-brief/
├── ARCHITECTURE.md          ← this file
├── README.md                ← public-facing docs
├── pyproject.toml           ← Python package config
├── x_brief/
│   ├── __init__.py
│   ├── config.py
│   ├── fetcher.py
│   ├── scorer.py
│   ├── analyzer.py
│   ├── curator.py
│   ├── formatter.py
│   ├── delivery.py
│   ├── models.py
│   └── cache.py
├── skill/                   ← OpenClaw skill
│   ├── SKILL.md
│   └── scripts/
├── server/                  ← Standalone API (Phase 3)
├── tests/
└── configs/
    └── example.json
```
