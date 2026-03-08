# X Brief Architecture

## System overview

X Brief is a local-first scan pipeline plus web renderer.

1. Timeline scans are written as JSON snapshots.
2. Python pipeline ingests, scores, and curates posts.
3. Pipeline exports JSON artifacts to `data/`.
4. Next.js app reads those artifacts and renders the briefing UI.

```text
timeline_scans/*.json
  -> x_brief.scan_reader.load_scan_posts()
  -> x_brief.dedup.filter_already_briefed()
  -> x_brief.curator.curate_briefing()
  -> x_brief.pipeline.export_briefing_json()
  -> data/latest-briefing.json + data/pipeline-status.json
  -> web/src/app/api/briefing/route.ts
  -> web/src/components/briefing-view.tsx
```

---

## Backend modules (`x_brief/`)

- `models.py` — Pydantic data models
- `config.py` — load/save user config
- `scan_reader.py` — parse scan files into normalized posts
- `scorer.py` — engagement+density scoring, in-batch dedup
- `curator.py` — 3-tab curation (Can't Miss / For You / Following)
- `dedup.py` — brief-history filtering + re-emergence logic
- `enrichment.py` — syndication enrichment (full post text, media, quotes, link cards, avatars)
- `pipeline.py` — orchestrates full run and writes artifacts
- `cli.py` — `init`, `brief`, `run` commands

---

## Frontend modules (`web/src/`)

- `app/api/briefing/route.ts` — reads `latest-briefing.json`
- `app/api/read-state/route.ts` — persists read IDs
- `app/api/media/route.ts` — safe proxy for X media domains
- `components/briefing-view.tsx` — tab shell, search, refresh, read-time, stale warnings
- `components/x-brief/post-card.tsx` — post rendering (media/thread/quote/link card)
- `components/media-viewer.tsx` — full-screen media lightbox

---

## Data contracts

## `latest-briefing.json`

Top-level keys:
- `generated_at`
- `period_hours`
- `sections[]` (each with `title`, `emoji`, `posts[]`)
- `stats`

Each post includes author, text, metrics, media, URL, timestamps, optional thread/quote/article/link-card data.

## `pipeline-status.json`

Success shape:
```json
{ "status": "ok", "last_success": "ISO", "posts_processed": 42, "sections": 3 }
```

Error shape:
```json
{ "status": "error", "error": "...", "last_success": "ISO|null", "last_attempt": "ISO" }
```

---

## Runtime boundaries

- Scan quality depends on upstream scraper output.
- Posts without parseable IDs are dropped.
- Enrichment is bounded/rate-limited.
- No database is required.
- Frontend state is mostly local/browser + small JSON files.

---

## Verification

```bash
python3 -m pytest tests/ -q
python -m x_brief.pipeline configs/example.json --from-scans --hours 36
cd web && npm run build
```
