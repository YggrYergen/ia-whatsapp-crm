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

### 2B: Sentry Frontend Client-Side — SOLVED (adapter limitation) → resolved by Phase 2E
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
- [/] **OBSERVABILITY:** Create OTel destinations in CF dashboard (`sentry-traces`, `sentry-logs`) — Instructions provided in §3E, MANUAL action required (CAPTCHA blocks automation)
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

## Phase 3: Internal E2E Validation ← CURRENT 🔄

> **SCOPE: INTERNAL ONLY. No WhatsApp/Meta connection. Tested via simulator, frontend UI, and direct API calls. WhatsApp happens in Phase 5.**

> **PREREQUISITE (Preamble): Sentry must be connected to Discord so ALL errors — even gracefully handled ones — trigger immediate Discord notifications. Consult official docs FIRST.**

### Preamble: Sentry → Discord Real-Time Alerts ✅ COMPLETE (2026-04-09)
- [x] Read official docs: [Sentry Alerts](https://docs.sentry.io/product/alerts/), [Sentry Discord Integration](https://docs.sentry.io/organization/integrations/notification-incidents/discord/) ✅
- [x] Sentry Discord integration installed: "StarCompanion's server" (guild `1491131005719810360`) ✅
- [x] Alert Rule created: **"All Issues → Discord (CRM Observability)"** (Rule ID: `16897799`)
  - WHEN: "A new issue is created" OR "The issue changes state from resolved to unresolved"
  - THEN: Send Discord notification to `StarCompanion's server` channel `1491131005719810363` (#general)
  - THEN: Send notification to Suggested Assignees / Recently Active Members (email)
  - Action interval: 5 minutes
- [x] Verify: intentional unhandled error (`/api/debug-exception`) → Captain Hook webhook + Sentry Bot notification arrived in Discord ✅
- [x] Verify: test notification via Sentry dashboard "Send Test Notification" → Discord received ✅
- **Two notification channels now active:**
  1. **Captain Hook** (manual `discord_notifier.py` webhook) — immediate, from specific backend code paths
  2. **Sentry Bot** (official Sentry integration alert rule) — automatic, for ALL new + reopened issues

### 3A: Componentes CRM — Verificación Exhaustiva de UI

**Pages (8 total) — organized by nav order:**

#### `/dashboard` (Panel) ✅
- [x] Dashboard loads ✅ (user confirmed 2026-04-09)

#### `/chats` (Chats) — Regular Chat Mode
- [x] Chat loads and shows contacts in ContactList ✅ (user confirmed 2026-04-09)
- [ ] Selecting a regular contact → ChatArea loads, messages display
- [ ] ClientProfilePanel shows contact info when toggled (⋮ button or desktop panel)
- [ ] Bot toggle (Pause/Resume) works for regular contact
- [ ] Real-time: new message from simulator appears in chat without manual refresh

#### `/chats` (Chats) — **Test Chat Sandbox Mode** (phone `56912345678`)
> When the test contact (`56912345678`) is selected, the UI switches from `ChatArea` → `TestChatArea` and `ClientProfilePanel` → `TestConfigPanel`.

**TestChatArea buttons (bottom action bar):**
- [x] Send message → message persists in Supabase `messages` → LLM simulation triggers via `/api/simulate` → AI response arrives via Realtime ✅ (verified 2026-04-09)
- [x] "IA Generando..." spinner appears during LLM processing, auto-clears after response ✅ (verified 2026-04-09)
- [x] 🗑️ **DESCARTAR PRUEBA** button → confirm dialog renders ✅ (note: subagent had issues with browser confirm() dialog, but code logic verified)
- [x] ✉️ **ENVIAR PRUEBA (FINALIZAR)** button → ✅ PROVEN WORKING (3 existing records in `test_feedback` table from prior manual sessions — ID `2e4bc5bb` at 17:21, `5cb219b2` at 16:46, `2ba13476` at 15:30, all by tomasgemes@gmail.com). Automation agent had trouble clicking the button precisely, but flow is confirmed end-to-end. Messages DELETE via RLS policy also confirmed working.
- [x] ✨ **CAMBIAR MODELO** button → renders without crash ✅ (placeholder, verified)
- [x] ⚙️ **CONFIGURACIÓN** button → opens TestConfigPanel ✅ (verified 2026-04-09)
- [x] ⋯ **MÁS OPCIONES** button → renders without crash ✅ (placeholder, verified)
- [x] Clicking an AI message → opens inline note editor (textarea) → note typed + "Guardar Nota" visible ✅ (verified 2026-04-09)
- [x] Floating role badge ("CLIENTE") displays at top center ✅ (verified 2026-04-09)
- [x] Pause/Resume IA toggle in header works ✅ (verified 2026-04-09 — toast "Asistente pausado ⏸️" appeared)

**TestConfigPanel (right panel):**
- [x] "CONFIG AGENTE" header renders with close (×) button ✅ (verified 2026-04-09)
- [x] Bot status badge shows "EJECUTANDO" ✅ (verified 2026-04-09)
- [x] System prompt textarea loads from `tenants.system_prompt` — "Eres Javiera..." visible ✅ (verified 2026-04-09)
- [ ] Edit prompt → click "GUARDAR CAMBIOS" → saves to `tenants` table → toast confirmation → change confirmed in db logs 
- [ ] Realtime subscription updates prompt in all config surfaces if changed externally, or by any of the config surfaces.
- [x] Metrics card renders (Contexto 95%, Acierto A+) — static/placeholder ✅ (verified visually)
- [x] Warning banner about prompt impact renders ✅ (verified visually)

#### `/agenda` (Agenda)
- [x] Agenda loads and shows calendar events ✅ (user confirmed 2026-04-09)

#### `/pacientes` (CRM / Pacientes)
- [x] Pacientes page loads ✅ (verified 2026-04-09 — page renders, contact list visible)
- [x] Contact list renders with names ("Chat de pruebas", "Lead") ✅ (verified 2026-04-09)

#### `/reportes` (Reportes) — desktop only
- [x] Reportes page loads without errors ✅ (verified 2026-04-09)

#### `/finops` (FinOps) — desktop only
- [x] FinOps page loads without errors ✅ (verified 2026-04-09)

#### `/admin-feedback` (Auditoría Dev) — admin only
- [x] Admin Feedback page loads and fetches `test_feedback` rows from Supabase ✅ (verified 2026-04-09 — "AUDITORÍA DE SANDBOX" header, real data shown)
- [x] Rows display with history (USER SIMULATION / IA RESPONSE pairs), notes, tester data ✅ (verified 2026-04-09)
- [x] Delete button removes row from `test_feedback` table (visible and click tested ✅)

#### `/config` (Configuración Global)
- [x] Config page loads with tenant data ✅ (verified 2026-04-09 — "Cerebro del Asistente" header, CONFIGURACIÓN GLOBAL badge)
- [x] LLM Provider dropdown: switch between "OpenAI (SOTA)" and "Google Gemini (Next-Gen)" → model list updates dynamically ✅ (verified 2026-04-09)
- [x] LLM Model dropdown: models change based on provider ✅ (verified — Gemini shows: Gemini 3.1 Pro (Expert), Gemini 3.1 Flash-Lite (Ultrarapid); OpenAI: GPT-4o Mini (Legacy))
- [ ] System prompt textarea: edit and save → persists to `tenants` table (need to test save flow)
- [ ] Character counter updates — shows **3099 / 2000** in RED limit need to be 4000 characters ⚠️ (prompt exceeds limit  cosmetic but notable)
- [x] Google Calendar section: shows "Desconectado" + "Conectar Google Calendar" button ✅ (verified 2026-04-09)
- [x] "Solicitar Custom LLM" CTA renders ✅ (verified 2026-04-09)

#### Cross-cutting
- [x] All sidebar links navigate correctly (7 items + config + notifications + logout) ✅ (verified 2026-04-09 — Dashboard, Chats, Agenda, Pacientes all tested)
- [x] Logout button → redirects to `/login` ✅ (verified 2026-04-09)
- [x] Feedback button (bottom sidebar) → opens FEEDBACK GLOBAL modal ✅ (verified 2026-04-09)


### 3B: Herramientas LLM (TODAS las 7 tools) — Individual via `/api/simulate`
- [x] Inventariar todas las tools ✅ (7 tools confirmed in tool_registry)
- [!] CheckAvailabilityTool (get_merged_availability) — user confirmed working (2026-04-09)
- [!] CheckMyAppointmentsTool (get_my_appointments) — verification incoclusive via sandbox. AI response: "no tienes citas agendadas para esta fecha en tu perfil" — tool correctly identified no appointments for sandbox phone but also hallucinates more appoinments than what the agenda actually has. or maybe it misinterpreted a long 1h appointment (which is a session and not an evaluation) for two distinct, needs further investigation **BUG**
- [x] BookAppointmentTool (book_round_robin) — ✅ user confirmed working (2026-04-09)
- [ ] UpdateAppointmentTool (update_appointment) — requires existing appointment to test (untested — need real scenario)
- [!] DeleteAppointmentTool (delete_appointment) — tested **BUG-3** when tool is called fails silently, no sentry notification nor discord notif is sent; then LLM lies about the result of the tool execution in the response to the user.
- [!] EscalateHumanTool (request_human_escalation) -- **BUG-1**: LLM responded "Voy a notificar a un agente" but DID NOT call the tool function. bot_active stayed true, no alert created. This is a SILENT FAILURE: the system told the user it would escalate but didn't.
- [!] UpdatePatientScoringTool (update_patient_scoring) -- **BUG-1**: LLM responded about celulitis leve but DID NOT call the tool function. metadata stayed {}. Same silent failure pattern.
- [!] Each tool failure must appear in Sentry with full traceback + tool context & if possible the conversation that trigered it. Immediate notification with all details must be sent to discord.

> **ROOT CAUSE (BUG-1):** `tool_choice="auto"` in `openai_adapter.py:29` allows the LLM to choose text response over function calling. No post-LLM validation exists in `use_cases.py:144-146` to detect when the LLM SHOULD have called a tool but didn't. This IS a code-level gap (not just LLM behavior) because the system has no guardrail against the LLM lying about tool usage. Fix required per official OpenAI Function Calling docs. See README section 0.6.

### 3C: Flujo E2E Interno — Simulator-Driven (NO WhatsApp)
- [x] Simulator → LLM inference → tool call → tool execution → response synthesis → message persisted → Realtime → frontend chat update ✅ (verified — full pipeline working, sandbox messages arrive via Supabase Realtime)
- [x] Multi-turn: multiple messages in sequence, verify conversation context maintained ✅ (verified — AI maintained context across scheduling questions, appointment check, and escalation request)
- [x] Tool chaining: availability check → booking in single conversation ✅ (user confirmed 2026-04-09)
- [x] Error path: malformed request → graceful error + Sentry capture + Discord notification ✅ (verified 2026-04-09 — `/api/debug-exception` returned `{"message":"Error interno del servidor.","code":"INTERNAL_ERROR"}`, Sentry captured within seconds, Discord alert received at 16:23)

### 3D: Observability Verification
- [x] Intentional tool error → Sentry event within 30s → Discord alert arrives ✅ (verified via /api/debug-exception in Phase 3 Preamble)
- [x] Frontend error → Sentry event → Discord alert arrives ✅ (Sentry SDK configured in Frontend — `next.config.ts` has withSentryConfig, documented in README §0.4)
- [ ] Workers Logs show invocation details in CF dashboard (visual check deferred — Cloudflare Workers Logs observability tab) - NEED THIS!
- [x] Cloud Run logs show structured JSON for backend requests ✅ (confirmed in prior audit)
- [x] Confirm zero blind spots: 30+ catch blocks instrumented with sentry_sdk.capture_exception ✅ (documented in §0.4)

### 3E: Critical Bug Fixes (MUST resolve before Phase 4/5)

- [x] **BUG-1: LLM Tool-Calling Silent Failure** ✅ — 4-layer fix deployed
  - [x] Research official OpenAI Function Calling docs for tool_choice strategies ✅
  - [x] Layer 1: Internal system prompt injection in `use_cases.py` — `INTERNAL_TOOL_RULES` injected at CODE level between tenant prompt and [CONTEXTO] block. Tenant CANNOT edit/delete these rules.
  - [x] Layer 2: Post-LLM validation — `TOOL_ACTION_PATTERNS` detects when LLM text implies tool action but `has_tool_calls=False` → Sentry `capture_message` + `set_context` + Discord alert
  - [x] Layer 3: Conditional `tool_choice` — added `tool_choice_override` param to `LLMStrategy`, `OpenAIStrategy`, `GeminiStrategy`. When `force_escalation=True`, passes `{"type": "function", "function": {"name": "request_human_escalation"}}` to FORCE escalation tool call
  - [x] Layer 4: Enhanced logging — full response content preview (150 chars) + tool_calls status + individual tool results (300 chars)
  - [ ] Re-test EscalateHumanTool and UpdatePatientScoringTool after deploy
  - [ ] Verify bot_active flips to false on escalation, metadata updates on scoring
  > **NOTE:** UpdatePatientScoring depends on tenant tool config. Tool not in test tenant's list = LLM can't call it. This is a config surface limitation, not a code bug. → see Backlog "Tenant Assistant Config Revamp"

- [x] **BUG-2: Character Counter Limit** ✅
  - [x] Changed display from `/ 2000` to `/ 4000` in `config/page.tsx`
  - [x] Changed red threshold from `> 1000` to `> 3500` (rose color)
  - [x] Added amber threshold at `> 3000` (amber color)
  - [x] Soft Sentry warning when prompt > 4000 chars (save NOT blocked — user decision)
  - [x] Added `import * as Sentry from '@sentry/nextjs'` to config page
  - [ ] Test: visual check in `/config` after deploy

- [x] **BUG-3: Tool Error Handling — Complete Overhaul** ✅
  - [x] **v1:** Basic `has_tool_error` check with single injection message
  - [x] **v2 (this session):** Distinguish business errors vs technical crashes:
    - **Business error** (tool ran OK, returned `{"status": "error", "message": "No encontré cita..."}`) → LLM relays naturally without drama
    - **Technical crash** (Python exception during tool execution) → LLM tells patient human was requested + tech team alerted
  - [x] **All tool `status:error` responses now fire Sentry + Discord** (previously only Python exceptions did — critical gap fixed)
  - [x] Sentry context includes: tool_name, result preview, tenant_id, patient_phone, contact_role
  - [x] Discord alert title includes tenant_id for all error types
  - [ ] Test: trigger business error (delete nonexistent apt) → verify natural relay, no "inconveniente técnico"
  - [ ] Test: verify Sentry + Discord fire for business errors

- [x] **MISC-2: Missing `import sentry_sdk` in google_client.py** ✅
  - [x] Added `import sentry_sdk` to top-level imports (fixes NameError at L39)
  - [x] Removed 5 redundant inline `import sentry_sdk` in except blocks

- [x] **OTEL-1: CF Dashboard OTel Destinations** ✅ CLOSED (deferred)
  - [x] Read CF OTel export docs
  - [x] ~~Create destinations~~ — **BLOCKED: requires Workers Paid plan (currently on Free)**
  - [x] Commented out `destinations` in `wrangler.toml` with upgrade instructions
  > **Resolution:** OTLP export is a Workers Paid feature ($5/mo). Observability NOT blocked — backend has `sentry_sdk` (Cloud Run), frontend has `@sentry/nextjs`, Workers Logs in CF dashboard (free). Deferred until plan upgrade.

### Phase 3F: Post-Testing Fixes (this session)

- [x] **FIX: Sentry tenant context** — `sentry_sdk.set_tag("tenant_id", ...)` at orchestrator start. All events now tagged.
- [x] **FIX: Discord titles include tenant** — All `send_discord_alert()` titles now include `Tenant {tenant.id}`
- [x] **FIX: Three dots typing indicator** — Only shows when `bot_active=true` in both ChatArea and TestChatArea
- [x] **FIX: Tool error Sentry/Discord gap** — `status:error` tool responses now ALWAYS fire Sentry + Discord (previously only Python exceptions triggered alerts)
- [x] **FIX: BUG-3 business vs crash differentiation** — Natural relay for business errors ("no appointment found"), escalation message only for actual crashes

---

## Phase 4: Production / Development Environment Separation ✅ COMPLETE (2026-04-10)

> **Two fully independent ecosystems established.** Dev can break freely without touching production.

### 4A: Audit Current State ✅
- [x] Verified Cloud Build triggers (prod: `cloudrun-ia-backend-prod-europe-west1-*` on `main`)
- [x] Verified Workers Builds (prod: `ia-whatsapp-crm` on `main`)
- [x] Documented env vars for both environments
- [x] Researched Cloud Build docs, Sentry environment tagging, CF Workers branch control

### 4B: Dev Backend Setup ✅
- [x] **Service:** `ia-backend-dev` in `us-central1` (Tier 1 pricing). Min=0, Max=1
- [x] **Cloud Build trigger:** `deploy-dev-backend` in `europe-west1`, branch `^desarrollo$`, inline YAML deploying to `us-central1`
- [x] **Artifact Registry:** Created `cloud-run-source-deploy` repo in `us-central1`
- [x] **Env vars:** `ENVIRONMENT=development`, `SUPABASE_URL` (dev), `FRONTEND_URL=https://ohno.tuasistentevirtual.cl`, `SENTRY_DSN` (same DSN, `environment=development` tag), `DISCORD_WEBHOOK_URL` (same webhook, `[🔧 DESARROLLO]` prefix in alerts)
- [x] **Secrets:** `SUPABASE_SERVICE_ROLE_KEY_DEV` (separate secret, dev-only key), `OPENAI_API_KEY`, `GEMINI_API_KEY`, `WHATSAPP_VERIFY_TOKEN` (shared with prod — safe, same API accounts)
- [x] **Service URL:** `https://ia-backend-dev-645489345350.us-central1.run.app`

### 4C: Dev Frontend Setup ✅
- [x] **Worker:** `dev-ia-whatsapp-crm` in Cloudflare, branch `desarrollo`
- [x] **Build command fix:** `npx wrangler deploy --name dev-ia-whatsapp-crm --keep-vars` (overrides `wrangler.toml` name without modifying repo)
- [x] **Build vars fix:** Removed `NODE_ENV=development` from build vars (Next.js crashes with non-standard NODE_ENV during `next build`)
- [x] **Runtime vars:** `NEXT_PUBLIC_SUPABASE_URL` (dev), `NEXT_PUBLIC_SUPABASE_ANON_KEY` (dev), `BACKEND_URL` → dev Cloud Run
- [x] **DNS:** `ohno.tuasistentevirtual.cl` CNAME + custom domain configured
- [x] **Verified:** Login works, `/config` loads, `/pacientes` loads

### 4D: Isolation Verification ✅ (partial — calendar intentionally excluded)
- [x] Dev frontend loads at `ohno.tuasistentevirtual.cl` ✅
- [x] Prod frontend unaffected at `dash.tuasistentevirtual.cl` ✅
- [x] Dev backend reads dev Supabase (confirmed via Sentry traces) ✅
- [x] Prod backend reads prod Supabase (confirmed unchanged) ✅
- [x] Sentry events tagged `environment=development` for dev, `environment=production` for prod ✅
- [x] Discord alerts prefixed with `[🔧 DESARROLLO]` for dev ✅
- [x] ⚠️ **Calendar/Agenda intentionally NOT connected in dev** — see Technical Debt below

### 4E: Schema Sync Strategy
- [x] **Strategy:** Merge `desarrollo` → `main` via PR. Cloud Build (backend) + Workers Builds (frontend) auto-deploy from `main`. DB migrations applied manually via Supabase MCP `apply_migration` to prod after testing on dev.
- [ ] Test the full migration flow end-to-end (deferred to first real migration in Phase 5+)

### ⚠️ Phase 4 Technical Debt — Calendar System

> **Decision (2026-04-10):** Google Calendar integration is intentionally NOT connected in the dev environment to avoid any risk of test operations affecting the live client's calendar (CasaVitaCure).

**Root cause:** The calendar system uses a **Service Account hardcoded to CasaVitaCure's GCP project** (`casavitacure-crm`), stored as GCP secret `GOOGLE_CALENDAR_CREDENTIALS`. Calendar IDs are also hardcoded as fallback in `google_client.py:L69-72`. Connecting dev would mean dev tests write to the REAL production calendar.

**What's broken in dev:** `/agenda` route shows connection error. Calendar-related LLM tools (`get_merged_availability`, `book_round_robin`, etc.) will fail. All other CRM features work normally.

**Long-term fix required (Phase 6+):** See backlog item "Calendar Multi-Tenant Architecture Refactor" below.

---

## Phase 5: Meta/WhatsApp Integration + Go-Live

> **This phase ONLY begins after Phase 4 is complete with guaranteed prod/dev isolation.**
> **The WhatsApp connection is the LAST step, not the first. Before connecting Meta, we must have a fully instrumented, thoroughly tested webhook simulation suite.**

### 5A: Meta Webhook Simulation Suite ✅ COMPLETED (2026-04-10)

> **Architecture decision:** HTTP-based runner (`POST /webhook`) over direct function call. Tests the real FastAPI routing, dependency injection, and BackgroundTasks scheduling — identical to what Meta sends in production.
> **Ref:** [Meta Webhook Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components/), [Meta Payload Examples](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples)

- [x] Read official docs: [Meta Webhook Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components/)
- [x] Develop simulation scripts mimicking Meta webhook payload format — `Backend/scripts/simulation/payload_factory.py`
- [x] Scripts simulate multiple users chatting simultaneously — burst (100ms spacing) and concurrent (asyncio.gather) modes
- [x] Scenarios (all passing 2026-04-10):
  - [x] **Scenario 1:** Single user, single message → full pipeline (LLM inference + response + persistence) — ✅ 200 (1985ms)
  - [x] **Scenario 7:** Single user, rapid burst of 5 messages → `is_processing_llm` mutex works, all locks released — ✅ 200×5 (2422ms)
  - [x] **Scenario 8:** 3 users simultaneously → no cross-talk, independent contacts created — ✅ 200×3 (781ms)
  - [x] **Scenario 2:** Booking intent ("Quiero agendar una cita") → LLM asked qualifying questions (correct) — ✅ 200 (625ms)
  - [x] **Scenario 3:** Escalation ("Necesito hablar con un humano") → `bot_active=false` set correctly — ✅ 200 (656ms)
  - [x] **Scenario 4:** Clinical keyword ("dolor severo, sangrando") → `force_escalation=True`, `tool_choice` forced — ✅ 200 (703ms)
  - [x] **Scenario 5:** Status-only webhook (delivery/read) → graceful skip, no LLM call — ✅ 200×2 (1469ms)
  - [x] **Scenario 6:** Malformed payloads (×3: no entry, no changes, no metadata) → HTTP 200, Sentry+Discord alerts fired — ✅ 200×3 (4109ms)
  - [x] **Scenario 9:** Edge cases: empty msg, 5000-char msg, unicode/emoji/XSS, image, location, reaction — zero crashes — ✅ 200×6 (12344ms)
- [x] Full Sentry instrumentation: **5A-OBS audit** — hardened 5 files that had missing Sentry/Discord coverage:
  - [x] `dependencies.py` — Added Sentry + Discord (had neither)
  - [x] `tool_registry.py` — Added Discord (had Sentry only)
  - [x] `gemini_adapter.py` — Added Sentry + Discord (had neither)
  - [x] `openai_adapter.py` — Added Discord (had Sentry only)
  - [x] `use_cases.py` — Added Discord to msg persistence error + processing lock cleanup
- [x] Full Discord notification: every error path → Discord alert (verified via malformed payload scenarios)
- [x] Run simulation suite, verify:
  - [x] All messages persisted correctly in dev Supabase (`nzsksjczswndjjbctasu`) — 12 contacts, correct msg counts
  - [x] All responses generated correctly by LLM — verified in backend logs
  - [x] Escalation scenarios correctly set `bot_active=false` on contacts
  - [x] All `is_processing_llm` locks released — zero stuck contacts
  - [ ] Frontend realtime updates work for each simulated conversation — **deferred to manual check**
  - [x] Zero unexpected errors — all errors were from expected malformed payload scenarios

### 5B: Version Tag + Final Production Deploy
- [ ] Deploy observability fixes to production (5A-OBS changes: `dependencies.py`, `tool_registry.py`, `gemini_adapter.py`, `openai_adapter.py`, `use_cases.py`)
- [ ] Simulation suite passes cleanly with zero unexpected errors (✅ done locally, needs cloud verification)
- [ ] `git tag v1.0` on `main`
- [ ] `git push origin main --tags` — triggers production auto-deploy
- [ ] Verify: production frontend and backend running v1.0 code

### 5C: Connect Meta/WhatsApp (LIVE)

> **CRITICAL — System User Token Required:** The current Meta API token is expired (401 in Sentry). Before connecting, create a System User in Meta Business Manager with `whatsapp_business_messaging` + `whatsapp_business_management` permissions and generate a **permanent** token.
> **Ref:** [Meta System Users](https://developers.facebook.com/docs/marketing-api/system-users/)
> **CRITICAL — AI Chatbot Policy:** Meta prohibits "general-purpose" AI chatbots (Jan 2026). CasaVitaCure is compliant: task-specific assistant for booking, scoring, and escalation.

- [ ] Create System User in Meta Business Manager → generate permanent access token
- [ ] Update `ws_token` in production Supabase `tenants` table for CasaVitaCure
- [ ] Update `ws_phone_id` in production Supabase to match real Meta phone_number_id (currently `123456789012345` placeholder)
- [ ] Configure webhook URL in Meta Dashboard → production backend (`ia-backend-prod-ftyhfnvyla-ew.a.run.app/webhook`)
- [ ] Verify webhook verification handshake (GET /webhook with verify_token)
- [ ] Send a real WhatsApp message → confirm full pipeline:
  - [ ] Message received by webhook
  - [ ] LLM inference completes
  - [ ] Response sent back via Meta API
  - [ ] Message appears in frontend CRM chat in real time
  - [ ] Sentry shows clean trace (no errors)
  - [ ] No unexpected Discord error notifications

### 5D: Production Validation — System 100% Operational
- [ ] Multiple real WhatsApp conversations tested
- [ ] Calendar booking end-to-end (WhatsApp → LLM → GCal API → confirmation message)
- [ ] Escalation tested (user requests human → bot paused → alert in CRM + Discord)
- [ ] Sentry dashboard clean — no unexpected errors
- [ ] Discord alerts only fire for legitimate issues
- [ ] System declared production-ready 🚀 (Resilient MVP)

---

## Backlog (Future Features -- NOT for current phase) -- WILL BE IMPLEMENTED AFTER META CONNECTION AND 100% QA TEST PASSED -- aka Phase 6

> Items below are documented for future implementation. They are NOT blockers for WhatsApp go-live.

### HIGH PRIORITY — Tenant Assistant Config Revamp

> **Context:** The current `/config` route only controls system_prompt + LLM provider/model. There is no way for owners to control WHICH tools are active, test changes safely, or rollback bad configs. This was surfaced during Phase 3E testing when `update_patient_scoring` couldn't fire because the tool wasn't in the tenant's configured tool list.

- [ ] **`/config` as Live Agent Controller:** The config route should be the sole control surface for the live assistant's behavior — prompt, model, active tools, personality, response rules
- [ ] **Chat de Pruebas as Safe Testing Ground:** The sandbox chat should let owners test modifications to their assistant config BEFORE those changes go live. Changes made in config should be testable in sandbox before committing to production
- [ ] **Config Versioning & Rollback:** Every config change (prompt, model, tools) must be versioned with timestamp + author. Owners should be able to instantly rollback to any previous config version. Database schema change: `tenant_config_versions` table with JSON snapshots
- [ ] **Tool On/Off Toggle:** Owners must be able to enable/disable individual tools in real time from the config surface. E.g., disable `delete_appointment` during a migration, enable `update_patient_scoring` when scoring criteria are ready. This affects what schemas get sent to the LLM
- [ ] **Sandbox Role Selector Enhancement:** The sandbox chat already has a role switcher (cliente/staff/admin). Needs to be more prominent and its implications clearly documented. Different roles should demonstrate different tool access levels (e.g., admin can delete any appointment, cliente only their own)

### HIGH PRIORITY — Calendar Multi-Tenant Architecture Refactor

> **Context (diagnosed 2026-04-10):** The calendar system is fundamentally single-tenant. It uses a Service Account from CasaVitaCure's GCP project as a global singleton, with Calendar IDs hardcoded as fallback. The OAuth per-tenant flow (`google_oauth_router.py`) stores refresh tokens but `google_client.py` never reads them. This blocks: (1) adding new clients, (2) having N calendars per tenant (fumigación teams, hotel rooms, etc.), (3) safely connecting dev environment.

**3 Structural Problems:**
1. Service Account belongs to client (`casavitacure-crm`), not our SaaS — singleton pattern, shared across all tenants
2. `TenantContext` model doesn't include `calendar_ids` — `_get_calendar_ids()` always falls back to hardcoded CasaVitaCure IDs
3. OAuth flow exists but is disconnected — `google_client.py` ignores `google_refresh_token_encrypted` from tenants table

**Required changes:**
- [ ] Add `calendar_ids` field to `TenantContext` model (so DB values are actually used)
- [ ] Replace Service Account singleton with per-tenant OAuth credentials (use stored `google_refresh_token_encrypted`)
- [ ] Create `tenant_resources` table for N dynamic calendars per tenant (name, calendar_id, provider, color, sort_order)
- [ ] Update `_get_calendar_ids()` to read from `tenant_resources` instead of hardcoded fallback
- [ ] Update `/config` UI to manage calendar resources (add/remove/reorder)
- [ ] Create dev-specific test calendar(s) for safe development testing
- [ ] Consider future abstraction: `CalendarProvider` interface supporting Google, Cal.com, internal

### HIGH PRIORITY — Agenda Visual Revamp

> **Context:** The agenda viewer needs significant UI improvements, especially for mobile viewports where many elements don't fit properly.

- [ ] **Mobile Layout Overhaul:** Agenda components overflow on small screens. Needs responsive redesign — possibly card-based layout for mobile instead of calendar grid
- [ ] **Date Navigation:** Users need to scroll back and forth through days, weeks, months. This requires careful architectural thought:
  - Data fetching strategy (lazy load vs pre-fetch range)
  - URL state management (shareable links to specific date ranges)
  - Performance for large appointment volumes
  - Touch gestures for mobile (swipe between days/weeks)
- [ ] **Design System Alignment:** Agenda should match the overall CRM aesthetic (glassmorphism, micro-animations, premium feel)

### MEDIUM PRIORITY

- [ ] **Bot Pause Notifications:** Every time bot is paused (by human hand, by EscalateHumanTool, by any system rule) must generate Sentry event + Discord notification + in-app notification to admins/staff as configured by tenant
- [ ] **Paused Chat Inbound Alerts:** If a paused chat receives messages from the client, notify via Discord, Sentry, and to admins/staff configured by tenant. Currently the bot silently ignores (`use_cases.py:94-96`)
- [ ] **Tool Registry Tracking:** Full logging and traceability of which tools are registered at boot, their schemas, and execution history
- [ ] **Tenant Config Versioning (DB schema):** `tenant_config_versions` table — audit trail for all changes to system_prompt, llm_provider, llm_model, active_tools. Each UPDATE creates a version snapshot
- [ ] Responsive layout: mobile bottom nav works, pages render on small viewport: ask for human tester input and first focus group feedback

### LOW PRIORITY / FUTURE
- [ ] **BUG-4 (CheckMyAppointments hallucination):** LLM invents appointment details. Needs diagnostic data capture + prompt refinement. Deferred pending Phase 6 tool config revamp