# Open Source Readiness Audit (Final)

Date: 2026-03-08
Scope: full tracked repository (`git ls-files`) plus setup/runtime verification.

## Critical (fixed)

1. **CLI false-success on missing bearer token**
   - `x-brief fetch` and `x-brief brief` printed an error but exited `0` when `X_BRIEF_BEARER_TOKEN` was unset.
   - Impact: scripts/agents think command succeeded when it actually failed.
   - Fix: both commands now raise `click.ClickException` (non-zero exit).
   - Validation: new tests in `tests/test_cli.py`.

2. **`x-brief init` used stale field (`interests`)**
   - Init sample wrote legacy/ignored field and produced empty `recent_interests` in saved config.
   - Impact: generated config less useful; docs/model mismatch.
   - Fix: init now writes `recent_interests` with neutral defaults.
   - Validation: new test in `tests/test_cli.py`.

3. **README quick start did not match no-key primary flow**
   - README claimed “No API keys required” but quickstart used `x-brief brief` (API mode; requires bearer token).
   - Impact: first-run failure for new users.
   - Fix: quickstart now demonstrates scan mode with a minimal sample scan JSON, then runs `python -m x_brief.pipeline --from-scans`.

## Should-Fix (partially fixed)

1. **Web README was generic Next.js template**
   - Fixed: replaced with project-specific instructions and data-path behavior.

2. **Docs drift in context/orientation**
   - Fixed: updated `CONTEXT.md` to reflect current behavior:
     - scan mode command surfaced explicitly
     - fail-fast CLI behavior
     - `recent_interests` init behavior

3. **Frontend lint has existing issues**
   - `npm run lint` reports 2 errors + warnings in UI files; `npm run build` succeeds.
   - Not fixed in this pass (outside critical launch blockers for basic local run).

## Nice-to-Have

1. Add first-class scan command to click CLI (e.g. `x-brief scan-brief ...`) instead of `python -m x_brief.pipeline ... --from-scans`.
2. Add frontend lint/build to CI to prevent drift.
3. Reduce stale auxiliary docs in `web/` (redesign/checklist docs can confuse new contributors).

## Verification Performed

- Python install:
  - `python3 -m venv /tmp/xbrief-audit-venv`
  - `pip install -e .`
  - `pip install -e '.[dev]'`
- Python tests:
  - `python -m pytest tests/ -q` → passing (22 total after new tests)
- Scan pipeline:
  - `python -m x_brief.pipeline configs/example.json --from-scans --hours 24`
- CLI behavior:
  - confirmed non-zero exits for missing bearer in `fetch`/`brief`
- Web frontend:
  - `cd web && npm install`
  - `npm run dev` (starts successfully)
  - `npm run build` (passes)
  - `npm run lint` (reports existing non-blocking issues for launch run-path)
- Secret/path checks:
  - scanned tracked files for obvious secrets/tokens/absolute personal paths
  - checked git history for token-like patterns (historical redacted token markers present; no active tracked secret found)
