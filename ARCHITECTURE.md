# X Brief Architecture

## Overview

X Brief is a local, scan-only system:

- The Python package in [`x_brief/`](./x_brief) reads browser timeline scan files, curates a briefing, and exports JSON.
- The Next.js app in [`web/`](./web) reads that JSON and renders the briefing UI.

## Runtime Flow

```text
timeline_scans/*.json
  -> x_brief.scan_reader.load_scan_posts()
  -> x_brief.dedup.filter_already_briefed()
  -> x_brief.curator.curate_briefing()
  -> x_brief.pipeline.export_briefing_json()
  -> data/latest-briefing.json (+ data/pipeline-status.json)
  -> web/src/app/api/briefing/route.ts
  -> (optional) web/src/app/api/pipeline-status/route.ts
  -> web/src/components/briefing-view.tsx
```

## Python Modules

- [`x_brief/models.py`](./x_brief/models.py): Pydantic models for posts, users, media, quoted posts, briefing items, and config.
- [`x_brief/config.py`](./x_brief/config.py): user config load/save helpers.
- [`x_brief/scan_reader.py`](./x_brief/scan_reader.py): scan JSON parsing, timestamp handling, metric parsing, and user synthesis.
- [`x_brief/dedup.py`](./x_brief/dedup.py): cross-run brief history loading, filtering, saving, and cleanup.
- [`x_brief/scorer.py`](./x_brief/scorer.py): post deduplication, scoring, and viral thresholds.
- [`x_brief/curator.py`](./x_brief/curator.py): section assembly for VIRAL 🔥, TOP PICKS 📌, and FOLLOWING 👥.
- [`x_brief/enrichment.py`](./x_brief/enrichment.py): optional syndication enrichment after JSON export.
- [`x_brief/pipeline.py`](./x_brief/pipeline.py): scan-only orchestration, markdown rendering, and JSON export.
- [`x_brief/cli.py`](./x_brief/cli.py): scan-only Click entrypoints.

## Frontend Modules

- [`web/src/app/api/briefing/route.ts`](./web/src/app/api/briefing/route.ts): reads `latest-briefing.json` from `X_BRIEF_DATA_DIR` or repo-local fallbacks.
- `web/src/app/api/pipeline-status/route.ts` (recommended): read `pipeline-status.json` so the UI can surface pipeline health without touching the filesystem directly.
- [`web/src/app/api/media/route.ts`](./web/src/app/api/media/route.ts): media proxy for approved X media hosts.
- [`web/src/app/page.tsx`](./web/src/app/page.tsx): app entrypoint.
- [`web/src/components/briefing-view.tsx`](./web/src/components/briefing-view.tsx): tabbed briefing shell, polling, read state, media viewer integration.
- [`web/src/components/x-brief/post-card.tsx`](./web/src/components/x-brief/post-card.tsx): individual post rendering.

## Commands

- `x-brief init --output config.json`
- `x-brief brief --config configs/example.json --hours 36`
- `x-brief run --config configs/example.json --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36 --scan-dir ./timeline_scans`
- `python -m x_brief.pipeline configs/example.json --from-scans --skip-dedup`
- `cd web && npm install`
- `cd web && npm run dev`

## Output Contract

The shared artifacts are:

- `latest-briefing.json` with `generated_at`, `period_hours`, `sections[]`, and `stats`
- `pipeline-status.json` with:
  - success: `{ "status": "ok", "last_success": "ISO timestamp", "posts_processed": N, "sections": N }`
  - failure: `{ "status": "error", "error": "description", "last_success": "ISO timestamp|null", "last_attempt": "ISO timestamp" }`

Each section contains `title`, `emoji`, and `posts[]`. Each post includes author fields, metrics, media, quoted-post data when present, `postUrl`, timestamps, and optional enrichment data.

## Boundaries

- Scan ingestion depends on browser-agent JSON quality. Missing `/status/<numeric_id>` URLs cause posts to be dropped.
- Brief-history dedup only applies when `--skip-dedup` is not used.
- Syndication enrichment is bounded and intentionally slow; it does not enrich every possible post in large runs.
- The frontend has no database and no backend persistence layer. It only reads generated JSON and stores per-browser read state locally.
- The media proxy is intentionally restricted to approved X media hosts.

## Verification

- `python -m pytest tests/ -q`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `cd web && npm run lint`
