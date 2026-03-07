# X Brief Setup Guide

This guide is the full end-to-end setup for running X Brief from scratch in either browser scan mode (recommended) or X API mode.

## Prerequisites

- Python `3.10+`
- Node.js `18+`
- One of:
  - OpenClaw (for browser scan mode)
  - X API Bearer Token (for API mode)

## Installation

1. Clone the repo.

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief
```

2. Create and activate a Python virtual environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install the package in editable mode.

```bash
pip install -e .
```

4. Create your config file from the example.

```bash
cp configs/example.json configs/my-config.json
```

## Configuration

### `configs/my-config.json`

Model source of truth is `UserConfig` in `x_brief/models.py`.

```json
{
  "x_handle": "your_x_handle",
  "tracked_accounts": ["openai", "AnthropicAI", "vercel"],
  "recent_interests": ["AI", "Machine Learning", "Startups"],
  "delivery": { "type": "telegram" },
  "briefing_schedule": "daily"
}
```

Fields:

- `x_handle` (`string | null`): Your own X username without `@`.
- `tracked_accounts` (`string[]`): Usernames to fetch in API mode.
- `recent_interests` (`string[]`): Topics used by curation logic and search query generation.
- `delivery` (`object`): Reserved metadata for delivery integrations.
- `briefing_schedule` (`string`, default `"daily"`): Informational scheduling preference.

Notes:

- Use `recent_interests` (not `interests`) in current code.
- In scan mode, `tracked_accounts` is not used for collection, but keeping it populated is still useful context.

For browser scan mode, no `.env` file is required. All env vars are optional overrides.

Core optional overrides:

- `X_BRIEF_SCAN_DIR` (scan-mode input folder; default `./timeline_scans/`):
  - Example: `X_BRIEF_SCAN_DIR=/home/you/projects/x-brief/timeline_scans`
- `X_BRIEF_DATA_DIR` (mainly for web API route override):
  - Example: `X_BRIEF_DATA_DIR=/home/you/projects/x-brief/data`

Optional vars used by helper script `scripts/fetch_following.py`:

- `X_BRIEF_USERNAME`
- `X_BRIEF_CONFIG_PATH`
- `X_BRIEF_FOLLOWING_OUTPUT`

Optional web env var in `web/.env.example`:

- `X_BRIEF_DATA_DIR`

## Mode 1: Browser Scan Mode (Recommended — No API Key)

This is the main mode.

No API keys needed. No `.env` file needed.

### How the scan works

An OpenClaw browser agent (for example Rabbit) opens `https://x.com/home`, scrolls the timeline, extracts posts, and writes a JSON file into your scan directory (`X_BRIEF_SCAN_DIR` or `./timeline_scans/`).  
Then Python reads those files via `x_brief/scan_reader.py`, deduplicates posts by status ID, curates sections, and writes `data/latest-briefing.json`.

### Scan JSON format

`x_brief/scan_reader.py` expects:

- Top-level `scan_time` or `timestamp` (ISO datetime string) for file freshness filtering.
- One or more post arrays under keys:
  - `posts`
  - `viral_alerts`
  - `notable_posts`
- Each post **must** include a `url` containing `/status/<numeric_id>`.

Accepted per-post fields:

- `url` (`string`, required): e.g. `https://x.com/sama/status/1891111111111111111`
- `text` (`string`, recommended)
- `author` (`string`, recommended) and/or `author_handle` (`string`)
- `author_name` (`string`, optional)
- `posted_at` or `time` (`string`, optional): supports `57m ago`, `2h`, `3d ago`, `just now`, `Feb 23`, ISO timestamps.
- `verified` (`boolean`, optional)
- `metrics` or `engagement` (`object`, optional) with:
  - `likes`, `reposts`/`retweets`, `replies`, `views`, `bookmarks` (numbers or strings like `1.2K`)
- Top-level metric fallbacks also work (`likes`, `reposts`, `retweets`, `replies`, `views`, `bookmarks`)
- `media` (`string | object | object[]`, optional)
- Quoted tweet object under one of:
  - `quoted_tweet`, `quote_tweet`, `quoted`, `quotedPost`

Complete working example (`timeline_scans/2026-03-07-08.json`):

