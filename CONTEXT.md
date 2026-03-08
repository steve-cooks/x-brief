# X Brief Context

## Current State

X Brief is scan-only:

- A Python package ingests browser timeline scan JSON, curates a briefing, and exports `data/latest-briefing.json`.
- A Next.js frontend reads that JSON through `/api/briefing` and renders the UI.

## Code Map

- [`x_brief/pipeline.py`](./x_brief/pipeline.py): scan-only orchestration and JSON export.
- [`x_brief/scan_reader.py`](./x_brief/scan_reader.py): parser for browser scan files.
- [`x_brief/curator.py`](./x_brief/curator.py): section assembly logic.
- [`x_brief/scorer.py`](./x_brief/scorer.py): ranking, viral thresholds, and in-run deduplication.
- [`x_brief/dedup.py`](./x_brief/dedup.py): cross-brief history store.
- [`x_brief/enrichment.py`](./x_brief/enrichment.py): optional syndication enrichment after JSON export.
- [`x_brief/cli.py`](./x_brief/cli.py): Click commands for `init`, `brief`, and `run`.
- [`web/src/app/api/briefing/route.ts`](./web/src/app/api/briefing/route.ts): server-side JSON bridge for the frontend.
- [`web/src/components/briefing-view.tsx`](./web/src/components/briefing-view.tsx): tabbed briefing UI.

## Commands That Matter

- `x-brief init --output config.json`
- `x-brief brief --config configs/example.json --hours 36`
- `x-brief run --config configs/example.json --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `python -m pytest tests/ -q`
- `cd web && npm run dev`

## Important Behavior

- `x-brief brief` and `x-brief run` both work without API credentials.
- `python -m x_brief.pipeline ... --from-scans` remains the module entrypoint for scan execution.
- `x-brief init` writes `recent_interests` with neutral sample defaults.
- The pipeline writes `latest-briefing.json` and optional brief-history state into `X_BRIEF_DATA_DIR` when set, otherwise into repo-local `data/`.
- The frontend renders the exported JSON without its own database.

## Env And Paths

- `X_BRIEF_SCAN_DIR`: optional override for scan JSON input. Default is `./timeline_scans/`.
- `X_BRIEF_DATA_DIR`: optional override for where the pipeline writes and the frontend reads `latest-briefing.json`.
- `web/.env.local` should remain local-only. It is gitignored and should not be tracked.

## Gotchas

- `recent_interests` is the current config field. Older docs that say `interests` are stale.
- Scan posts without a `/status/<numeric_id>` URL are ignored by the parser.
- `x_brief/dedup.py` only suppresses already-briefed posts when the scan pipeline runs without `--skip-dedup`.
- `x_brief/enrichment.py` is rate-limited on purpose and only enriches a bounded number of posts per run.
- `web/src/app/api/media/route.ts` only proxies approved X media domains.
- The frontend hides already-read posts per browser session via local storage, not via backend state.

## Tests

Focused pytest coverage exists for:

- [`tests/test_scorer.py`](./tests/test_scorer.py)
- [`tests/test_dedup.py`](./tests/test_dedup.py)
- [`tests/test_curator.py`](./tests/test_curator.py)
- [`tests/test_models.py`](./tests/test_models.py)
- [`tests/test_pipeline.py`](./tests/test_pipeline.py)
