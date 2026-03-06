# SaaS Analysis: X Brief

## 1) Current State

### What Exists
- A working Python pipeline (`x_brief/`) that can:
  - Ingest X content from two sources:
    - Official X API (`fetcher.py`, `pipeline.run_briefing`)
    - Rabbit/browser scan JSON dumps (`scan_reader.py`, `pipeline.run_briefing_from_scans`)
  - Score, deduplicate, and section content (`scorer.py`, `curator.py`, `dedup.py`)
  - Export one canonical JSON output (`data/latest-briefing.json`)
  - Optionally enrich media/quotes/link cards via X syndication endpoint (`enrichment.py`)
- A Next.js frontend (`web/src`) that renders that JSON in an X-like tabbed feed with:
  - Read-state persistence in localStorage
  - Client-side analytics in localStorage
  - Media proxy endpoint
  - Polling-based refresh
- CLI operations (`x-brief init/fetch/brief/accounts/run`) and cron/systemd-style local ops.

### Prototype-Grade (Not Production-Ready)
- Single-machine assumptions everywhere:
  - Hardcoded/local filesystem paths in pipeline and web API fallback.
  - Cron + local file output model.
- No real backend service boundary:
  - No persistent API layer for tenants/jobs/state.
  - No queue/workers for reliable execution.
- No tests for backend/frontend behavior.
- Error handling is mostly print-and-continue.
- Secrets hygiene issues:
  - `fetch_following.py` contains a hardcoded bearer token (critical operational/security smell).
- Data correctness and consistency issues:
  - Some docs are stale vs code.
  - `UserConfig` shape in code diverges from example fields (`interests` vs `recent_interests`).

### Production-Ready-ish Parts (Reusable Foundation)
- Typed data models (Pydantic) and clear transformation flow.
- Functional curation/scoring pipeline with dedup strategies.
- Frontend rendering quality is solid for MVP UX.
- Media proxy allowlist in place (basic control).

Bottom line: this is a strong single-user/operator prototype, not a SaaS platform.

## 2) Multi-Tenancy Gaps

### Hardcoded Paths / Single-Tenant Assumptions
- Web API fallback path is machine-specific (`/home/cluvis/projects/x-brief/data/latest-briefing.json`).
- Scan input defaults to an external personal directory (`~/projects/second-brain/timeline_scans/`).
- Output is always one shared file: `data/latest-briefing.json`.
- Brief history dedup uses one shared file: `data/brief_history.json`.

### Single User Data Model
- One config file per run (`configs/*.json`), no tenant/user identity boundary.
- Cache DB defaults to one local SQLite file in home dir (`~/.x-brief/cache.db`), shared scope.
- No per-user namespace for:
  - tracked accounts
  - interests
  - dedup history
  - generated briefings
  - delivery settings

### No Isolation / Access Control
- No authn/authz.
- No tenant-level ACLs.
- Frontend reads shared briefing source; any user would see same content unless you fork runtime instance per user.

Required shift: move from file-based singleton artifacts to tenant-scoped persistent storage + tenant-scoped job execution.

## 3) Data Pipeline at Scale

### Can Rabbit Browser Scan Approach Scale?
Short answer: no, not as a primary multi-user ingestion strategy.

Why it breaks:
- It depends on external scan artifacts in a local directory.
- It has no durable ingestion contract (schema may drift, scrape artifacts already visible: `(pinned)` cleanup logic, typo-heavy verified fallback map).
- It is operationally brittle (browser automation/scraping pipelines break often with UI changes).
- It is hard to parallelize safely for many users without anti-bot risk and high maintenance.

Use it only as:
- dev fallback,
- emergency fallback,
- niche premium “no API” experiment.
Not as core SaaS ingestion.

### X API Scaling Reality (from current code shape)
Current pipeline per user run roughly does:
- Resolve tracked usernames in batches of 100.
- `get_user_tweets` per followed account (currently max 20 per account in `pipeline.run_briefing`).
- Search queries (currently only top 3 queries, max 20 each).

For a user following ~200 accounts, one run is roughly:
- ~2 user lookup requests
- ~200 timeline requests
- ~3 search requests
- Total ~205 requests/run

If you run 4x/day/user:
- ~820 requests/day/user
- 1,000 users => ~820,000 requests/day

Even before endpoint-specific limits, this requires serious rate-limit orchestration, backoff, multi-app sharding strategy, and cost controls.

### Rate Limits / Consumption Risk
Current code is not ready for SaaS-scale limit handling:
- `_check_rate_limit` only throws after a 0-remaining response.
- Pipeline retry/backoff is ad hoc and partial (single 60s sleep on some errors).
- No global throttle, no tenant fair scheduling, no quota manager, no burst control.

Also, X v2 has monthly post consumption caps by plan (not just request windows), and timeline/search endpoints count toward that cap. This is a direct SaaS unit economics constraint.

### Cost Model (Practical)
Do not lock a dollar estimate in code/docs. Use a live model driven by:
- `users * runs_per_day * avg_followed_accounts * avg_posts_returned_per_call`
- plus search volume and enrichment overhead.

Implement hard budget controls:
- Cap followed accounts ingested per tier.
- Adaptive polling frequency by activity.
- Incremental fetch (`since_id`) instead of broad windows where possible.
- Reduce expensive searches for low-value tenants.
- Tiered freshness SLA (hourly/daily).

## 4) X API Situation

### Do You Need Official X API?
Yes, for a defensible SaaS.

