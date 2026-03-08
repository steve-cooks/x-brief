# X Brief Setup Guide

This guide covers local setup for the scan-only workflow.

## Prerequisites

- Python 3.10+
- Node.js 18+
- Timeline scan JSON files (from your browser automation/scraper)

## 1) Clone + install backend

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2) Configure

```bash
cp configs/example.json configs/my-config.json
```

Edit `configs/my-config.json` with:
- `tracked_accounts`
- `recent_interests`

## 3) Prepare scans

Default scan input directory: `./timeline_scans/`

Minimum file shape:

```json
{
  "scan_time": "2026-03-07T08:00:00Z",
  "posts": [
    {
      "url": "https://x.com/openai/status/1891111111111111111",
      "author": "@openai",
      "author_name": "OpenAI",
      "text": "Example post",
      "posted_at": "57m ago",
      "verified": true,
      "metrics": { "likes": "1200", "reposts": "80", "replies": "40", "views": "100K" }
    }
  ]
}
```

Also supported: `viral_alerts` and `notable_posts` arrays.

## 4) Run pipeline

```bash
python -m x_brief.pipeline configs/my-config.json --from-scans --hours 36
# or
x-brief run --config configs/my-config.json --hours 36
```

## 5) Run frontend

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Optional env overrides

- `X_BRIEF_SCAN_DIR` — input directory for scans
- `X_BRIEF_DATA_DIR` — output directory for briefing/status/history files

Example:

```bash
export X_BRIEF_SCAN_DIR=/home/you/timeline_scans
export X_BRIEF_DATA_DIR=/home/you/x-brief-data
```

## Automation with cron

```cron
5 */4 * * * cd /home/you/projects/x-brief && . .venv/bin/activate && python -m x_brief.pipeline configs/my-config.json --from-scans --hours 48 >> /home/you/projects/x-brief/data/pipeline.log 2>&1
```

## Troubleshooting

- **No briefing file generated**: verify scan directory exists and contains recent valid JSON
- **All posts filtered**: run with `--skip-dedup` or clear `data/brief_history.json`
- **Frontend says no briefing**: check `X_BRIEF_DATA_DIR` alignment between pipeline and web process
