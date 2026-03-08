# X Brief Context

## Current State

X Brief currently ships as:

- A Python package that ingests X data, curates a briefing, and exports `data/latest-briefing.json`.
- A Next.js frontend that reads that JSON through `/api/briefing` and renders an X-style tabbed UI.

The active, best-supported workflow is scan mode. Browser automation writes scan JSON files, `python -m x_brief.pipeline ... --from-scans` converts them into the briefing artifact, and the web app displays the result.

## Code Map

- [`x_brief/pipeline.py`](./x_brief/pipeline.py): main orchestration for API mode and scan mode.
- [`x_brief/scan_reader.py`](./x_brief/scan_reader.py): parser for browser scan files.
- [`x_brief/curator.py`](./x_brief/curator.py): section assembly logic.
- [`x_brief/scorer.py`](./x_brief/scorer.py): ranking, viral thresholds, and in-run deduplication.
- [`x_brief/dedup.py`](./x_brief/dedup.py): cross-brief history store.
- [`x_brief/enrichment.py`](./x_brief/enrichment.py): optional syndication enrichment after JSON export.
- [`x_brief/cli.py`](./x_brief/cli.py): Click commands for init/fetch/brief/accounts/run.
- [`scripts/fetch_following.py`](./scripts/fetch_following.py): helper for syncing followed accounts into config.
- [`web/src/app/api/briefing/route.ts`](./web/src/app/api/briefing/route.ts): server-side JSON bridge for the frontend.
- [`web/src/components/briefing-view.tsx`](./web/src/components/briefing-view.tsx): tabbed briefing UI.

## Commands That Matter

- `x-brief init --output config.json`
- `x-brief fetch --config configs/example.json --hours 24`
- `x-brief brief --config configs/example.json --hours 24 --format markdown` (API mode)
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 24` (scan mode)
- `x-brief run --config configs/example.json --hours 24`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`
- `python scripts/fetch_following.py`
- `python -m pytest tests/ -q`
- `cd web && npm run dev`

## Important Behavior

- `x-brief run` uses the API-backed pipeline in [`x_brief/pipeline.py`](./x_brief/pipeline.py).
- Scan mode is currently only exposed through `python -m x_brief.pipeline ... --from-scans`.
- `x-brief brief` is still a lighter API-mode briefing path. It does not go through the full scan-mode pipeline.
- `x-brief fetch` and `x-brief brief` now fail fast with non-zero exit when `X_BRIEF_BEARER_TOKEN` is missing.
- `x-brief init` writes `recent_interests` (not legacy `interests`) with neutral sample defaults.
- Scan mode writes `data/latest-briefing.json`; the frontend renders that file without its own persistence layer.
- The frontend has no Convex integration anymore.

## Env And Paths

- `X_BRIEF_BEARER_TOKEN`: required for API mode and `scripts/fetch_following.py`.
- `X_BRIEF_SCAN_DIR`: optional override for scan JSON input. Default is `./timeline_scans/`.
- `X_BRIEF_DATA_DIR`: optional override for where the frontend API route reads `latest-briefing.json`.
- `web/.env.local` should remain local-only. It is gitignored and should not be tracked.

## Gotchas

- `recent_interests` is the current config field. Older docs that say `interests` are stale.
- Scan posts without a `/status/<numeric_id>` URL are ignored by the parser.
- `x-brief brief` still requires an API bearer token even though the project’s main local flow is scan-based.
- For no-key setup demos, use scan mode (`python -m x_brief.pipeline ... --from-scans`) rather than `x-brief brief`.
- `x_brief/dedup.py` only suppresses already-briefed posts when the scan pipeline runs without `--skip-dedup`.
- `x_brief/enrichment.py` is rate-limited on purpose and only enriches a bounded number of posts per run.
- `web/src/app/api/media/route.ts` only proxies approved X media domains.
- The frontend hides already-read posts per browser session via local storage, not via backend state.
- `web/.env.example` now documents only `X_BRIEF_DATA_DIR`; there is no active frontend backend configuration beyond file location.

## Tests

Focused pytest coverage now exists for:

- [`tests/test_scorer.py`](./tests/test_scorer.py)
- [`tests/test_dedup.py`](./tests/test_dedup.py)
- [`tests/test_curator.py`](./tests/test_curator.py)
- [`tests/test_models.py`](./tests/test_models.py)
