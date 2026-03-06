# X Brief Context

## What This Is
X Brief is a two-part project: a Python pipeline that fetches/curates X (Twitter) posts into a structured briefing JSON, and a Next.js frontend that renders that JSON in an X-like tabbed UI. The operational center is `x_brief/` (fetch, analyze, score, curate, export), while `web/` is a separate app that reads `data/latest-briefing.json` and serves it via `/api/briefing` for client rendering.

## Stack
- Backend language/runtime: Python 3.10+ (`pyproject.toml`)
- Backend CLI: Click (`x_brief/cli.py`, command `x-brief`)
- Backend HTTP: `httpx` async client against X API v2 (`x_brief/fetcher.py`)
- Backend models: Pydantic v2 (`x_brief/models.py`)
- Backend storage: SQLite cache in `~/.x-brief/cache.db` (`x_brief/cache.py`)
- Frontend: Next.js App Router + React 19 + TypeScript (`web/package.json`)
- Frontend styling: Tailwind CSS v4 + shadcn/radix primitives (`web/src/components/ui/*`)
- Frontend state/theme: client-side fetch + `next-themes` (`web/src/components/briefing-view.tsx`)
- Optional data enrichment: X syndication endpoint (`x_brief/enrichment.py`)

## Architecture
- Primary flow: `X API/scan files -> dedup -> score -> curate sections -> export JSON -> web render`
- CLI entrypoints: `x-brief init|fetch|brief|accounts|run`
- End-to-end pipeline API mode: `x_brief.pipeline.run_briefing()`
- End-to-end pipeline scan mode: `x_brief.pipeline.run_briefing_from_scans()`
- JSON output contract: `data/latest-briefing.json` (written by pipeline)
- Web data read path: `web/src/app/api/briefing/route.ts`
- UI composition: `BriefingView -> tabs -> PostCard -> MediaViewer`
- Media proxy route: `web/src/app/api/media/route.ts` (allows only `video.twimg.com`, `pbs.twimg.com`)

## Patterns
- Async boundary pattern: network I/O is async (`XClient`), CLI wraps with `asyncio.run(...)`.
- Cache-first lookup pattern: username -> cache -> API fallback (`get_or_fetch_user_id`).
- Sectioned curation pattern: VIRAL, TOP STORIES, YOUR CIRCLE, TRENDING, WORTH A LOOK (`x_brief/curator.py`).
- Strong typed interchange: Python typed models -> JSON -> TS interfaces in UI.
- Dedup in layers: content dedup (`x_brief/scorer.py`) + history dedup (`x_brief/dedup.py`).
- Progressive enrichment: base JSON first, then optional syndication media/quote/link-card enrichment.
- Dynamic web rendering: homepage and API route are `force-dynamic` to avoid stale build-time data.

## Gotchas
- **Tailwind v4 — CSS-based config, NO `tailwind.config.ts`.** Uses `@import "tailwindcss"` syntax.
- **`cn()`/tailwind-merge EATS class overrides on Radix/shadcn components.** The merger strips "conflicting" classes. Use inline `style` props for reliable overrides on Radix primitives (especially Tabs).
- **`overflow-x-clip` over `overflow-hidden`** — `clip` doesn't create a scroll container, so `position: sticky` children still work. `hidden` breaks sticky.
- **Sticky tab nav `top-[54px]`** — header is 53px content + 1px border = 54px total.
- **CSS `!important` outside `@layer` is UNRELIABLE** for overriding Radix component defaults in Tailwind v4.
- **Service: `systemctl --user status x-brief-web.service`**. Dev server on port 3000.
- **Pipeline runs via cron** (4x daily via `x-brief-pipeline` cron) — data lives in `data/latest-briefing.json`.
- **Scan files come from `./timeline_scans/` by default** (or `X_BRIEF_SCAN_DIR`, e.g. `~/your-scan-dir/timeline_scans/`) from your browser agent.
- `x-brief brief` currently re-fetches recent posts (demo path) instead of being purely cache-driven.
- `web/src/app/api/briefing/route.ts` reads `X_BRIEF_DATA_DIR` first, then falls back to repo-relative `data/latest-briefing.json`.
- Sticky tabs can break if an ancestor uses `overflow: hidden`; bug notes are in `TAB_NAV_BUG.md`.
- Scan-mode pipeline default input is now `./timeline_scans/` (override with `X_BRIEF_SCAN_DIR`).
- `fetch_following.py` contains a hardcoded bearer token string; treat as sensitive and rotate/remove.
- Curator thresholds are opinionated and can hide low-engagement but important posts.
- `enrichment.py` only enriches up to `MAX_POSTS_PER_RUN = 30` and sleeps 1s/request.
- Some docs are stale vs current code (README says some modules are “not yet implemented”, but they exist).

