# X Brief Setup

This is the full end-to-end setup for the scan-only version of X Brief.

## What You Need

- Python 3.10+
- Node.js 18+
- A local clone of this repository
- A browser automation workflow or exported timeline scan files

## Repository Layout

```text
x-brief/
├── configs/
├── data/
├── timeline_scans/
├── web/
└── x_brief/
```

## 1. Clone And Install

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Create A Config File

```bash
cp configs/example.json configs/my-config.json
```

Example:

```json
{
  "x_handle": "your_x_handle",
  "tracked_accounts": ["openai", "AnthropicAI", "vercel"],
  "recent_interests": ["AI", "Machine Learning", "Startups", "Design"],
  "delivery": { "type": "telegram" },
  "briefing_schedule": "daily"
}
```

Field notes:

- `x_handle`: optional reference to your own handle.
- `tracked_accounts`: optional context for who matters to you.
- `recent_interests`: topics used during curation.
- `delivery`: reserved for downstream delivery integrations.
- `briefing_schedule`: free-form schedule label.

## 3. Optional Environment Variables

No `.env` file is required. The scan-only pipeline supports:

- `X_BRIEF_SCAN_DIR`: input folder for timeline scan JSON. Default: `./timeline_scans/`
- `X_BRIEF_DATA_DIR`: output folder for `latest-briefing.json` and `brief_history.json`

Example:

```bash
X_BRIEF_SCAN_DIR=./timeline_scans
X_BRIEF_DATA_DIR=./data
```

## 4. Browser Scan File Format

X Brief expects scan JSON files in `timeline_scans/` or your configured scan directory.

Minimum supported shape:

```json
{
  "scan_time": "2026-03-07T08:00:00Z",
  "posts": [
    {
      "url": "https://x.com/openai/status/1891111111111111111",
      "author": "@openai",
      "author_name": "OpenAI",
      "text": "Example scan post for local setup validation.",
      "posted_at": "57m ago",
      "verified": true,
      "metrics": {
        "likes": "1200",
        "reposts": "80",
        "replies": "40",
        "views": "100K"
      }
    }
  ]
}
```

Notes:

- `scan_time` should be ISO 8601.
- Each post must include a valid X status URL with `/status/<numeric_id>`.
- `posted_at` can be relative text like `57m ago`, `3h ago`, or `Mar 7`.
- Metric values can be raw numbers or abbreviated strings like `12K`.
- Optional arrays `viral_alerts` and `notable_posts` are also read when present.

## 5. Run The Pipeline

Module entrypoint:

```bash
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48
```

Installed CLI:

```bash
x-brief brief --config configs/my-config.json --hours 48
x-brief run --config configs/my-config.json --hours 48
```

Useful flags:

- `--scan-dir /absolute/path/to/timeline_scans`
- `--skip-dedup`
- `--output /path/to/brief.md` for the Click commands

What happens:

1. Scan files from the requested time window are loaded.
2. Previously briefed posts are filtered unless `--skip-dedup` is set.
3. The curator builds ranked sections.
4. Markdown is printed to stdout.
5. `latest-briefing.json` is written for the frontend.
6. `brief_history.json` is updated when dedup is active.

## 6. Run The Web Frontend

Development:

```bash
cd web
npm install
npm run dev
```

Production:

```bash
cd web
npm install
npm run build
npm start
```

The frontend reads:

1. `${X_BRIEF_DATA_DIR}/latest-briefing.json` when `X_BRIEF_DATA_DIR` is set.
2. Otherwise `../data/latest-briefing.json`.

## 7. Automate Scan + Pipeline

Example browser-agent instruction:

```text
Go to https://x.com/home and collect timeline posts.
Write JSON with top-level keys scan_time and posts.
Save the file to ${X_BRIEF_SCAN_DIR}/$(date -u +%Y-%m-%d-%H).json.
Then run:
cd /home/you/projects/x-brief
source .venv/bin/activate
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48
```

Example cron fallback:

```cron
5 */4 * * * cd /home/you/projects/x-brief && . .venv/bin/activate && python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48 >> /home/you/projects/x-brief/data/pipeline.log 2>&1
```

## 8. Run The Frontend As A Service

Example user-level systemd service:

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

## Troubleshooting

### No `latest-briefing.json`

- Run `python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48`
- Confirm the scan directory exists and has recent JSON files
- Confirm scan files include `scan_time` and valid `/status/<id>` URLs

### Empty results or `All posts already briefed.`

- Run with `--skip-dedup`, or
- Remove/rotate `brief_history.json` if you intentionally want a full refresh

### Web frontend shows `No briefing available`

- Set `X_BRIEF_DATA_DIR` for the web process when data lives outside the repo default
- Confirm `latest-briefing.json` exists in the expected directory

### Port conflicts on `3000`

- Stop the other process, or
- Start Next.js on another port: `npm start -- -p 3001`
