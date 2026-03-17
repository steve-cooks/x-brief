# X Brief

[![CI](https://github.com/steve-cooks/x-brief/actions/workflows/test.yml/badge.svg)](https://github.com/steve-cooks/x-brief/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Replace 2 hours of compulsive scrolling with a 5-minute brief.

X Brief is an **anti-scrolling-addiction tool** for X/Twitter.
It is **not** a generic news aggregator.

The goal is simple:
- get the most useful posts from your timeline,
- avoid dopamine-driven feed loops,
- close the app and move on with your day.

![X Brief screenshot](docs/images/screenshot-light-foryou.jpg)

---

## Why this exists

Most feeds reward attention capture, not usefulness.
X Brief flips that:
- fewer posts,
- higher information density,
- clear stopping point (`~X min read`).

If nothing important happened, that is a good outcome too.

---

## How it works

```text
scan timeline JSON
   → score (engagement + information density)
   → curate (topic clustering + quality gates)
   → enrich (full text, media, quotes, link cards)
   → serve (web UI + JSON API)
```

Pipeline output:
- `data/latest-briefing.json`
- `data/pipeline-status.json`
- `data/brief_history.json` (dedup window + re-emergence tracking)

---

## The 3-tab briefing system (v2)

### 1) Can't Miss 🔥
**Philosophy:** rare, globally important, high-substance moments only.

Quality gates:
- density score >= 3
- likes >= 10,000 and views >= 500,000
- quality ratio `(bookmarks + replies) / likes >= 5%`
- max 1 post per author

If empty: **"Nothing major happened. Go live your life. ✌️"**

### 2) For You 📌
**Philosophy:** useful posts tailored to your interests, with breadth.

- Interest-matched
- Topic-clustered (one winner per topic)
- Max 1 post per author
- Scored to favor substance

### 3) Following 👥
**Philosophy:** balanced updates from people you intentionally track.

- Source: following feed or tracked account fallback
- Lower engagement floor
- Topic-clustered for variety

---

## Scoring model

### Engagement score (normalized per run)

```text
raw =
  likes*1.0 + reposts*2.0 + replies*1.5 + bookmarks*3.0 + views*0.01
```

Why these weights:
- **Bookmarks x3**: strongest usefulness signal
- Reposts/replies > likes: endorsement + discussion
- Views lightly weighted: cheap and passive

### Information density score (0-20)

Bonuses:
- external link +3
- X article +5
- thread +4
- long form (>200 chars +2, >500 chars additional +2)
- media +1

Penalty:
- short hot take (<100 chars, no link/media) -2

### Final tab weights

- **Can't Miss:** `0.7 engagement + 0.3 density`
- **For You:** `0.4 engagement + 0.6 density`
- **Following:** `0.5 engagement + 0.5 density`

### Re-emergence

A previously briefed post can re-enter **Can't Miss** if engagement jumps 10x.

---

## Quick start

## 1) Backend (Python)

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create config:

```bash
cp configs/example.json configs/my-config.json
```

Run pipeline from scans:

```bash
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 36
# or
x-brief run --config configs/my-config.json --hours 36
```

## 2) Frontend (Next.js)

```bash
cd web
npm install
npm run dev
```

Open: `http://localhost:3000`

---

## Configuration

Main config file fields:

- `x_handle`: optional personal reference
- `tracked_accounts`: accounts that should influence relevance
- `recent_interests`: your topical filters
- `delivery`: reserved for downstream delivery integrations
- `briefing_schedule`: label for your cadence

Example (`configs/example.json`):

```json
{
  "x_handle": "your_handle",
  "tracked_accounts": ["openai", "anthropicai", "vercel"],
  "recent_interests": ["AI & Tech", "Startups & Business", "Design & UI"],
  "delivery": { "type": "local" },
  "briefing_schedule": "daily"
}
```

### Environment variables (optional)

- `X_BRIEF_SCAN_DIR` — where scan JSON files are read from
- `X_BRIEF_DATA_DIR` — where briefing/status/history files are written/read

---

## Scan input format

Each scan file should contain:
- `scan_time` (ISO timestamp)
- one or more arrays with posts (`posts`, `viral_alerts`, `notable_posts`)

Each post should include a valid X status URL (`/status/<id>`) or article URL.

See full setup + examples in [`SETUP.md`](./SETUP.md).

---

## Automation (cron)

Run every 4 hours:

```cron
5 */4 * * * cd /home/you/projects/x-brief && . .venv/bin/activate && python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48 >> /home/you/projects/x-brief/data/pipeline.log 2>&1
```

Typical schedule:
1. browser/agent writes scan JSON into `timeline_scans/`
2. cron runs pipeline
3. web UI auto-refreshes from latest JSON

---

## Project structure

```text
x_brief/        Python ingestion/scoring/curation/pipeline
tests/          Pytest coverage
configs/        Example configuration
timeline_scans/ Input scan snapshots
data/           Generated briefing artifacts
web/            Next.js UI + API routes
```

---

## Tech stack

- **Backend:** Python 3.10+, Click, Pydantic
- **Frontend:** Next.js (App Router), React, TypeScript, Tailwind, shadcn/ui
- **Storage:** local JSON files (no DB required)
- **Enrichment:** X syndication endpoint for full post text, media, quote tweets, link cards, and avatars

---

## Contributing

We welcome contributions that improve:
- curation quality
- anti-addiction UX
- reliability and docs

Please read [`CONTRIBUTING.md`](./CONTRIBUTING.md) first.

Before opening a PR:

```bash
python3 -m pytest tests/ -q
cd web && npm run build
```

---

## License

MIT — see [`LICENSE`](./LICENSE).