## Testing
- Python tests are not present in-repo right now (no `tests/` directory, no discovered `test_*.py`).
- Frontend test framework is not configured (no Jest/Vitest/Playwright config found).
- Available quality gates are lint/build/manual-run checks.
- Python dev deps in `pyproject.toml` include `pytest`, `pytest-asyncio`, `black`, `ruff`.

## Verification
- Install backend package: `pip install -e .`
- Create config: `x-brief init --output config.json`
- Set required env: `export X_BRIEF_BEARER_TOKEN="..."`
- Fetch tracked accounts: `x-brief fetch --config config.json --hours 24`
- Run full pipeline: `x-brief run --config config.json --hours 24`
- Run scan pipeline directly: `python -m x_brief.pipeline configs/example.json --from-scans --hours 48`
- Optional enrichment pass: `python -m x_brief.enrichment data/latest-briefing.json`
- Start web app: `cd web && npm install && npm run dev`
- Build web app: `cd web && npm run build`
- Lint web app: `cd web && npm run lint`
- Smoke-check API JSON: `curl http://localhost:3000/api/briefing`
- Verify stale-data indicator logic in UI: generated timestamp > 12h shows warning in `BriefingView`.

## Key Files
- `README.md`: high-level setup/usage (partly outdated).
- `ARCHITECTURE.md`: product/phase intent and data flow.
- `pyproject.toml`: Python package metadata, deps, CLI entrypoint.
- `configs/example.json`: baseline user config shape.
- `configs/example.json`: baseline tracked-account config template.
- `x_brief/cli.py`: operational commands (`init/fetch/brief/accounts/run`).
- `x_brief/pipeline.py`: end-to-end orchestration and JSON export.
- `x_brief/fetcher.py`: X API v2 client, pagination/rate-limit handling.
- `x_brief/cache.py`: SQLite cache schema and lookup helpers.
- `x_brief/scorer.py`: dedup + scoring and viral multipliers.
- `x_brief/analyzer.py`: interest inference, categorization, query generation.
- `x_brief/curator.py`: section assembly and selection policy.
- `x_brief/scan_reader.py`: your browser agent scan JSON ingestion/parsing.
- `x_brief/enrichment.py`: syndication-based rich media/quote/link-card augmentation.
- `x_brief/dedup.py`: cross-brief history dedup store.
- `web/src/app/page.tsx`: frontend entrypoint.
- `web/src/app/api/briefing/route.ts`: JSON bridge from pipeline output to UI.
- `web/src/components/briefing-view.tsx`: tabbed shell, polling, stale-state UX.
- `web/src/components/x-brief/post-card.tsx`: post rendering details.
- `web/src/hooks/use-swipe-tabs.ts`: mobile swipe tab navigation.
- `web/src/app/api/media/route.ts`: media proxy with domain allowlist.
- `TAB_NAV_BUG.md`: known sticky/overflow regression details and fix constraints.
- `web/VERIFICATION_CHECKLIST.md`: manual UI acceptance checklist.
