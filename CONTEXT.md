# X Brief Context

## Current State

X Brief is scan-first with a lightweight web app:

- Python pipeline ingests timeline scan JSON and exports `data/latest-briefing.json`.
- Next.js frontend reads JSON via `/api/briefing` and renders the briefing UI.
- Section model is now **3 categories only**: **VIRAL 🔥**, **TOP PICKS 📌**, **FOLLOWING 👥**.

## Recent Product Changes

- 3-category briefing system (Viral, Top Picks, Following)
- Article support (`is_article`, `article_url` in scan + export path)
- Thread detection/support (`thread_posts` attached during scan ingest)
- Async enrichment (`enrich_with_syndication_async` after JSON export)
- PWA support in web app
- In-app search/filter in the briefing UI
- Pin/save posts feature (Saved tab + persisted saved URLs)
- Scan/source field support (`source: for_you | following`)
- Server-side read state (`/api/read-state` sync + local fallback)
- Pipeline health status file (`data/pipeline-status.json`)

## Code Map

- [`x_brief/pipeline.py`](./x_brief/pipeline.py): scan orchestration, JSON export, pipeline-status writes.
- [`x_brief/scan_reader.py`](./x_brief/scan_reader.py): resilient scan parsing (skips invalid files, continues).
- [`x_brief/curator.py`](./x_brief/curator.py): section assembly and ranking for 3 categories.
- [`x_brief/scorer.py`](./x_brief/scorer.py): engagement scoring + in-run dedup.
- [`x_brief/dedup.py`](./x_brief/dedup.py): history cleanup + recent-window dedup filtering.
- [`x_brief/enrichment.py`](./x_brief/enrichment.py): optional post-export enrichment.
- [`x_brief/cli.py`](./x_brief/cli.py): `init`, `brief`, `run` commands.
- [`web/src/app/api/briefing/route.ts`](./web/src/app/api/briefing/route.ts): server JSON bridge.
- [`web/src/app/api/read-state/route.ts`](./web/src/app/api/read-state/route.ts): server read-state persistence.
- [`web/src/app/api/saved/route.ts`](./web/src/app/api/saved/route.ts): server saved-post persistence.
- [`web/src/components/briefing-view.tsx`](./web/src/components/briefing-view.tsx): tabs, search, save, read tracking, stale warnings.

## Commands That Matter

- `x-brief init --output config.json`
- `x-brief brief --config configs/example.json --hours 36`
- `x-brief run --config configs/example.json --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `python -m pytest tests/ -q`
- `cd web && npm run dev`

## Important Behavior

- `x-brief brief` and `x-brief run` work without API credentials.
- `python -m x_brief.pipeline ... --from-scans` remains the module entrypoint.
- Scan loading is fault-tolerant: bad/invalid JSON files are logged and skipped.
- Cross-brief dedup only blocks posts briefed within the active dedup window (default 48h; pipeline passes `--hours`).
- Pipeline writes:
  - `latest-briefing.json`
  - `brief_history.json`
  - `pipeline-status.json`
- Frontend reads server data first and falls back to local state where needed.

## Env And Paths

- `X_BRIEF_SCAN_DIR`: optional input override. Default: `./timeline_scans/`.
- `X_BRIEF_DATA_DIR`: optional output/read directory override.
- `web/.env.local`: local-only, gitignored.

## Gotchas

- `recent_interests` is the config field (not `interests`).
- Scan posts without parsable post/article IDs are ignored.
- Dedup can be bypassed with `--skip-dedup` (web mode/manual reruns).
- Enrichment is intentionally bounded/rate-limited.
- Media proxy only allows approved X domains.

## Tests

Focused pytest coverage exists for:

- [`tests/test_scorer.py`](./tests/test_scorer.py)
- [`tests/test_dedup.py`](./tests/test_dedup.py)
- [`tests/test_curator.py`](./tests/test_curator.py)
- [`tests/test_models.py`](./tests/test_models.py)
- [`tests/test_pipeline.py`](./tests/test_pipeline.py)
- [`tests/test_scan_reader.py`](./tests/test_scan_reader.py)
