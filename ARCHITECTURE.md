# X Brief Architecture

## Overview

X Brief is a local, two-part system:

- A Python pipeline in [`x_brief/`](/home/cluvis/projects/x-brief/x_brief) that ingests X data, deduplicates and scores posts, curates sections, and exports JSON.
- A Next.js frontend in [`web/`](/home/cluvis/projects/x-brief/web) that reads that JSON and renders the briefing UI.

The current primary workflow is scan mode: browser automation writes timeline scan JSON, the Python pipeline converts it into `data/latest-briefing.json`, and the web app serves that file through `/api/briefing`.

## Runtime Modes

### Scan Mode

Scan mode is the main path for the current codebase.

1. A browser agent writes timeline scan files into `./timeline_scans/` or `X_BRIEF_SCAN_DIR`.
2. [`x_brief.scan_reader`](/home/cluvis/projects/x-brief/x_brief/scan_reader.py) parses those files into typed `Post` objects.
3. [`x_brief.dedup`](/home/cluvis/projects/x-brief/x_brief/dedup.py) optionally filters posts already used in previous briefs.
4. [`x_brief.curator`](/home/cluvis/projects/x-brief/x_brief/curator.py) builds briefing sections from the parsed posts.
5. [`x_brief.pipeline`](/home/cluvis/projects/x-brief/x_brief/pipeline.py) exports `data/latest-briefing.json`.
6. [`x_brief.enrichment`](/home/cluvis/projects/x-brief/x_brief/enrichment.py) optionally augments posts with syndication media, quotes, and link cards.
7. The Next.js app reads that JSON and renders the briefing.

### API Mode

API mode is still supported, but it is secondary and requires `X_BRIEF_BEARER_TOKEN`.

1. [`x_brief.fetcher`](/home/cluvis/projects/x-brief/x_brief/fetcher.py) calls X API v2.
2. [`x_brief.analyzer`](/home/cluvis/projects/x-brief/x_brief/analyzer.py) infers interests from followed accounts and builds search queries.
3. [`x_brief.curator`](/home/cluvis/projects/x-brief/x_brief/curator.py) selects sections from tracked-account posts plus search results.
4. [`x_brief.pipeline`](/home/cluvis/projects/x-brief/x_brief/pipeline.py) formats markdown and exports the same web JSON contract.

## Data Flow

### Scan Mode Flow

```text
Browser timeline scan JSON
  -> x_brief.scan_reader.load_scan_posts()
  -> x_brief.dedup.filter_already_briefed()
  -> x_brief.curator.curate_briefing()
  -> x_brief.pipeline.export_briefing_json()
  -> data/latest-briefing.json
  -> web/src/app/api/briefing/route.ts
  -> web/src/components/briefing-view.tsx
```

### API Mode Flow

```text
Config tracked_accounts + X bearer token
  -> x_brief.fetcher.XClient
  -> x_brief.analyzer.infer_interests()
  -> x_brief.analyzer.build_search_queries()
  -> x_brief.curator.curate_briefing()
  -> x_brief.pipeline.export_briefing_json()
  -> data/latest-briefing.json
```

## Python Modules

- [`x_brief/models.py`](/home/cluvis/projects/x-brief/x_brief/models.py): Pydantic models for posts, users, media, quoted posts, briefing items, and config.
- [`x_brief/config.py`](/home/cluvis/projects/x-brief/x_brief/config.py): JSON config loading plus env-backed system config.
- [`x_brief/fetcher.py`](/home/cluvis/projects/x-brief/x_brief/fetcher.py): async X API client.
- [`x_brief/cache.py`](/home/cluvis/projects/x-brief/x_brief/cache.py): SQLite cache for user/post lookups in API mode.
- [`x_brief/scorer.py`](/home/cluvis/projects/x-brief/x_brief/scorer.py): post deduplication, scoring, ranking, and viral thresholds.
- [`x_brief/analyzer.py`](/home/cluvis/projects/x-brief/x_brief/analyzer.py): interest inference, post categorization, breakout detection, search query generation.
- [`x_brief/curator.py`](/home/cluvis/projects/x-brief/x_brief/curator.py): section assembly for VIRAL, TOP STORIES, YOUR CIRCLE, TRENDING, ARTICLES, and WORTH A LOOK.
- [`x_brief/dedup.py`](/home/cluvis/projects/x-brief/x_brief/dedup.py): cross-run brief history loading, filtering, saving, and cleanup.
- [`x_brief/scan_reader.py`](/home/cluvis/projects/x-brief/x_brief/scan_reader.py): scan JSON parsing, timestamp handling, metric parsing, and user synthesis.
- [`x_brief/enrichment.py`](/home/cluvis/projects/x-brief/x_brief/enrichment.py): syndication enrichment for richer media/cards after JSON export.
- [`x_brief/formatter.py`](/home/cluvis/projects/x-brief/x_brief/formatter.py): markdown, HTML, and plain-text formatting.
- [`x_brief/pipeline.py`](/home/cluvis/projects/x-brief/x_brief/pipeline.py): end-to-end orchestration and JSON export.
- [`x_brief/cli.py`](/home/cluvis/projects/x-brief/x_brief/cli.py): Click CLI entrypoints.

