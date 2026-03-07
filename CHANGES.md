# P0 Open Source Readiness Changes

Date: 2026-03-06

## Security and Secrets
- Removed hardcoded bearer token from `fetch_following.py`.
- Added env-based token loading: `X_BRIEF_BEARER_TOKEN`.
- Added fail-fast check in `fetch_following.py` when token is missing.
- Added basic payload size limit (50KB) for `web/src/app/api/analytics/route.ts`.
- Added production hardening warning comment to analytics endpoint.

## Path and Personal Data Generalization
- Replaced machine-specific fallback path in `web/src/app/api/briefing/route.ts`.
- Added env-driven data directory support via `X_BRIEF_DATA_DIR` in briefing API route.
- Updated scan pipeline default in `x_brief/pipeline.py` to use `X_BRIEF_SCAN_DIR` or `./timeline_scans/`.
- Sanitized personal names/paths in:
  - `README.md`
  - `CONTEXT.md`
  - `ARCHITECTURE.md`
  - `PHASE2_COMPLETE.md`

## Config and Env Templates
- Replaced `configs/example.json` content with a generic open-source-safe example.
- Kept user-specific local config files in place for now (not deleted).
- Added root `.env.example` with documented variables:
  - `X_BRIEF_BEARER_TOKEN`
  - `X_BRIEF_ANTHROPIC_KEY`
  - `X_BRIEF_SCAN_DIR`
  - `X_BRIEF_DATA_DIR`
- Added `web/.env.example` with placeholder Convex/web env vars.

## Convex Guard Rails
- Added top-of-file security warning comments in:
  - `web/convex/users.ts`
  - `web/convex/briefings.ts`
  - `web/convex/preferences.ts`
- Added minimal auth presence checks (`ctx.auth.getUserIdentity()`) in mutation handlers.
- Added non-empty `userId` guard checks in mutation handlers that accept `userId`.

## Gitignore
- Updated `.gitignore` to ignore user configs while keeping the template tracked:
  - `configs/*.json`
  - `!configs/example.json`
