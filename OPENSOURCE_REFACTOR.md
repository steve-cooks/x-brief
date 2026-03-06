# Open Source Readiness Refactor Audit

Date: 2026-03-06

## 1. Cluvis/Steve-Specific Code To Generalize

- Hardcoded personal account target and output behavior in [`/home/cluvis/projects/x-brief/fetch_following.py`](/home/cluvis/projects/x-brief/fetch_following.py)
  - `@steve_cook` hardcoded (`:57-58`), writes to `configs/steve.json` (`:69`), writes outside repo to `~/projects/second-brain/steve_following.json` (`:80`).
- Hardcoded machine path in API route [`/home/cluvis/projects/x-brief/web/src/app/api/briefing/route.ts:16`](/home/cluvis/projects/x-brief/web/src/app/api/briefing/route.ts:16).
- Scan-mode default points to personal directory in [`/home/cluvis/projects/x-brief/x_brief/pipeline.py:145`](/home/cluvis/projects/x-brief/x_brief/pipeline.py:145).
- Personal config checked in: [`/home/cluvis/projects/x-brief/configs/steve.json`](/home/cluvis/projects/x-brief/configs/steve.json).
- README contains personal operational details (`Steve's following list`, personal path assumptions) at [`/home/cluvis/projects/x-brief/README.md:177`](/home/cluvis/projects/x-brief/README.md:177).

## 2. Prototype-Grade Areas Needing Cleanup

- CLI `brief` path is explicitly demo-mode and re-fetches only first 5 accounts (`x_brief/cli.py:207-218` behavior).
- Broad `except Exception` usage across pipeline/fetching/parsing reduces debuggability and can hide real failures.
- Heavy print/emoji logging across core modules instead of structured logging levels.
- Unauthenticated Convex data layer (`web/convex/*.ts`) is not production-safe.
- `web/src/app/api/analytics/route.ts` is stub-level and logs raw client data.

## 3. Dead Code / Unused / Debug Artifacts

- `sqlite-utils` declared dependency appears unused in codebase (only referenced in docs and `pyproject.toml`).
- `x_brief/pipeline.py` contains `enrich_briefing_json()` helper that is not called by the main flow.
- `web/src/app/test-video/page.tsx` appears diagnostic-only test page.
- Both `web/package-lock.json` and `web/pnpm-lock.yaml` are present, indicating mixed package-manager artifacts.
- `web/README.md` is default Next.js boilerplate and does not describe this app.

## 4. Missing Documentation

- No dedicated open-source setup guide for:
  - env vars and required/optional matrix,
  - scan-mode input expectations,
  - local vs hosted Convex setup,
  - security hardening defaults.
- No `.env.example` at repo root despite `.gitignore` allowing `!.env.example`.
- No contributor docs for test/lint/release workflow.
- No explicit threat model/security policy for public deployment.

## 5. Dependency Audit

### Python
- `pyproject.toml` uses lower-bound-only ranges (`>=`) for runtime deps, which reduces reproducibility.
- `sqlite-utils` likely removable (unused).
- No lockfile for Python dependencies.

### Web
- Core stack is pinned to modern versions (`next 16.1.6`, `react 19.2.3`), which is fine but high-churn; validate deployment/runtime compatibility.
- Duplicate lockfiles (`package-lock.json` + `pnpm-lock.yaml`) can cause drift and non-reproducible installs.

## 6. Prioritized Refactor Recommendations

## P0 (must fix before release)

1. Remove hardcoded token from `fetch_following.py`; rotate leaked credential.
2. Remove/replace all hardcoded personal paths and usernames (`/home/cluvis`, `steve_cook`, `~/projects/second-brain`).
3. Add authn/authz to all Convex mutations/queries before any public deployment.
4. Replace checked-in `configs/steve.json` with sanitized example config.
5. Add `.env.example` and security docs (required vars, secret handling, rotation).

## P1 (should fix)

1. Normalize package manager to one lockfile (`npm` or `pnpm`) and document it.
2. Replace ad-hoc prints with structured logging and explicit error classes.
3. Remove or gate debug/test routes (`/test-video`) and stub analytics endpoint.
4. Remove unused deps (`sqlite-utils`) or adopt them in actual code.
5. Add minimal CI: lint, typecheck, tests, and secret scan.

## P2 (nice to have)

1. Split personal/internal docs from OSS docs (`CONTEXT.md`, internal phase notes).
2. Introduce config schema docs and migration notes.
3. Add architecture diagrams specifically for OSS deploy targets.
