# X Brief Context

> **Maintenance rule for any agent working here:** If your work changes product behavior, architecture, commands, env/config expectations, workflows, data flow, or other durable project facts, update this file before finishing. Keep it lean: preserve durable truths and delete stale material.

## Product intent

X Brief helps users avoid doomscrolling by turning noisy X timelines into a short, high-signal briefing.

Core principle: **substance over dopamine**.

## Current model (v3 - simplified)

- Three tabs in web UI:
  - TL;DR ⚡ (AI-generated casual summary of unseen posts)
  - For You 📌 (posts from "For You" tab, unseen only)
  - Following 👥 (posts from "Following" tab, unseen only)
- Posts are scraped read-only - no interaction with X
- Posts marked as `seen` disappear from the UI
- Daily reset at midnight clears all posts for a fresh start
- TL;DR summarizes only unseen posts

## Pipeline flow

1. OpenClaw cron (Rabbit) scrapes X timeline - For You + Following tabs (10 posts each)
2. Scan data saved to `timeline_scans/YYYY-MM-DD-HH-{tab}.json`
3. `python3 -m x_brief.posts_store --ingest <scan_file> --tab <tab>` appends new posts (deduped) to `data/posts.json`
4. `python3 -m x_brief.tldr` reads unseen posts -> calls LLM -> writes `data/latest-briefing.json`
5. Web UI reads `data/posts.json` (via /api/posts) and `data/latest-briefing.json` (via /api/briefing)
6. When user views a post, UI calls POST /api/posts with `{ ids: [...] }` to mark as seen

## Key commands

```bash
# Ingest a scan file
python3 -m x_brief.posts_store --ingest timeline_scans/2026-03-27-04-foryou.json --tab foryou

# Regenerate TL;DR
python3 -m x_brief.tldr

# Midnight reset
python3 -m x_brief.posts_store --clear

# Run tests
python3 -m pytest tests/ -q

# Build web UI
cd web && npm run build
```

## Paths and artifacts

Inputs:
- `timeline_scans/*.json` (raw scan files from Rabbit)

Outputs:
- `data/posts.json` - all scraped posts with seen/unseen state
- `data/latest-briefing.json` - TL;DR + metadata

## Environment variables

- `X_BRIEF_DATA_DIR` (optional) - data directory (default: `data/`)
- `ANTHROPIC_API_KEY` - required for TL;DR generation
- `XBRIEF_CRON_JOB_ID` - OpenClaw cron job ID (used by web UI)
- `OPENCLAW_GATEWAY_TOKEN` - gateway auth token (used by scan wrapper script)

## Important notes

- Rabbit writes scan files; Python pipeline ingests them - these are separate steps
- See `CRON_INSTRUCTIONS.md` for the exact cron messages to use
- The old scoring/curation pipeline (`x_brief/pipeline.py`) still exists as fallback but is not the primary path
- `data/read-state.json` is legacy - new seen-state lives in `data/posts.json`