```json
{
  "scan_time": "2026-03-07T08:00:00Z",
  "posts": [
    {
      "url": "https://x.com/sama/status/1891111111111111111",
      "author": "@sama",
      "author_name": "Sam Altman",
      "text": "New model updates rolling out this week.",
      "posted_at": "57m ago",
      "verified": true,
      "metrics": {
        "likes": "12.4K",
        "reposts": "1,240",
        "replies": 311,
        "views": "1.2M",
        "bookmarks": 980
      },
      "media": "photo"
    },
    {
      "url": "https://x.com/karpathy/status/1891222222222222222",
      "author_handle": "@karpathy",
      "author_name": "Andrej Karpathy",
      "text": "Training recipe thread. https://t.co/abc",
      "time": "2h",
      "engagement": {
        "likes": "8.7K",
        "retweets": "990",
        "replies": "140",
        "views": "430K"
      },
      "media": [
        {
          "type": "photo",
          "url": "https://pbs.twimg.com/media/Gabc123.jpg"
        }
      ]
    }
  ],
  "viral_alerts": [
    {
      "url": "https://x.com/elonmusk/status/1891333333333333333",
      "author": "@elonmusk",
      "author_name": "Elon Musk",
      "text": "Interesting engineering milestone.",
      "posted_at": "just now",
      "likes": "61K",
      "retweets": "9.1K",
      "replies": "4.2K",
      "views": "8.3M",
      "verified": true,
      "quoted_tweet": {
        "url": "https://x.com/openai/status/1891000000000000000",
        "author": "@openai",
        "author_name": "OpenAI",
        "text": "Research preview available now.",
        "metrics": {
          "likes": "22K",
          "reposts": "3.2K",
          "replies": "740",
          "views": "2.5M"
        }
      }
    },
    {
      "url": "https://x.com/vercel/status/1891444444444444444",
      "author": "@vercel",
      "author_name": "Vercel",
      "text": "We shipped a major performance improvement.",
      "posted_at": "Mar 6",
      "metrics": {
        "likes": 3200,
        "reposts": 410,
        "replies": 55,
        "views": 120000
      },
      "media": {
        "type": "video",
        "preview_image_url": "https://pbs.twimg.com/media/Gdef456.jpg",
        "video_url": "https://video.twimg.com/ext_tw_video/123/pu/vid/1280x720/demo.mp4"
      }
    }
  ],
  "notable_posts": [
    {
      "url": "https://x.com/anthropicai/status/1891555555555555555",
      "author": "@AnthropicAI",
      "author_name": "Anthropic",
      "text": "Model card and safety notes published.",
      "posted_at": "2026-03-06T22:14:00Z",
      "metrics": {
        "likes": "4.1K",
        "reposts": "380",
        "replies": "89",
        "views": "280K"
      },
      "verified": true
    },
    {
      "url": "https://x.com/levelsio/status/1891666666666666666",
      "author": "@levelsio",
      "author_name": "Pieter Levels",
      "text": "Shipping fast still wins.",
      "posted_at": "1d ago",
      "metrics": {
        "likes": "2.9K",
        "reposts": "150",
        "replies": "70",
        "views": "95K"
      }
    }
  ]
}
```

### Setting up the OpenClaw cron

Recommended schedule: every 4 hours.

Cron expression:

```cron
0 */4 * * *
```

Exact agent instruction message (copy/paste):

```text
Go to https://x.com/home and make sure the home timeline is fully loaded.
Collect 80-150 visible timeline posts while scrolling.
For each post, capture: url (must include /status/<id>), text, author (as @username), author_name, posted_at, verified, metrics {likes,reposts,replies,views,bookmarks}, media, and quoted_tweet when present.
Write JSON with top-level keys: scan_time (ISO string) and posts (array). Optionally include viral_alerts and notable_posts arrays.
Save file to: ${X_BRIEF_SCAN_DIR}/$(date -u +%Y-%m-%d-%H).json
Then run:
cd /home/you/projects/x-brief
source .venv/bin/activate
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48
```

Example OpenClaw cron config:

```json
{
  "name": "x-brief-scan-and-pipeline",
  "schedule": "0 */4 * * *",
  "timezone": "UTC",
  "agent": "rabbit",
  "message": "Go to https://x.com/home and collect timeline posts; save JSON to ${X_BRIEF_SCAN_DIR}/$(date -u +%Y-%m-%d-%H).json with keys scan_time + posts; then run cd /home/you/projects/x-brief && source .venv/bin/activate && python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48"
}
```

