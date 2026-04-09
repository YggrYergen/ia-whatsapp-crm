# AI CRM — Production Stabilization Tasks

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por la doc oficial más actualizada. Sin excepciones.

> **⚠️ LEY POST-IMPLEMENTACIÓN:** Toda solución confirmada como funcional DEBE documentarse EN ESE MOMENTO con: qué se hizo, por qué funciona, links a docs oficiales. Esto previene que futuras sesiones de LLM rompan lo que ya funciona por desconocimiento.

---

## Phase 0: Pre-flight ✅
- [x] Clean working tree, inspect diffs, create restoration tag

## Phase 1A: Infrastructure ✅
- [x] Configure env vars, backend URL, SQL migrations

## Phase 1B: Security ✅
- [x] Auth guard, real logout, CORS fix, traceback removal
- [x] Backend deploy with security fixes (done via Phase 1D)

## Phase 1C: Auth PKCE ✅
- [x] Fix: remove manual `exchangeCodeForSession`, use `onAuthStateChange`
- [x] Full login cycle validated, documented in README §0.1

## Phase 1D: Backend Deploy (Cloud Build) ✅ COMPLETE

### Root Cause 1: IAM Permissions ✅
SA: `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`
- [x] `roles/cloudbuild.builds.builder` — granted
- [x] `roles/run.admin` — granted
- [x] `roles/iam.serviceAccountUser` — granted

### Root Cause 2: Missing Deploy Step ✅
Trigger: `7458b935-6cd5-48e2-b12b-b7115947e39d`
- [x] Added 3-step pipeline: Build → Push → Deploy
- [x] Deploy step uses `gcr.io/google.com/cloudsdktool/cloud-sdk` with `gcloud run services update`
- [x] Per docs: https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run

### Root Cause 3: Secrets Not Configured ✅
- [x] Created `WHATSAPP_VERIFY_TOKEN` in Secret Manager
- [x] Granted `roles/secretmanager.secretAccessor` to SA for all 6 secrets
- [x] Configured service with `--update-secrets` (all 6 secrets via `secretKeyRef`)
- [x] Per docs: https://cloud.google.com/run/docs/configuring/services/secrets

### Dockerfile Restructure ✅
- [x] Created `Backend/Dockerfile` (self-contained, multi-stage)
- [x] Build context = `Backend/`

### Verification ✅
- [x] Build `c1c97b1b` → SUCCESS (3 steps)
- [x] Revision `ia-backend-prod-00046-hfx` → Active, Ready=True
- [x] Traffic: 100% on new revision
- [x] API: `GET /api/debug-ping` → 200 OK
- [x] Secrets: 6 secrets via `secretKeyRef` confirmed in revision spec
- [x] README updated with complete deployment procedure

---

## Phase 2: Sentry Observability — EXHAUSTIVA

