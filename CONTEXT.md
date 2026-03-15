# X Brief Context

> **Maintenance rule for any agent working here:** If your work changes product behavior, architecture, commands, env/config expectations, workflows, data flow, operational behavior, or other durable project facts, update this file before finishing. Keep it lean: preserve durable truths and delete stale material; do not dump transient task notes, logs, or implementation trivia here.

## Product intent

X Brief helps users avoid doomscrolling by turning noisy X timelines into a short, high-signal briefing.

Core principle: **substance over dopamine**.

## Current model (v2)

- Three tabs:
  - Can't Miss 🔥
  - For You 📌
  - Following 👥
- Scoring combines engagement + information density
- Topic clustering enforces breadth
- Dedup history prevents repeats
- Re-emergence allows true breakouts to return
- UI shows read-time estimate (`~X min read`)

## Key commands

```bash
x-brief init --output config.json
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

- `X_BRIEF_SCAN_DIR` (optional)
- `X_BRIEF_DATA_DIR` (optional)

## Important implementation notes

- `recent_interests` is the active config field.
- Scan files can include `posts`, `viral_alerts`, and `notable_posts` arrays.
- Posts without valid status/article IDs are ignored.
- `--skip-dedup` bypasses brief-history filtering.
- Can't Miss empty state is intentional and desirable.
