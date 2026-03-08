# X Brief

X Brief is a self-hosted, scan-only X/Twitter briefing generator. It reads browser timeline scan JSON, curates and scores posts locally, writes `data/latest-briefing.json`, tracks pipeline health in `data/pipeline-status.json`, and serves results through the included Next.js frontend. No API keys are required.

![X Brief Screenshot](docs/images/screenshot.jpg)

## How It Works

```text
Browser agent / exported timeline scans
                |
                v
        timeline_scans/*.json
                |
                v
    Python pipeline (parse/score/curate)
                |
                v
      data/latest-briefing.json + data/pipeline-status.json
                |
                v
           Next.js frontend
```

## Quick Start

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

mkdir -p timeline_scans
cat > timeline_scans/sample.json <<'JSON'
{
  "scan_time": "2026-03-07T08:00:00Z",
  "posts": [
    {
      "url": "https://x.com/openai/status/1891111111111111111",
      "author": "@openai",
      "author_name": "OpenAI",
      "avatar_url": "https://pbs.twimg.com/profile_images/.../openai_normal.jpg",
      "text": "Example scan post for local setup validation.",
      "posted_at": "57m ago",
      "verified": true,
      "metrics": { "likes": "1200", "reposts": "80", "replies": "40", "views": "100K" }
    }
  ]
}
JSON

python -m x_brief.pipeline configs/example.json --from-scans --hours 24

cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Commands

- `x-brief init --output config.json`
- `x-brief brief --config configs/example.json --hours 36`
- `x-brief run --config configs/example.json --hours 36`
- `python -m x_brief.pipeline configs/example.json --from-scans --hours 36`

## Configuration

No `.env` file is required. The only supported environment variables are optional overrides:

| Variable | Required | Description |
|---|---|---|
| `X_BRIEF_SCAN_DIR` | No | Directory containing timeline scan JSON files |
| `X_BRIEF_DATA_DIR` | No | Directory where `latest-briefing.json` is written/read |

`configs/example.json` includes:

- `tracked_accounts`: optional context for who you care about
- `recent_interests`: topics used during curation
- `delivery` and `briefing_schedule`: preserved config fields for downstream integrations

## Frontend

From `web/`:

```bash
npm install
npm run dev
```

The frontend reads `latest-briefing.json` from `X_BRIEF_DATA_DIR` when set, otherwise from the repo-local `data/` directory.

Pipeline health is written to `pipeline-status.json` in the same data directory. A companion API route (for example `web/src/app/api/pipeline-status/route.ts`) can read this file so the UI can display scan/pipeline health.

## More Detail

Use [SETUP.md](./SETUP.md) for the full scan-only setup, scan file format, automation examples, and troubleshooting.  
Use [ARCHITECTURE.md](./ARCHITECTURE.md) for the module-level system map.

## License

MIT. See [LICENSE](./LICENSE).
