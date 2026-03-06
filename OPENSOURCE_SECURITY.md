# Open Source Security & Credentials Audit

Date: 2026-03-06
Scope reviewed: all `x_brief/*.py`, `fetch_following.py`, all `web/src/**`, `configs/**`, `.env`, `web/.env.local`, `.gitignore`, plus related app/config files likely to carry secrets.

## 1. Hardcoded Secrets / Sensitive Values

### Critical
- [`/home/cluvis/projects/x-brief/fetch_following.py:9`](/home/cluvis/projects/x-brief/fetch_following.py:9)
  - Hardcoded X bearer token in source:
  - `BEARER_TOKEN = "AAAAAAAA..."`
  - This file is tracked by git (`git ls-files` includes it).

### High
- [`/home/cluvis/projects/x-brief/.env:1`](/home/cluvis/projects/x-brief/.env:1)
  - `X_BRIEF_BEARER_TOKEN=<real token>`
  - Local file, ignored by git, but still active sensitive credential on disk.

- [`/home/cluvis/projects/x-brief/web/.env.local:2`](/home/cluvis/projects/x-brief/web/.env.local:2)
  - `CONVEX_SELF_HOSTED_ADMIN_KEY='convex-self-hosted|...'`
  - Local file, ignored by git, but is an admin key and must never be exposed client-side.

### Sensitive personal data (not credential, but should not be default OSS payload)
- [`/home/cluvis/projects/x-brief/configs/steve.json:1`](/home/cluvis/projects/x-brief/configs/steve.json:1)
  - Personal profile and large real tracked account list.

## 2. Environment Variable Inventory

| Variable | Where used | Required? | Frontend-exposed? | In `.gitignore` coverage |
|---|---|---|---|---|
| `X_BRIEF_BEARER_TOKEN` | `x_brief/config.py:24`, `x_brief/pipeline.py:21`, CLI runtime checks | Yes for fetch/pipeline | No | Yes (`.env`, `.env.*`) |
| `X_BRIEF_ANTHROPIC_KEY` | `x_brief/config.py:26` | Optional currently (not actively used in pipeline) | No | Yes (`.env`, `.env.*`) |
| `CONVEX_SELF_HOSTED_URL` | `web/.env.local:1` (Convex runtime config) | Required for current local self-hosted Convex setup | No | Yes (`.env.local`, `.env.*`) |
| `CONVEX_SELF_HOSTED_ADMIN_KEY` | `web/.env.local:2` | Required for Convex admin operations | No (must remain server-only) | Yes (`.env.local`, `.env.*`) |
| `NEXT_PUBLIC_CONVEX_URL` | `web/.env.local:4` | Required if frontend uses Convex client endpoint | Yes (`NEXT_PUBLIC_*`) | Yes (`.env.local`, `.env.*`) |
| `NEXT_PUBLIC_CONVEX_SITE_URL` | `web/.env.local:6` | Optional depending on Convex UI usage | Yes (`NEXT_PUBLIC_*`) | Yes (`.env.local`, `.env.*`) |

Notes:
- `NEXT_PUBLIC_*` values are intentionally exposed to browser bundles.
- No code path should ever place `CONVEX_SELF_HOSTED_ADMIN_KEY` into `NEXT_PUBLIC_*` vars.

## 3. `.gitignore` Audit

### Sensitive items currently excluded
- `.env`, `.env.local`, `.env.*`
- `secrets.json`, `secrets/`
- `*.key`, `*.pem`
- build artifacts and caches (`node_modules`, `.next`, `data/`, etc.)

### Missing or weak for open-source release
- No ignore rule for user-specific runtime configs such as `config.json` (created by `x-brief init`), which can include personal handles and delivery metadata.
- No pattern for private config variants (recommend `configs/*.local.json` and/or `config*.local.json`).
- No pre-commit secret scanner config/ignore policy file (not `.gitignore` itself, but release hygiene gap).

## 4. Other Security Risks

### P0 (must fix before public release)
- Unauthenticated data mutation/query surface in Convex functions.
  - `web/convex/users.ts`, `web/convex/briefings.ts`, `web/convex/preferences.ts` accept `userId`/`email` directly with no auth checks in handlers.
  - Risk: unauthorized read/write across user records if deployed.

- Public analytics ingestion endpoint without auth or size controls.
  - [`/home/cluvis/projects/x-brief/web/src/app/api/analytics/route.ts:29`](/home/cluvis/projects/x-brief/web/src/app/api/analytics/route.ts:29)
  - Accepts arbitrary JSON and logs to stdout.
  - Risk: log spam/poisoning and resource abuse.

### P1 (should fix)
- Media proxy endpoint is publicly callable and allows wildcard CORS.
  - [`/home/cluvis/projects/x-brief/web/src/app/api/media/route.ts:40`](/home/cluvis/projects/x-brief/web/src/app/api/media/route.ts:40)
  - `Access-Control-Allow-Origin: *` with no auth/rate limiting.
  - Host allowlist exists (good), but endpoint can still be abused as public bandwidth relay.

- Sensitive local file fallback path in API route.
  - [`/home/cluvis/projects/x-brief/web/src/app/api/briefing/route.ts:16`](/home/cluvis/projects/x-brief/web/src/app/api/briefing/route.ts:16)
  - Hardcoded absolute filesystem path leaks operator username/layout and is brittle.

### P2 (nice to have)
- Extensive stdout logging of pipeline activity in production paths (`x_brief/pipeline.py`, `x_brief/cli.py`) can leak operational metadata in hosted logs.

## Immediate Remediation Checklist

1. Rotate/revoke exposed X bearer token immediately (both source and local `.env` copies).
2. Remove hardcoded token from `fetch_following.py`; load from env only.
3. Add auth/authorization inside all Convex mutations/queries before deployment.
4. Add auth + payload size/rate limits to `/api/analytics`; consider disabling in OSS template.
5. Restrict `/api/media` CORS to your frontend origin and add rate limiting.
6. Replace hardcoded filesystem fallback paths with configurable env-based paths.
7. Add `.env.example` (sanitized) and a secret-scanning gate in CI.
