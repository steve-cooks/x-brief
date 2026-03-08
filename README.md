# X Brief

X Brief is a self-hosted, AI-powered X/Twitter feed curator. **No API keys required.** It uses browser automation (via an OpenClaw agent) to scan your X timeline, curates and scores posts through a Python pipeline, and displays them in a clean Next.js web app, all running locally on your own machine.

- `No API keys required` (browser scan mode)
- `No dependencies on external services` (browser scan mode)

## Getting Started

For full setup from zero (scan mode, API mode, scan JSON format, cron automation, and web/service deployment), use [SETUP.md](./SETUP.md).  
If you are new to this repository, start there before using the shorter README quick start below.

## Screenshots / Demo

After generating a briefing, `http://localhost:3000` opens a clean, local web interface with X-style tabs (for example: Top Stories, Viral, Your Circle, Articles, Trending, Worth a Look depending on available data).

Each section highlights ranked posts with summaries, links, and metadata so you can quickly review the most relevant items from your timeline.

## How It Works

X Brief follows a simple local data flow:

```text
Browser Agent (OpenClaw) or X API
            |
            v
      scan JSON input
            |
            v
 Python pipeline (curate/score/dedup)
            |
            v
   data/latest-briefing.json
            |
            v
       Next.js frontend
```

Architecture overview:
- Input layer: Browser scan mode (OpenClaw automation) or API mode (X bearer token)
- Processing layer: Python pipeline deduplicates, scores, and organizes posts by relevance
- Output layer: `latest-briefing.json` drives the web frontend
- Scheduling layer: Cron can run scans every 4 hours for a continuously fresh briefing

## Requirements

- Python `3.10+`
- Node.js `18+`
- OpenClaw installed (for browser scan mode)

Optional for API mode only:
- X API bearer token

## Quick Start

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

# Python setup
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Create one sample scan file (so scan mode works out of the box)
mkdir -p timeline_scans
cat > timeline_scans/sample.json <<'JSON'
{
  "scan_time": "2026-03-07T08:00:00Z",
  "posts": [
    {
      "url": "https://x.com/openai/status/1891111111111111111",
      "author": "@openai",
      "author_name": "OpenAI",
      "text": "Example scan post for local setup validation.",
      "posted_at": "57m ago",
      "verified": true,
      "metrics": { "likes": "1200", "reposts": "80", "replies": "40", "views": "100K" }
    }
  ]
}
JSON

# Generate/update briefing data (scan mode, no API key)
python -m x_brief.pipeline configs/example.json --from-scans --hours 24

# Frontend setup
cd web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Configuration

For browser scan mode, no `.env` file is required. Environment variables are optional overrides:

| Variable | Required | Description |
|---|---|---|
| `X_BRIEF_BEARER_TOKEN` | No* | X API bearer token (required only for API mode) |
| `X_BRIEF_SCAN_DIR` | No | Directory containing browser scan JSON files |
| `X_BRIEF_DATA_DIR` | No | Directory where briefing outputs are written/read |

`*` Optional in browser scan mode.

## Modes

### Browser Scan Mode (No API Key)

- Uses OpenClaw browser automation to scan your X timeline
- No API keys needed
- No `.env` file needed
- Best for local, self-hosted use when you already run OpenClaw

### API Mode (Bearer Token Required)

- Pulls data from X API endpoints
- Requires `X_BRIEF_BEARER_TOKEN`
- Useful when you want a direct API-driven workflow

## Running the Web Frontend

From the `web/` directory:

```bash
npm install
npm run dev
```

Then open `http://localhost:3000`.

## Contributing

Contributions are welcome.

- Open an issue describing the bug or enhancement
- Submit a focused pull request with clear before/after behavior
- Include tests or reproduction steps when possible

## License

MIT. See [LICENSE](./LICENSE).
