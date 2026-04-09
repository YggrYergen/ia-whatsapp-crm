# Phase 1D Walkthrough: Backend Deploy Pipeline Fix

## Problem
Cloud Build trigger was failing to deploy the backend to Cloud Run after every push to `main`. Multiple consecutive FAILURE builds with no new revisions deployed.

## Root Causes Found (3 separate issues, each backed by official docs)

### 1. IAM Permissions Missing
**Error:** `Permission 'iam.serviceaccounts.actAs' denied on service account ia-calendar-bot@...`
**Doc:** [Cloud Build IAM](https://cloud.google.com/build/docs/securing-builds/configure-access-control)
**Fix:** Granted 3 roles to `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`:
- `roles/cloudbuild.builds.builder`
- `roles/run.admin`
- `roles/iam.serviceAccountUser` ← root cause of the specific error

### 2. Trigger Had No Deploy Step
**Error:** Build succeeded (`docker build` + image push) but no new revision was created on Cloud Run.
**Doc:** [Cloud Build Deploy to Cloud Run](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run)
**Fix:** Added 3-step pipeline to trigger:
```yaml
steps:
- id: Build    # docker build
- id: Push     # docker push
- id: Deploy   # gcloud run services update --image=...
```

### 3. Secrets Not in Secret Manager
**Error:** `pydantic_core.ValidationError: 5 validation errors for Settings` — WHATSAPP_VERIFY_TOKEN, OPENAI_API_KEY, etc. missing at runtime.
**Doc:** [Configure secrets for Cloud Run](https://cloud.google.com/run/docs/configuring/services/secrets)
**Root cause:** Previous deploys via `gcloud run deploy --source .` (buildpacks) had secrets baked into the image at build time. Custom Dockerfile doesn't have this — secrets must be explicitly configured via Secret Manager.
**Fix:**
1. Created `WHATSAPP_VERIFY_TOKEN` secret in Secret Manager
2. Granted `roles/secretmanager.secretAccessor` to SA for all 6 secrets
3. Configured service with `--update-secrets` flag — secrets now injected at startup via `secretKeyRef`

## Verification Results

| Check | Result |
|:---|:---|
| Build `c1c97b1b` | ✅ SUCCESS (3 steps) |
| Revision `00046-hfx` | ✅ Active, Ready=True |
| Traffic | ✅ 100% on latest |
| API `/api/debug-ping` | ✅ 200 OK |
| Secrets in revision spec | ✅ 6 `secretKeyRef` entries confirmed |
| Auto-trigger on push | ✅ Push to main fires Build→Push→Deploy |

## Documentation Updated
- `README.md` — Full trigger YAML, Secret Manager table, IAM commands, warnings
- `implementation_plan.md` — Phase 1D marked COMPLETE
- `task.md` — All 1D subtasks checked off

## Key Lesson
The entire issue chain was solvable by reading the official docs. Three separate doc pages each contained the exact fix for their respective issue. The "Docs-First" rule prevented further wheel-reinvention.

---

# Phase 2A Walkthrough: Backend Sentry + Discord Observability

## Problem
WhatsApp messages sent to the test chat produced NO response from the bot AND no error logs in Sentry or Discord. The system was failing silently — zero observability.

## Official Docs Consulted

| Doc | URL | Key Takeaway |
|:---|:---|:---|
| Sentry FastAPI | [link](https://docs.sentry.io/platforms/python/integrations/fastapi/) | `sentry_sdk.init()` auto-captures FastAPI exceptions; custom exception handlers need explicit `capture_exception()` |
| Sentry Python Config | [link](https://docs.sentry.io/platforms/python/configuration/) | `traces_sample_rate=1.0` for full capture; `environment` tag for filtering |

## What Was Done

### 1. `config.py` — Added `SENTRY_DSN` to Pydantic Settings
Previously the DSN was hardcoded inline. Now it's a proper `Optional[str]` field read from environment variables, following the same pattern as all other config.

### 2. `main.py` — Sentry SDK initialization
- `sentry_sdk.init()` called in FastAPI lifespan with `traces_sample_rate=1.0` and `environment="production"`
- **Critical:** Added explicit `sentry_sdk.capture_exception(exc)` in BOTH custom exception handlers (`AppBaseException` handler and generic `Exception` handler). Without this, FastAPI's custom handlers swallow exceptions before Sentry sees them.

### 3. `use_cases.py` — Pipeline error enrichment
- Added `sentry_sdk.set_context("pipeline", {...})` before `capture_exception()` in the fatal error handler of `ProcessMessageUseCase.execute()`
- Context includes: `tenant_id`, `contact_id`, `pipeline_step`, `error_type`
- This means every pipeline failure in Sentry now has full business context attached

### 4. `logger_service.py` — Fixed Cloud Logging `[object Object]` bug
- Root cause: `QueueHandler` + `QueueListener` was wrapping JSON output in a way that Cloud Logging couldn't parse
- Fix: In production (`ENVIRONMENT=production`), removed `QueueHandler` entirely. JSON formatter outputs single-line JSON strings directly to `stdout`
- Cloud Logging now shows properly parsed structured JSON logs

### 5. Cloud Run environment variables
- Set `SENTRY_DSN`, `DISCORD_WEBHOOK_URL`, `ENVIRONMENT=production` as env vars on the service
- Verified via Cloud Run MCP `get_service`

## Verification Results — ALL CONFIRMED ✅

| Check | Result | Evidence |
|:---|:---|:---|
| `GET /api/debug-exception` | ✅ Sentry captures | Issue `PYTHON-5` visible in Sentry dashboard |
| Discord alert | ✅ Embed received | #general channel in StarCompanion's server |
| Cloud Logging | ✅ Clean structured JSON | No more `[object Object]` |
| Active revision | ✅ `ia-backend-prod-00052-7xc` | 100% traffic, all env vars confirmed |

## Diagnostic Gains (errors now visible that were previously silent)
- Meta API `401 Unauthorized` — WhatsApp token is expired/invalid
- Google Calendar credential loading errors — PEM file issues
- These explain why the "hi" message test failed: the pipeline works but the Meta API returns 401 when trying to send a response

## Key Lesson
Custom exception handlers in FastAPI **swallow exceptions silently** unless you explicitly call `sentry_sdk.capture_exception()` inside them. The Sentry SDK's auto-capture only works for exceptions that propagate to the ASGI layer unhandled.

---

# Phase 2B: Next.js 14 → 15 Upgrade Decision

## Problem
Frontend Sentry integration is broken because:
1. `sentry.client.config.ts` is deprecated by Sentry SDK v10
2. `disableClientInstrumentation: true` in `next.config.js` kills ALL client-side error capture
3. The replacement file `instrumentation-client.ts` is a Next.js 15+ file convention

## Official Docs Consulted

| Doc | URL | Key Takeaway |
|:---|:---|:---|
| Sentry Next.js Manual Setup | [link](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) | Client init must be in `instrumentation-client.ts`, NOT `sentry.client.config.ts` |
| instrumentation-client.ts API | [link](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client) | This file convention only exists in Next.js 15+ |
| Next.js 15 Upgrade Guide | [link](https://nextjs.org/docs/app/building-your-application/upgrading/version-15) | Requires React 19, async request APIs |

## Decision

> **⚠️ CRITICAL — DO NOT DOWNGRADE Next.js BELOW 15.x**
> Doing so will BREAK the Sentry frontend integration because `instrumentation-client.ts` does not exist in Next.js 14.
> The old `sentry.client.config.ts` file is DEPRECATED by Sentry and should NEVER be re-created.

**Target version:** Next.js 15.5.15 (latest stable 15.x, not bleeding-edge 16.x)

**Status:** Approved by user, execution pending.
