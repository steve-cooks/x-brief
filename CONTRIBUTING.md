# Contributing to X Brief

Thanks for helping improve X Brief.

Our north star: **less scrolling, more signal**.

## Principles

- Prioritize usefulness over novelty.
- Keep anti-addiction intent intact (brevity, clarity, quality gates).
- Prefer simple, local, transparent systems over complex infrastructure.

## Repo map

- `x_brief/` — Python pipeline (scan ingest, scoring, curation, export)
- `tests/` — backend tests
- `configs/` — example config
- `web/` — Next.js UI and API routes reading generated JSON
- `docs/images/` — README assets

## Local setup

```bash
git clone https://github.com/steve-cooks/x-brief.git
cd x-brief

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

cd web
npm install
cd ..
```

## Workflow

1. Create a branch from `master`
2. Keep changes focused (one idea per PR)
3. Update docs/tests with code changes
4. Run checks locally
5. Open PR with clear context

## Required checks

```bash
python3 -m pytest tests/ -q
cd web && npm run build
```

If you touched frontend behavior, run dev server too:

```bash
cd web && npm run dev
```

## What to include in PRs

- What changed
- Why it changed (especially anti-addiction/quality rationale)
- Before/after behavior
- Any follow-up work or known limitations

## Documentation expectations

If behavior changes, update relevant docs in the same PR:

- `README.md`
- `SETUP.md`
- `ARCHITECTURE.md`
- `SPEC-v2-curation.md` (if curation logic changed)

## Style guidelines

- Prefer readability over cleverness.
- Add/adjust docstrings for non-obvious logic.
- Keep interfaces backward compatible when possible.
- Avoid introducing external services when local files suffice.

## Reporting bugs

Open an issue with:
- reproduction steps
- expected vs actual behavior
- logs or screenshots if useful
- environment (OS, Python, Node versions)

## Code of conduct

Be respectful, direct, and constructive.
