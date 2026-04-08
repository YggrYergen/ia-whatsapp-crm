# AI CRM Production Stabilization — Implementation Plan

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por docs oficiales actualizados. Leer docs PRIMERO, implementar DESPUÉS. Sin excepciones.

## Status: Phase 1D COMPLETE ✅ | Phase 2 NEXT

---

## Completed Phases
- ✅ Phase 0: Pre-flight
- ✅ Phase 1A: Infrastructure  
- ✅ Phase 1B: Security (frontend done, backend deployed)
- ✅ Phase 1C: Auth PKCE — RESOLVED (see README §0.1)
- ✅ Phase 1D: Backend Deploy — FULLY VERIFIED

---

## Phase 1D: Backend Deploy — COMPLETE ✅

### Official Docs Consulted

| Doc | URL | Key Finding |
|:---|:---|:---|
| FastAPI Quickstart | [link](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service) | Flat directory, Cloud Build needs builder role |
| Continuous Deployment | [link](https://cloud.google.com/run/docs/continuous-deployment) | SA needs `roles/cloudbuild.builds.builder` + `roles/run.admin` + `roles/iam.serviceAccountUser` |
| Cloud Build Deploy | [link](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) | 3-step pipeline: Build → Push → Deploy using `gcr.io/google.com/cloudsdktool/cloud-sdk` |
| Configure Secrets | [link](https://cloud.google.com/run/docs/configuring/services/secrets) | Use `--update-secrets=ENV=SECRET:latest`, SA needs `roles/secretmanager.secretAccessor` per secret |
| Cloud Build IAM | [link](https://cloud.google.com/build/docs/securing-builds/configure-access-control) | Service account permissions for builds |

### Root Causes Found (3 separate issues)

1. **`iam.serviceaccounts.actAs` error** → SA missing `roles/iam.serviceAccountUser`
2. **Build-only trigger** → Original trigger only had a `docker build` step, no Push or Deploy step
3. **Missing secrets** → Env vars were baked into buildpacks images; custom Dockerfile needed Secret Manager references via `--update-secrets`

### What Was Done

| Step | Fix | Verification |
|:---|:---|:---|
| 1. Restructure Dockerfile | `Backend/Dockerfile` self-contained | Build step succeeds |
| 2. IAM Roles | 3 roles granted to SA | Build no longer fails on permissions |
| 3. Trigger Updated | 3-step pipeline (Build→Push→Deploy) | Build `c1c97b1b` → SUCCESS |
| 4. Secrets via Secret Manager | `--update-secrets` with all 6 secrets | Revision `00046-hfx` starts, `secretKeyRef` confirmed |
| 5. Traffic routed | `--to-latest` | 100% traffic on new revision, API returns 200 |

### Final Verified State

- **Build:** `c1c97b1b` → SUCCESS (3 steps)
- **Revision:** `ia-backend-prod-00046-hfx` → Active, 100% traffic
- **API:** `GET /api/debug-ping` → 200 OK
- **Secrets:** 6 secrets via `secretKeyRef` to Secret Manager
- **Trigger:** Auto-deploys on push to `main`

---

## Remaining Phases

### Phase 2: Sentry Observability — EXHAUSTIVE (before E2E)
Docs: [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/), [Sentry Next.js](https://docs.sentry.io/platforms/javascript/guides/nextjs/)

- 2A: Backend (FastAPI) — every exception, timeout, API failure, tool failure → Sentry
- 2B: Frontend client — Error Boundaries, fetch failures, WebSocket errors, button failures
- 2C: Frontend server — Cloudflare Workers / OpenNext compatibility
- 2D: Alerts — Discord webhook, email fallback

### Phase 3: E2E Validation — EXHAUSTIVE (after Sentry confirmed)
- Test every LLM tool individually
- Test complete WhatsApp → LLM → Tool → Response → Realtime → Frontend flow
- All errors must appear in Sentry with full traceback

### Phase 4: Environment Separation
### Phase 5: Go-Live
