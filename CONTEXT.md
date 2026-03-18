# X Brief Context

> **Maintenance rule for any agent working here:** If your work changes product behavior, architecture, commands, env/config expectations, workflows, data flow, operational behavior, or other durable project facts, update this file before finishing. Keep it lean: preserve durable truths and delete stale material; do not dump transient task notes, logs, or implementation trivia here.

## Product intent

X Brief helps users avoid doomscrolling by turning noisy X timelines into a short, high-signal briefing.

Core principle: **substance over dopamine**.

## Current model (v2)

- Three tabs:
  - TL;DR ⚡ (formerly Can't Miss — rare, high-substance moments; shows AI-generated summary paragraph instead of individual posts)
  - For You 📌 (interest-matched, topic-clustered)
  - Following 👥 (tracked account updates)
- Scoring combines engagement + information density
- Topic clustering enforces breadth
- Dedup history prevents repeats
- Re-emergence allows true breakouts to return
- UI shows read-time estimate
- Scan trigger button in UI (15-minute cooldown between scans)

## Pipeline flow

1. Agent (e.g. Rabbit via OpenClaw) scans X timeline in a real browser — scrolls For You + Following tabs
2. Scan data saved to `timeline_scans/*.json`
3. Pipeline reads scans → scores → curates → enriches → generates TL;DR summary
4. Output written to `data/latest-briefing.json`
5. Web UI reads JSON and renders briefing

## Key commands

```bash
x-brief run --config configs/example.json --hours 36
python -m x_brief.pipeline configs/example.json --from-scans --hours 36
python3 -m pytest tests/ -q
cd web && npm run build
```

## Paths and artifacts

Inputs:
- `timeline_scans/*.json` (or `X_BRIEF_SCAN_DIR`)

Outputs:
- `data/latest-briefing.json`
- `data/pipeline-status.json`
- `data/brief_history.json`

## Environment variables

- `X_BRIEF_SCAN_DIR` (optional) — input scan directory
- `X_BRIEF_DATA_DIR` (optional) — output data directory
- `XBRIEF_SCAN_COMMAND` — command to trigger a scan (used by web UI scan button)
- `XBRIEF_CRON_JOB_ID` — OpenClaw cron job ID (used by web UI)
- `OPENCLAW_GATEWAY_TOKEN` — gateway auth token (used by scan wrapper script)

## Important implementation notes

- `recent_interests` is the active config field — this drives the For You tab. Without it, For You will be empty.
- Scan files can include `posts`, `viral_alerts`, and `notable_posts` arrays.
- Posts without valid status/article IDs are ignored.
- `--skip-dedup` bypasses brief-history filtering.
- TL;DR empty state is intentional and desirable ("Nothing major happened").
- Scan trigger button has 15-minute cooldown (configurable via COOLDOWN_MINUTES in scan route).