Reasons:
- Predictability: structured endpoints, known fields, known auth model.
- Compliance posture is cleaner than pure scraping.
- Better operability for retries, observability, and incident response.

### Risk of Browser/Syndication/Scrape Strategy
High risk as core dependency:
- Terms/compliance risk (account blocks/legal exposure depending on method/use).
- Fragility to DOM/product changes.
- Data incompleteness and inconsistent schema.
- Difficult to provide enterprise-grade uptime promises.

Syndication enrichment is useful but should be optional and non-critical. Current enrichment is capped (`MAX_POSTS_PER_RUN=30`) and serialized with `sleep(1)`; that is a bottleneck at scale.

Recommendation:
- Primary ingestion: official X API.
- Secondary enrichment: best-effort async enrichers with timeouts and circuit breakers.
- Scrape/scan: non-core fallback path only.

## 5) Auth & Billing Recommendations

## Suggested Stack
- App auth/session:
  - Next.js + Auth.js (or Clerk) with email magic link + OAuth (Google).
- Core database:
  - Postgres (Supabase or managed Neon/RDS).
- Background jobs:
  - Trigger.dev / Temporal / BullMQ + Redis (pick one durable queue system).
- Billing:
  - Stripe subscriptions + metered usage.
- Internal API:
  - Next.js route handlers for light control-plane + separate worker service for pipeline execution.

## Data Model Additions (Must-Have)
- `users` (auth identity)
- `organizations`/`workspaces` (if you want team plans)
- `subscriptions` + `plans`
- `sources` (tracked accounts, lists, interests)
- `briefing_jobs` (queued/running/failed/success)
- `briefings` (versioned output snapshots, not single latest file)
- `usage_events` (API calls, posts consumed, enrichment calls, compute time)
- `delivery_channels` (email/webhook/chat settings)

## Billing Model
- Start simple:
  - Base subscription includes:
    - account count cap
    - runs/day cap
    - lookback window cap
  - Metered overages on posts consumed / runs beyond tier.
- Enforce quotas in scheduler before job execution.
- Expose transparent usage dashboard to reduce churn and support load.

## 6) Biggest Technical Risks / Blockers

1. Single-tenant file architecture
- Shared JSON output + shared history make multi-user impossible without full re-architecture.

2. Ingestion dependency risk
- Current scan/scrape path is fragile and non-defensible as core SaaS data source.

3. Rate-limit and quota control immaturity
- No centralized throttling and no plan-aware scheduling.

4. Security and secrets handling
- Hardcoded bearer token in repo script is a serious issue.
- Need immediate secret rotation and secret scanning.

5. No reliability layer
- No job queue, retries with policy, dead-letter queues, idempotency keys, or observability traces.

6. No test safety net
- Fast iteration now, but high regression risk during SaaS conversion.

7. Product correctness risks from heuristics
- Curation thresholds are heavily hardcoded and can hide important low-engagement posts.
- Verified fallback and parse heuristics include noisy artifacts.

## 7) MVP SaaS Roadmap (Concrete, Phased)

## Phase 0 (1 week): Stabilize Current Codebase
- Remove/rotate leaked bearer token immediately.
- Normalize config schema (`interests` vs `recent_interests`) and docs.
- Add structured logging and error taxonomy.
- Add smoke tests for core pipeline + JSON contract.

Exit criteria:
- No hardcoded secrets, reproducible local run, minimal CI checks green.

## Phase 1 (2-3 weeks): Multi-Tenant Data Foundations
- Introduce Postgres schema for users, sources, jobs, briefings.
- Replace `data/latest-briefing.json` singleton with tenant-scoped briefing records.
- Add authenticated dashboard shell (sign-in + tenant selection).
- Keep current frontend UI, but load from tenant-scoped API.

Exit criteria:
- Two separate users can generate and view isolated briefings.

## Phase 2 (2-4 weeks): Job System + Rate Limit Control
- Move pipeline execution into background workers.
- Add job queue with retries, backoff, idempotency.
- Add global X API throttle + per-tenant quotas.
- Add scheduler for run frequency by plan.

Exit criteria:
- Stable queued runs with observable success/failure metrics.

## Phase 3 (2 weeks): Billing + Plan Enforcement
- Stripe subscriptions + webhook handling.
- Plan limits: tracked accounts, run cadence, lookback hours, enrichment depth.
- Usage metering and paywall enforcement in scheduling layer.

Exit criteria:
- End-to-end paid signup -> scheduled brief generation -> limit enforcement.

## Phase 4 (2-3 weeks): Delivery + Reliability Hardening
- Email/webhook delivery with retry and delivery logs.
- Alerting + dashboards (job failure rate, API errors, quota exhaustion).
- Add integration tests for ingestion->curation->delivery path.

Exit criteria:
- Production MVP with on-call visibility and recoverability.

## Phase 5 (Ongoing): Quality + Defensibility
- Reduce heuristic brittleness in curation.
- Incremental fetch optimizations (`since_id`, adaptive search).
- Optional enrichment workers with strict timeout budgets.
- Add privacy/compliance docs, retention controls, and tenant data deletion flows.

---

## Direct Verdict
Current X Brief is a solid single-operator prototype with good curation/UI potential. It is not SaaS-ready due to single-tenant filesystem architecture, ingestion fragility, and missing auth/billing/reliability primitives. The fastest path is not “patching around” current file flows; it is introducing tenant-scoped storage + queued workers + official X API-first ingestion, then layering billing and delivery.