## Frontend Modules

- [`web/src/app/api/briefing/route.ts`](/home/cluvis/projects/x-brief/web/src/app/api/briefing/route.ts): reads `latest-briefing.json` from `X_BRIEF_DATA_DIR` or repo-local fallbacks.
- [`web/src/app/api/media/route.ts`](/home/cluvis/projects/x-brief/web/src/app/api/media/route.ts): media proxy for approved X media hosts.
- [`web/src/app/page.tsx`](/home/cluvis/projects/x-brief/web/src/app/page.tsx): app entrypoint.
- [`web/src/components/briefing-view.tsx`](/home/cluvis/projects/x-brief/web/src/components/briefing-view.tsx): tabbed briefing shell, polling, read state, media viewer integration.
- [`web/src/components/x-brief/post-card.tsx`](/home/cluvis/projects/x-brief/web/src/components/x-brief/post-card.tsx): individual post rendering.

The frontend has no Convex backend and no database layer. It is a renderer over the generated JSON file.

## Commands

### Python CLI

- `x-brief init --output config.json`
- `x-brief fetch --config configs/example.json --hours 24`
- `x-brief brief --config configs/example.json --hours 24 --format markdown`
- `x-brief accounts --config configs/example.json`
- `x-brief run --config configs/example.json --hours 24`

### Scan Pipeline Entrypoint

- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36 --scan-dir ./timeline_scans`
- `python -m x_brief.pipeline configs/example.json --from-scans --skip-dedup`

### Helper Script

- `python scripts/fetch_following.py`

This script pulls the accounts followed by `X_BRIEF_USERNAME` and can write the usernames back into a config file.

### Frontend

- `cd web && npm install`
- `cd web && npm run dev`
- `cd web && npm run build`
- `cd web && npm run lint`

## Output Contract

The shared artifact between backend and frontend is `data/latest-briefing.json`.

Current top-level shape:

- `generated_at`
- `period_hours`
- `sections[]`
- `stats`

Each section contains `title`, `emoji`, and `posts[]`. Posts include author fields, metrics, media, quoted post data, link card data when enriched, `postUrl`, and timestamps.

## Current Limits And Boundaries

- Scan mode is not exposed as a first-class Click command. It is run through `python -m x_brief.pipeline ... --from-scans`.
- `x-brief brief` is a lightweight API-mode formatter, not the same end-to-end pipeline as `run_briefing()` or `run_briefing_from_scans()`.
- API mode requires `X_BRIEF_BEARER_TOKEN`; scan mode does not.
- Scan ingestion depends on browser-agent JSON quality. Missing `/status/<id>` URLs cause posts to be dropped.
- Brief-history dedup is only active in scan mode when `--skip-dedup` is not used.
- Syndication enrichment is bounded and intentionally slow; it does not enrich every possible post in large runs.
- The frontend does not persist source data. It only reads the exported JSON file and keeps client-side read state in browser storage.
- The media proxy is intentionally restricted to X media hosts and will reject arbitrary URLs.

## Verification

- `python -m pytest tests/ -q`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `cd web && npm run lint`
- `curl http://localhost:3000/api/briefing`