### Running the pipeline manually

```bash
cd x-brief
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48
```

Useful flags:

- `--scan-dir /absolute/path/to/timeline_scans`
- `--skip-dedup` (ignore `data/brief_history.json` and include already-briefed posts)

## Mode 2: X API Mode

This mode requires an X developer account and bearer token.

1. Create an X developer app and generate a bearer token from the developer portal.
2. Create `.env` from `.env.example` and set your bearer token.

```bash
cp .env.example .env
```

`.env` for API mode:

- `X_BRIEF_BEARER_TOKEN` (required):
  - Example: `X_BRIEF_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAA...`
- `X_BRIEF_SCAN_DIR` (optional override)
- `X_BRIEF_DATA_DIR` (optional override)

3. Load env vars into your shell (this project does not auto-load `.env`).

```bash
set -a
source .env
set +a
```

4. Ensure `configs/my-config.json` has `tracked_accounts` populated.
5. Run full pipeline:

```bash
x-brief run --config configs/my-config.json --hours 24
```

Alternative two-step flow:

```bash
x-brief fetch --config configs/my-config.json --hours 24
x-brief brief --config configs/my-config.json --hours 24 --format markdown
```

## Running the Web Frontend

```bash
cd web
npm install
npm run build
npm start
```

Open `http://localhost:3000`.

How data is read:

- API route: `web/src/app/api/briefing/route.ts`
- It first checks `X_BRIEF_DATA_DIR/latest-briefing.json`
- Then falls back to `../data/latest-briefing.json`

Generate data first:

```bash
cd /home/you/projects/x-brief
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48
```

## Running as a Service (optional)

Example user-level systemd service for the web frontend:

`~/.config/systemd/user/x-brief-web.service`

```ini
[Unit]
Description=X Brief Web Frontend
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/you/projects/x-brief/web
Environment=NODE_ENV=production
Environment=X_BRIEF_DATA_DIR=/home/you/projects/x-brief/data
ExecStart=/usr/bin/npm start
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable --now x-brief-web.service
systemctl --user status x-brief-web.service
```

## Automating Everything (cron + pipeline + serve)

End-to-end target state:

1. OpenClaw cron runs every 4 hours.
2. It scans `x.com/home`.
3. It writes scan JSON to `X_BRIEF_SCAN_DIR` (for example `/home/you/projects/x-brief/timeline_scans`).
4. It runs `python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48`.
5. Pipeline writes `/home/you/projects/x-brief/data/latest-briefing.json`.
6. Next.js service (`npm start`) serves updated briefing at `http://localhost:3000`.

Minimal local cron fallback (if OpenClaw only writes files and does not run commands):

```cron
5 */4 * * * cd /home/you/projects/x-brief && . .venv/bin/activate && python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48 >> /home/you/projects/x-brief/data/pipeline.log 2>&1
```

## Troubleshooting

### No `data/latest-briefing.json`

- Cause: pipeline did not run or failed early.
- Check:
  - `python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48`
  - Scan directory exists and has recent JSON files.
  - JSON has `scan_time` or `timestamp`.

### Wrong scan format / parser skips posts

- Cause: post objects missing `url` or URL has no `/status/<id>`.
- Fix: ensure every post has valid status URL and top-level `scan_time`.
- Also ensure arrays are in `posts`, `viral_alerts`, or `notable_posts`.

### Empty results or “All posts already briefed”

- Cause: dedup history filtered everything.
- Fix:
  - Run with `--skip-dedup`, or
  - Remove/rotate `data/brief_history.json` if you intentionally want a full refresh.

### API mode fails with missing token

- Cause: `X_BRIEF_BEARER_TOKEN` not exported in current shell/service.
- Fix: `export X_BRIEF_BEARER_TOKEN=...` and restart the command/service.

### Web frontend shows “No briefing available”

- Cause: route cannot find `latest-briefing.json`.
- Fix:
  - Set `X_BRIEF_DATA_DIR` for web process.
  - Confirm file exists at `${X_BRIEF_DATA_DIR}/latest-briefing.json` or repo `data/latest-briefing.json`.

### Port conflicts on `3000`

- Cause: another service is already using port 3000.
- Fix:
  - Stop the other process, or
  - Start Next.js on another port: `npm start -- -p 3001`
