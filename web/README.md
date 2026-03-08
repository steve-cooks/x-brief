# X Brief Web Frontend

This Next.js app renders `data/latest-briefing.json` produced by the Python pipeline.

## Run locally

```bash
cd web
npm install
npm run dev
```

Open <http://localhost:3000> (or the next available port if 3000 is busy).

## Data source

The API route at `src/app/api/briefing/route.ts` reads:

1. `${X_BRIEF_DATA_DIR}/latest-briefing.json` (when `X_BRIEF_DATA_DIR` is set), or
2. `../data/latest-briefing.json` from the repo root.

Generate briefing data first (scan mode):

```bash
cd ..
python -m x_brief.pipeline configs/example.json --from-scans --hours 24
```

## Useful commands

```bash
npm run dev
npm run build
npm run lint
```

Note: `npm run lint` currently reports some warnings/errors in UI code; build and runtime are still functional.
