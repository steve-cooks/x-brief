# X Brief

X Brief is a self-hosted, AI-powered X/Twitter feed curator. **No API keys required.** It uses browser automation (via an OpenClaw agent) to scan your X timeline, curates and scores posts through a Python pipeline, and displays them in a clean Next.js web app, all running locally on your own machine.

- `No API keys required` (browser scan mode)
- `No dependencies on external services` (browser scan mode)

## Getting Started

For full setup from zero (scan mode, API mode, scan JSON format, cron automation, and web/service deployment), use [SETUP.md](./SETUP.md).  
If you are new to this repository, start there before using the shorter README quick start below.

## Screenshots / Demo

The web UI presents an X-style tabbed briefing with three sections:
- `Top Stories`
- `Articles`
- `Worth a Look`

To capture screenshots for this README, run the app locally and open `http://localhost:3000` after generating a briefing.

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
git clone https://github.com/<your-org>/x-brief.git
cd x-brief

# Python setup
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Generate/update briefing data
x-brief brief --config configs/example.json --hours 24 --format markdown

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
