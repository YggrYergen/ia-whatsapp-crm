# AI CRM Production Stabilization — Implementation Plan

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por docs oficiales actualizados. Leer docs PRIMERO, implementar DESPUÉS. Sin excepciones.

> **⚠️ LEY POST-IMPLEMENTACIÓN:** Toda solución confirmada como funcional DEBE ser documentada EN ESE MOMENTO con: (1) qué se hizo, (2) por qué funciona, (3) links a los docs oficiales que lo respaldan. Esto previene que futuras sesiones de LLM rompan lo que ya funciona por desconocimiento.

## Status: Phase 2A, 2D COMPLETE ✅ | Phase 2B IN PROGRESS (blocked on Next.js upgrade)

---

## Completed Phases
- ✅ Phase 0: Pre-flight
- ✅ Phase 1A: Infrastructure  
- ✅ Phase 1B: Security (frontend done, backend deployed)
- ✅ Phase 1C: Auth PKCE — RESOLVED (see README §0.1)
- ✅ Phase 1D: Backend Deploy — FULLY VERIFIED
- ✅ Phase 2A: Sentry Backend — FULLY VERIFIED (see below)
- ✅ Phase 2D: Discord Alerts — FULLY VERIFIED (see below)

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

## Phase 2A: Sentry Backend (FastAPI) — COMPLETE ✅

### Official Docs Consulted

| Doc | URL | Key Finding |
|:---|:---|:---|
| Sentry FastAPI Integration | [link](https://docs.sentry.io/platforms/python/integrations/fastapi/) | `sentry_sdk.init()` in app startup, auto-captures FastAPI exceptions |
| Sentry Python Config | [link](https://docs.sentry.io/platforms/python/configuration/) | `traces_sample_rate=1.0`, `environment` tag, `send_default_pii=True` |

### What Was Done

| Step | Detail | Verification |
|:---|:---|:---|
| 1. `config.py` | Added `SENTRY_DSN: Optional[str] = None` to Pydantic Settings | Env var correctly read |
| 2. `main.py` | `sentry_sdk.init()` in lifespan with `traces_sample_rate=1.0`, `environment="production"` | SDK initializes at startup |
| 3. Exception handlers | Added explicit `sentry_sdk.capture_exception(exc)` in custom 500/AppBase handlers | Errors not swallowed by custom handlers |
| 4. `use_cases.py` | Enriched pipeline fatal errors with `sentry_sdk.set_context()` (tenant_id, contact_id, pipeline step) | Sentry events have full business context |
| 5. `logger_service.py` | Rewrote to fix Cloud Logging `[object Object]` bug: removed QueueHandler in prod, JSON formatter outputs single-line JSON strings to stdout | Cloud Logging shows clean structured JSON |
| 6. Cloud Run env vars | Set `SENTRY_DSN`, `DISCORD_WEBHOOK_URL`, `ENVIRONMENT=production` | Verified via MCP `get_service` |

### Verification — CONFIRMED ✅

- **`GET /api/debug-exception`** → Sentry captured as issue `PYTHON-5`
- **Sentry dashboard** → Issue visible at `tuasistentevirtual.sentry.io` with full traceback
- **Discord alert** → Embed with traceback sent to #general channel (Captain Hook webhook)
- **Cloud Logging** → Clean JSON structured logs, no more `[object Object]`
- **Active revision:** `ia-backend-prod-00052-7xc` serving 100% traffic

### Known Errors Now Visible in Sentry (diagnostic gains)

- Meta API `401 Unauthorized` — WhatsApp token invalid/expired
- Google Calendar credential loading errors — PEM file issues
- These are expected and will be fixed in Phase 3 (E2E Validation)

---

## Phase 2D: Discord Alerts — COMPLETE ✅

- Webhook URL: "Captain Hook" in StarCompanion's #general channel
- `discord_notifier.py` sends embeds with severity (error/warning/info) + traceback
- Verified: fatal error from `/api/debug-exception` → Discord embed received

---

## Phase 2B: Sentry Frontend Client-Side — IN PROGRESS 🔄

### BLOCKER: Next.js 14.1.4 incompatible with Sentry SDK v10

> **⚠️ CRITICAL — DO NOT SKIP THIS SECTION. READ BEFORE TOUCHING FRONTEND SENTRY.**

#### Problem Discovered (via docs research)

| Issue | Detail |
|:---|:---|
| **`sentry.client.config.ts` is DEPRECATED** | Sentry SDK v10 expects `instrumentation-client.ts` — a Next.js 15+ file convention. [Sentry manual setup docs](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) |
| **`disableClientInstrumentation: true`** | This flag in `next.config.js` **KILLS all client-side error capture**. It was set to prevent Edge runtime crashes on Next.js 14. |
| **`instrumentation-client.ts` requires Next.js 15+** | This is a [Next.js file convention](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client) not available in 14.x |
| **Next.js 14.1.4 is EOL** | 2 major versions behind, known CVEs, no longer receiving security patches |

#### Decision: Upgrade Next.js 14.1.4 → 15.5.15 (APPROVED)

> **⚠️ DO NOT DOWNGRADE Next.js back to 14.x — it will BREAK Sentry frontend integration.**
> The `instrumentation-client.ts` file ONLY works on Next.js 15+.
> The old `sentry.client.config.ts` file is DEPRECATED and should NOT be re-created.

**Why 15.5.15 (not 16.x):**
- 15.x has 6+ months of production hardening
- 16.x is brand new (weeks old), higher regression risk
- Fewer breaking changes from 14→15 than 14→16
- Full Sentry SDK v10 + `instrumentation-client.ts` support

**Docs consulted:**
- [Next.js 15 upgrade guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)
- [Sentry Next.js manual setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) — specifies `instrumentation-client.ts`
- [instrumentation-client.ts convention](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client)

**Breaking changes to handle:**
1. React 18 → React 19 (required by Next.js 15)
2. `sentry.client.config.ts` → `instrumentation-client.ts`
3. Remove `disableClientInstrumentation: true` from `next.config.js`
4. Add `global-error.tsx` for React render error capture (per Sentry docs)
5. `eslint-config-next` must match Next.js version
6. `@types/react` and `@types/react-dom` bump to v19

**Status:** Approved, execution pending.

---

## Phase 2C: Sentry Frontend Server-Side — DEFERRED

- N/A for static export (Cloudflare Pages has no Node.js server runtime)
- `sentry.server.config.ts` and `instrumentation.ts` are not relevant for our deployment
- If we migrate to OpenNext in the future, this becomes relevant

---

## Remaining Phases

### Phase 3: E2E Validation — EXHAUSTIVE (after Sentry confirmed on BOTH front and back)
- Test every LLM tool individually via `/api/simulate`
- Test complete WhatsApp → LLM → Tool → Response → Realtime → Frontend flow
- Test frontend buttons: Send Test Chat, Agenda book, Config save, etc.
- All errors must appear in Sentry with full traceback

### Phase 4: Environment Separation
### Phase 5: Go-Live