### 2A: Sentry Backend (FastAPI) ✅ COMPLETE
Docs consulted:
- [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [Sentry Python Config](https://docs.sentry.io/platforms/python/configuration/)

- [x] Read official docs
- [x] Added `SENTRY_DSN` to `config.py` (Pydantic Settings)
- [x] `sentry_sdk.init()` in `main.py` lifespan with `traces_sample_rate=1.0`, `environment="production"`
- [x] Added explicit `sentry_sdk.capture_exception()` in custom exception handlers (prevents silent swallowing)
- [x] Enriched pipeline errors in `use_cases.py` with `sentry_sdk.set_context()` (tenant_id, contact_id, pipeline step)
- [x] Fixed Cloud Logging `[object Object]` bug in `logger_service.py` (removed QueueHandler in prod, JSON to stdout)
- [x] Set `SENTRY_DSN`, `DISCORD_WEBHOOK_URL`, `ENVIRONMENT=production` as env vars in Cloud Run
- [x] **TESTED:** `GET /api/debug-exception` → Sentry issue `PYTHON-5` captured with full traceback
- [x] **TESTED:** Discord alert received in #general with embed + traceback
- [x] **TESTED:** Cloud Logging shows clean structured JSON
- [x] Active revision: `ia-backend-prod-00052-7xc` serving 100% traffic

### 2B: Sentry Frontend Client-Side — BLOCKED (adapter limitation) → resolved by Phase 2E
Docs consulted:
- [Sentry Next.js Manual Setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/)
- [Next.js instrumentation-client.ts](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client)
- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)

> **⚠️ DO NOT DOWNGRADE Next.js below 15.x — it will BREAK the Sentry frontend integration.**
> The `instrumentation-client.ts` file ONLY works on Next.js 15+.
> The old `sentry.client.config.ts` is DEPRECATED by Sentry and should NOT be re-created.
> The `disableClientInstrumentation: true` flag was KILLING all client-side error capture.
> **⚠️ DO NOT DOWNGRADE `lucide-react` below ^1.7.0** — React 19 peer dep conflict breaks build.

- [x] Read Sentry Next.js docs — confirmed `instrumentation-client.ts` is the new standard
- [x] Read Next.js 15 upgrade guide — confirmed breaking changes (React 19, etc.)
- [x] Decision: Upgrade Next.js 14.1.4 → 15.5.15 (latest stable 15.x) — APPROVED
- [x] Updated `package.json`: next@15.5.15, react@^19, react-dom@^19, @types/react@^19, eslint-config-next@15.5.15
- [x] Created `instrumentation-client.ts` per Sentry docs (replaces deprecated `sentry.client.config.ts`)
- [x] Created `app/global-error.tsx` per Sentry docs (captures React render errors)
- [x] Updated `next.config.js` — removed `disableClientInstrumentation`, cleaned up Sentry options
- [x] Deleted deprecated `sentry.client.config.ts`
- [x] Deleted N/A `sentry.server.config.ts` (not needed for static export)
- [x] `npm install` — installed successfully (react@19.2.5, next@15.5.15 confirmed)
- [x] `npm run build` — **SUCCESS** ✅ (14 pages compiled, no errors)
- [x] Added `onRouterTransitionStart` export per Sentry build requirement
- [x] Updated README §0.2 with full upgrade documentation + DO NOT DOWNGRADE warnings
- [x] Hardcoded Sentry DSN in `instrumentation-client.ts` (wrangler `[vars]` are runtime not build-time)
- [x] Upgraded `lucide-react` ^0.364.0 → ^1.7.0 (React 19 peer dep fix)
- [x] Deploy to Cloudflare Pages (commit + push to main) ✅
- [x] **TESTED:** Sentry SDK IS bundled in client JS (verified in browser DevTools)
- [x] **TESTED:** Sentry is **NOT** capturing client-side errors ❌
- [x] **DIAGNOSED:** `@cloudflare/next-on-pages` adapter does NOT process `instrumentation-client.ts` — it strips/ignores the Next.js 15 instrumentation hooks
- [ ] **RESOLUTION:** Migrate to OpenNext (Phase 2E) to unblock client-side Sentry

### 2C: Sentry Frontend Server-Side — DEFERRED → BECOMES AVAILABLE WITH OPENNEXT
- [x] Evaluated: Previously N/A for Cloudflare Pages static export (no Node.js server runtime)
- [ ] Re-evaluate AFTER Phase 2E completes (OpenNext enables server-side Sentry via `instrumentation.ts`)

### 2D: Alertas ✅ COMPLETE
- [x] Discord webhook configured ("Captain Hook" in StarCompanion's #general)
- [x] `discord_notifier.py` sends embeds with severity + traceback
- [x] **TESTED:** Fatal error from `/api/debug-exception` → Discord embed received

### 2E: OpenNext Migration (Cloudflare Pages → Workers) ← CURRENT 🔄
Docs consulted:
- [OpenNext Get Started (existing apps)](https://opennext.js.org/cloudflare/get-started#existing-nextjs-apps)
- [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars)
- [OpenNext Dev & Deploy](https://opennext.js.org/cloudflare/howtos/dev-deploy)

> **Rollback:** Git tag `pre-opennext-migration` at commit `f1494c9`. Persistent KI in `knowledge/opennext-migration-rollback/`.

- [x] Read all 3 official OpenNext docs (get-started, env-vars, dev-deploy)
- [x] Verified Worker size fits free tier (~1.23 MB gzipped < 3 MB limit)
- [x] Created rollback tag `pre-opennext-migration` and pushed to remote
- [x] Created persistent rollback KI artifact
- [ ] Step 1: Install `@opennextjs/cloudflare@latest`
- [ ] Step 2: Install `wrangler@latest` as devDep
- [ ] Step 3: Replace `wrangler.toml` (Pages → Workers format)
- [ ] Step 4: Create `open-next.config.ts`
- [ ] Step 5: Create `.dev.vars`
- [ ] Step 6: Update `package.json` scripts
- [ ] Step 7: Create `public/_headers` for static asset caching
- [ ] Step 9: Remove `export const runtime = "edge"` (none found ✅)
- [ ] Step 10: Add `.open-next` to `.gitignore`
- [ ] Step 11: Remove `@cloudflare/next-on-pages` references
- [ ] Step 12: Update `next.config.js` — add `initOpenNextCloudflareForDev()`
- [ ] Step 13: Commit, push, deploy to Cloudflare Workers
- [ ] Set up Workers Builds in Cloudflare dashboard
- [ ] Add env vars in Workers dashboard
- [ ] **TEST:** Trigger frontend error → verify it appears in Sentry dashboard
- [ ] **TEST:** Verify no regressions in existing UI (login, dashboard, chat, agenda)
- [ ] Update README with OpenNext documentation

---

## Phase 3: E2E Validation — EXHAUSTIVA (DESPUÉS de Sentry confirmado en front y back)

### 3A: Componentes CRM
- [ ] Dashboard loads
- [ ] Chat loads and shows contacts
- [ ] Agenda loads and shows calendar events
- [ ] Contactos/Pacientes loads
- [ ] Configuración loads and saves
- [ ] Send Test Chat button works
- [ ] All buttons that are supposed to work actually work

### 3B: Herramientas LLM (TODAS las 7 tools)
- [ ] Inventariar todas las tools
- [ ] CheckAvailabilityTool — test via `/api/simulate`
- [ ] CheckMyAppointmentsTool — test via `/api/simulate`
- [ ] BookAppointmentTool — test via `/api/simulate`
- [ ] UpdateAppointmentTool — test via `/api/simulate`
- [ ] DeleteAppointmentTool — test via `/api/simulate`
- [ ] EscalateHumanTool — test via `/api/simulate`
- [ ] UpdatePatientScoringTool — test via `/api/simulate`
- [ ] Each tool failure must appear in Sentry with full traceback

### 3C: Flujo E2E Completo
- [ ] WhatsApp webhook → LLM → tool → response → Realtime → frontend
- [ ] Note: Meta API token is expired/invalid (401), will need fixing before this works

---

## Phase 4: Environment Separation
- [ ] `desarrollo` branch auto-deploy

## Phase 5: Go-Live
- [ ] Meta webhook token refresh
- [ ] E2E real with WhatsApp
- [ ] Sentry production validation
- [ ] Launch
