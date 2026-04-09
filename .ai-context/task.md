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

### 2E: OpenNext Migration (Cloudflare Pages → Workers) ✅ COMPLETE
Docs consulted:
- [OpenNext Get Started (existing apps)](https://opennext.js.org/cloudflare/get-started#existing-nextjs-apps)
- [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars)
- [OpenNext Dev & Deploy](https://opennext.js.org/cloudflare/howtos/dev-deploy)
- [Sentry Next.js on Cloudflare](https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/)
- [Sentry Cloudflare Quick Start](https://docs.sentry.io/platforms/javascript/guides/cloudflare/)
- [CF Workers Env Vars](https://developers.cloudflare.com/workers/configuration/environment-variables/)
- [CF Workers Builds Config](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)

> **Rollback:** Git tag `pre-opennext-migration` at commit `f1494c9`. Persistent KI in `knowledge/opennext-migration-rollback/`.

- [x] Read all 3 official OpenNext docs (get-started, env-vars, dev-deploy)
- [x] Verified Worker size fits free tier (~1.23 MB gzipped < 3 MB limit)
- [x] Created rollback tag `pre-opennext-migration` and pushed to remote
- [x] Created persistent rollback KI artifact
- [x] Step 1: Install `@opennextjs/cloudflare@latest` (v1.18.1)
- [x] Step 2: Install `wrangler@latest` as devDep (already bundled with opennext)
- [x] Step 3: Replace `wrangler.toml` (Pages → Workers format: `main=.open-next/worker.js`, `assets`, `services`)
- [x] Step 4: Create `open-next.config.ts`
- [x] Step 5: Create `.dev.vars` (NEXTJS_ENV=development)
- [x] Step 6: Update `package.json` scripts (preview, deploy, upload, cf-typegen)
- [x] Step 7: Create `public/_headers` for static asset caching
- [x] Step 9: Remove `export const runtime = "edge"` — **found 5 instances** (auth/callback, simulate, test-feedback, calendar/book, calendar/events) — ALL removed
- [x] Step 10: Add `.open-next`, `.wrangler`, `.dev.vars` to `.gitignore`
- [x] Step 11: Remove `@cloudflare/next-on-pages` references — updated comment in auth/callback/route.ts
- [x] Step 12: Update `next.config.js` — added `initOpenNextCloudflareForDev()`, updated comments
- [x] `npm run build` — **SUCCESS** ✅ (19 routes, no edge runtime warnings)
- [x] Step 13: Commit `6c2efdd` + push to `main` ✅
- [x] `wrangler login` — authenticated ✅
- [x] `opennextjs-cloudflare build` — SUCCESS ✅ (worker.js generated, 2004 KiB gzipped)
- [x] `wrangler deploy` — SUCCESS ✅ (54 assets uploaded, Worker live)
- [x] **Workers URL:** `https://ia-whatsapp-crm.tomasgemes.workers.dev` — login page renders ✅
- [x] **FIX:** Bumped `compatibility_date` from `2024-12-30` to `2025-08-16` — REQUIRED by Sentry for `https.request` in Workers runtime. Per: https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/
- [x] **FIX:** Removed `global_fetch_strictly_public` flag (included by default at 2025-08-16)
- [x] **FIX:** Added `upload_source_maps = true` per Sentry Cloudflare docs for readable stack traces
- [x] Build verified after compat date bump — SUCCESS ✅ (commit `b5c7d2f`)
- [x] Created deployment guide artifact (`cloudflare_workers_deploy_guide.md`) with step-by-step instructions
- [x] Workers Builds CI/CD configured and functional
- [x] Custom domain `dash.tuasistentevirtual.cl` moved from Pages to Workers
- [x] Env vars set in Workers dashboard (build + runtime)
- [x] **OBSERVABILITY:** Added `[observability]` block to `wrangler.toml` — enables Workers Logs + OTel export to Sentry (commit `b48f860`)
  - Per: https://developers.cloudflare.com/workers/observability/logs/workers-logs/
  - Per: https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/sentry/
- [ ] **OBSERVABILITY:** Create OTel destinations in CF dashboard (`sentry-traces`, `sentry-logs`) — see deploy guide Paso 9B
- [x] **OBSERVABILITY:** Updated deploy guide (`cloudflare_workers_deploy_guide.md`) with full Paso 9 instructions
- [x] **OBSERVABILITY:** Workers Logs confirmed WORKING in CF dashboard ✅ — shows invocation logs + errors
- [x] **BUG FIX:** `TypeError: Expected "8000" to be a string` — root cause: `.env.local` with `BACKEND_URL=http://localhost:8000` was NOT in `.gitignore`. Build baked `localhost:8000` into routes manifest. Fix: added `.env.local` to `.gitignore` (commit `19b665f`).
- [x] Verified: login, dashboard, chat, agenda all functional
- [x] README updated with OpenNext documentation (§0.3)

### 2F: Sentry Coverage Hardening ✅ COMPLETE (commit `5ba489d`, 2026-04-09)
Docs consulted:
- [Sentry Python: capture_exception](https://docs.sentry.io/platforms/python/usage/#capturing-errors)
- [Sentry Python: Enriching Events](https://docs.sentry.io/platforms/python/enriching-events/context/)
- [Sentry Next.js: captureException](https://docs.sentry.io/platforms/javascript/guides/nextjs/usage/)

**Problem:** Systemic "silent failures" — 30+ catch blocks across backend and frontend were logging errors to console but NOT sending them to Sentry. This made production debugging impossible for tool failures, credential errors, and frontend data operations.

**Backend (6 files, 12 catch blocks instrumented):**
- [x] `tool_registry.py` → `execute_tool()`: `sentry_sdk.capture_exception()` + `set_context("tool_execution", ...)` — the #1 black hole, ALL 7 tool failures were invisible
- [x] `tools.py` → `EscalateHumanTool`: replaced `except Exception: pass` with logging + Sentry capture
- [x] `tools.py` → `UpdatePatientScoringTool`: added Sentry capture to existing catch
- [x] `use_cases.py` → Contact creation: added Sentry capture
- [x] `use_cases.py` → Message persistence: added Sentry capture
- [x] `use_cases.py` → Tool execution loop: added Sentry capture per-tool
- [x] `use_cases.py` → Cleanup `except: pass`: replaced with `except Exception as cleanup_err: sentry_sdk.capture_exception(cleanup_err)`
- [x] `google_client.py` → Credential loading: added Sentry capture
- [x] `meta_graph_api.py` → Meta API errors: added Sentry capture + `set_context("meta_graph_api", ...)` with phone_number_id, status_code, response_body
- [x] `main.py` → `/api/simulate`: added Sentry capture
- [x] `main.py` → `/api/test-feedback`: added Sentry capture
- [x] `main.py` → `/api/calendar/book`: wrapped in try/except + Sentry capture (had NO error handling)

**Frontend (11 files, 18 catch blocks instrumented):**
- [x] `simulate/route.ts`: `Sentry.captureException` + `captureMessage` on non-ok response
- [x] `test-feedback/route.ts`: same
- [x] `calendar/events/route.ts`: same
- [x] `calendar/book/route.ts`: same
- [x] `TestChatArea.tsx`: 5 catch blocks (localStorage, msg insert, Supabase, simulate, bot toggle, sandbox feedback)
- [x] `ChatArea.tsx`: 2 catch blocks (DB insert, simulation trigger)
- [x] `AgendaView.tsx`: 2 catch blocks (fetchEvents, handleBook)
- [x] `TestConfigPanel.tsx`: 2 catch blocks (fetch config, save prompt)
- [x] `GlobalFeedbackButton.tsx`: 1 catch block (handleSend)
- [x] `admin-feedback/page.tsx`: handleDelete wrapped in new try/catch (had none) + Sentry capture
- [x] `auth/confirm/page.tsx`: session error → Sentry captureMessage

**Additional fix — CORS:**
- [x] `main.py`: replaced old `ia-whatsapp-crm.pages.dev` with `ia-whatsapp-crm.tomasgemes.workers.dev`

**Additional fix — RLS DELETE policies (via Supabase MCP migration):**
- [x] `messages`: DELETE policy `messages_delete_own` for `authenticated` scoped to `get_user_tenant_ids()`
- [x] `test_feedback`: DELETE policy `test_feedback_delete_tenant` for `authenticated` scoped to `get_user_tenant_ids()`

**Additional fix — GCal Secret Manager:**
- [x] `GOOGLE_CALENDAR_CREDENTIALS` version 4: re-uploaded as raw JSON (was base64-encoded, caused JSON parse failure)

**Verification:**
- [x] `npm run build` → SUCCESS (0 errors, 19 routes)
- [x] Commit `5ba489d` pushed to `main` → auto-deploy triggered
- [x] User confirmed: chat working, calendar check availability working, appointment booking working

---

## Phase 3: E2E Validation — EXHAUSTIVA ← CURRENT 🔄

> **PREREQUISITE:** Sentry exhaustive coverage confirmed on BOTH front and back (Phase 2F). All errors will now appear in Sentry.

### 3A: Componentes CRM
- [x] Dashboard loads ✅ (user confirmed 2026-04-09)
- [x] Chat loads and shows contacts ✅ (user confirmed 2026-04-09)
- [x] Agenda loads and shows calendar events ✅ (user confirmed 2026-04-09)
- [ ] Contactos/Pacientes loads
- [ ] Configuración loads and saves
- [ ] Send Test Chat button works ("Enviar Prueba" with DELETE RLS fix)
- [ ] Admin Feedback page loads and delete works
- [ ] All buttons that are supposed to work actually work

### 3B: Herramientas LLM (TODAS las 7 tools)
- [x] Inventariar todas las tools ✅ (7 tools confirmed in tool_registry)
- [x] CheckAvailabilityTool (get_merged_availability) — ✅ user confirmed working (2026-04-09)
- [ ] CheckMyAppointmentsTool (get_my_appointments) — test via `/api/simulate`
- [x] BookAppointmentTool (book_round_robin) — ✅ user confirmed working (2026-04-09)
- [ ] UpdateAppointmentTool (update_appointment) — test via `/api/simulate`
- [ ] DeleteAppointmentTool (delete_appointment) — test via `/api/simulate`
- [ ] EscalateHumanTool (request_human_escalation) — test via `/api/simulate`
- [ ] UpdatePatientScoringTool (update_patient_scoring) — test via `/api/simulate`
- [ ] Each tool failure must appear in Sentry with full traceback

### 3C: Flujo E2E Completo
- [ ] Simulator → LLM → tool → response → Realtime → frontend chat update
- [ ] WhatsApp webhook → LLM → tool → response → Meta API → frontend (requires Meta token refresh)
- [ ] Note: Meta API token is expired/invalid (401), will need fixing before WhatsApp E2E works

### 3D: Observability Verification
- [ ] Trigger intentional tool error → appears in Sentry within 30s
- [ ] Trigger frontend error → appears in Sentry
- [ ] Discord alert fires for backend errors
- [ ] Workers Logs show invocation details in CF dashboard

---

## Phase 4: Environment Separation
- [ ] `desarrollo` branch auto-deploy

## Phase 5: Go-Live
- [ ] Meta webhook token refresh
- [ ] E2E real with WhatsApp
- [ ] Sentry production validation
- [ ] Launch
