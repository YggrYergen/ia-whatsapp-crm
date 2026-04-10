# AI CRM Production Stabilization — Implementation Plan

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por docs oficiales actualizados. Leer docs PRIMERO, implementar DESPUÉS. Sin excepciones.

> **⚠️ LEY POST-IMPLEMENTACIÓN:** Toda solución confirmada como funcional DEBE ser documentada EN ESE MOMENTO con: (1) qué se hizo, (2) por qué funciona, (3) links a los docs oficiales que lo respaldan. Esto previene que futuras sesiones de LLM rompan lo que ya funciona por desconocimiento.

## Status: Phase 0-4 COMPLETE ✅ | Phase 5 (Meta/WhatsApp) NEXT | Calendar disconnected in dev (by design, see Phase 4 tech debt)

---

## Completed Phases
- ✅ Phase 0: Pre-flight
- ✅ Phase 1A: Infrastructure  
- ✅ Phase 1B: Security (frontend done, backend deployed)
- ✅ Phase 1C: Auth PKCE — RESOLVED (see README §0.1)
- ✅ Phase 1D: Backend Deploy — FULLY VERIFIED
- ✅ Phase 2A: Sentry Backend — FULLY VERIFIED (see below)
- ✅ Phase 2D: Discord Alerts — FULLY VERIFIED (see below)
- ✅ Phase 2E: OpenNext Migration — FULLY VERIFIED (see below)
- ✅ Phase 2F: Sentry Coverage Hardening — FULLY VERIFIED (commit `5ba489d`, 2026-04-09)

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

## Phase 2B: Sentry Frontend Client-Side — COMPLETE ✅

### History: Next.js 14→15 Upgrade (COMPLETED)

> **⚠️ CRITICAL — DO NOT SKIP THIS SECTION. READ BEFORE TOUCHING FRONTEND SENTRY.**

#### Problem Discovered (via docs research)

| Issue | Detail |
|:---|:---|
| **`sentry.client.config.ts` is DEPRECATED** | Sentry SDK v10 expects `instrumentation-client.ts` — a Next.js 15+ file convention. [Sentry manual setup docs](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) |
| **`disableClientInstrumentation: true`** | This flag in `next.config.js` **KILLS all client-side error capture**. It was set to prevent Edge runtime crashes on Next.js 14. |
| **`instrumentation-client.ts` requires Next.js 15+** | This is a [Next.js file convention](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client) not available in 14.x |
| **Next.js 14.1.4 is EOL** | 2 major versions behind, known CVEs, no longer receiving security patches |

#### Decision: Upgrade Next.js 14.1.4 → 15.5.15 (COMPLETED ✅)

> **⚠️ DO NOT DOWNGRADE Next.js back to 14.x — it will BREAK Sentry frontend integration.**
> The `instrumentation-client.ts` file ONLY works on Next.js 15+.
> The old `sentry.client.config.ts` file is DEPRECATED and should NOT be re-created.
> **⚠️ DO NOT DOWNGRADE `lucide-react` below ^1.7.0** — older versions have React 19 peer dep conflicts that fail the build.

**Docs consulted:**
- [Next.js 15 upgrade guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15)
- [Sentry Next.js manual setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) — specifies `instrumentation-client.ts`
- [instrumentation-client.ts convention](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client)

### Resolution: OpenNext Migration (Phase 2E) Unblocked Sentry

The `@cloudflare/next-on-pages` adapter (deprecated) did NOT execute `instrumentation-client.ts` at runtime. After migrating to OpenNext (Phase 2E), the Sentry SDK initializes correctly and **captures client-side errors in production** ✅.

**Verified 2026-04-09:** Sentry dashboard at `tuasistentevirtual.sentry.io` shows frontend issues with full stack traces.

---

## Phase 2C: Sentry Frontend Server-Side — AVAILABLE (via OpenNext)

- With OpenNext, the Worker has a Node.js-compatible runtime
- Server-side Sentry is now possible via `@sentry/nextjs` + `compatibility_date >= 2025-08-16`
- Will be fully validated during Phase 3 (E2E testing)

---

## Phase 2E: OpenNext Migration (Cloudflare Pages → Workers) — COMPLETE ✅

### Official Docs Consulted

| Doc | URL | Key Finding |
|:---|:---|:---|
| OpenNext Get Started | [link](https://opennext.js.org/cloudflare/get-started#existing-nextjs-apps) | 13-step guide for existing apps; `@cloudflare/next-on-pages` removal documented |
| OpenNext Env Vars | [link](https://opennext.js.org/cloudflare/howtos/env-vars) | Production vars via Cloudflare dashboard, `.env` files for dev, `NEXTJS_ENV` for environment selection |
| OpenNext Dev & Deploy | [link](https://opennext.js.org/cloudflare/howtos/dev-deploy) | Workers Builds for CI/CD, `opennextjs-cloudflare build && deploy` commands |
| Workers Logs | [link](https://developers.cloudflare.com/workers/observability/logs/workers-logs/) | `[observability]` block in wrangler.toml for native logs |
| OTel Export to Sentry | [link](https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/sentry/) | `destinations` in observability block, manual setup in CF dashboard |
| Sentry CF Workers | [link](https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/) | `compatibility_date >= 2025-08-16` required for `https.request` |
| Workers Builds Config | [link](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/) | Build/deploy commands, root directory, branch config |

### What Was Done

| Step | Fix | Verification |
|:---|:---|:---|
| 1. Install OpenNext | `@opennextjs/cloudflare@latest` + `wrangler@latest` | Build output generates `.open-next/` |
| 2. Replace wrangler.toml | Pages format → Workers format | `main = ".open-next/worker.js"` |
| 3. Create open-next.config.ts | Minimal config | Build succeeds |
| 4. Update next.config.js | Add `initOpenNextCloudflareForDev()` | Dev server works |
| 5. Update package.json | New `preview`, `deploy` scripts | Scripts functional |
| 6. Deploy to CF Workers | `npx wrangler deploy --keep-vars` | Worker active |
| 7. Workers Builds CI/CD | Connect GitHub, set build/deploy commands | Auto-deploy on push to main ✅ |
| 8. Custom domain | Move `dash.tuasistentevirtual.cl` from Pages to Workers | Domain resolves ✅ |
| 9. Env vars | 4 build vars + 3 runtime vars in CF dashboard | Sentry + Supabase functional ✅ |
| 10. Observability | `[observability]` block with logs + OTel destinations | Workers Logs visible in dashboard ✅ |
| 11. .gitignore fix | Added `.env.local` to prevent `localhost:8000` leak | No more routing crash ✅ |
| 12. Source maps | `upload_source_maps = true` | Sentry shows readable stack traces |
| 13. compatibility_date | Set to `2025-08-16` | Sentry SDK `https.request` works ✅ |

### Critical Bug Found and Fixed

**`TypeError: Expected "8000" to be a string`**
- **Root cause:** `.env.local` had `BACKEND_URL=http://localhost:8000` and was NOT in `.gitignore`. The build on CF Workers Builds picked up this file, causing `next build` to compile rewrites pointing to `localhost:8000`. The `path-to-regexp` library in Next.js 15 threw a TypeError when the port `8000` was parsed as a number instead of a string.
- **Fix:** Added `.env.local` to `.gitignore` (commit `19b665f`). Also added `BACKEND_URL` as a build variable in Workers Builds config.
- **Lesson:** `.env.local` files must NEVER be committed to git. All build-time env vars must be set in the CF dashboard.

### Final Verified State (2026-04-09)

- **Worker:** `ia-whatsapp-crm` active, serving 100% traffic
- **Custom domain:** `dash.tuasistentevirtual.cl` → Worker
- **Sentry Frontend:** ✅ Capturing client-side JS errors
- **Workers Logs:** ✅ Showing in CF dashboard (Observability tab)
- **API Rewrites:** ✅ `/api/*` correctly proxied to Cloud Run backend
- **Workers Builds:** ✅ Auto-deploying on push to `main`
- **Pending:** OTel destinations in CF dashboard for Sentry trace/log export

---

## Phase 2F: Sentry Coverage Hardening — COMPLETE ✅

### Official Docs Consulted

| Doc | URL | Key Finding |
|:---|:---|:---|
| Sentry Python: capture_exception | [link](https://docs.sentry.io/platforms/python/usage/#capturing-errors) | `sentry_sdk.capture_exception(e)` sends exception + traceback to Sentry |
| Sentry Python: Enriching Events | [link](https://docs.sentry.io/platforms/python/enriching-events/context/) | `sentry_sdk.set_context()` adds custom key-value data to events |
| Sentry Next.js: captureException | [link](https://docs.sentry.io/platforms/javascript/guides/nextjs/usage/) | `Sentry.captureException()` / `Sentry.captureMessage()` for client-side |

### Problem Discovered

Systemic "silent failures" — 30+ catch blocks across backend and frontend were logging errors to console/Cloud Logging but **never sending them to Sentry**. This made production debugging of tool failures, credential errors, and frontend data operations impossible. The `tool_registry.execute_tool()` catch block was the #1 black hole: all 7 LLM tool failures were caught, logged locally, and swallowed.

### What Was Done

#### Backend (6 files, 12 catch blocks)

| File | Location | Fix |
|:---|:---|:---|
| `tool_registry.py` | `execute_tool()` | Added `sentry_sdk.capture_exception()` + `set_context("tool_execution", {tool_name, kwargs_keys})` |
| `tools.py` | `EscalateHumanTool.execute()` | Replaced `except Exception: pass` with logging + `sentry_sdk.capture_exception()` |
| `tools.py` | `UpdatePatientScoringTool.execute()` | Added `sentry_sdk.capture_exception()` |
| `use_cases.py` | Contact creation, msg persistence, tool loop, cleanup | 4 catch blocks: all added `sentry_sdk.capture_exception()` |
| `google_client.py` | Credential loading from ENV | Added `sentry_sdk.capture_exception()` |
| `meta_graph_api.py` | HTTP errors + network errors | Added `sentry_sdk.capture_exception()` + `set_context("meta_graph_api", {phone_number_id, status_code, response_body})` |
| `main.py` | `/api/simulate`, `/api/test-feedback`, `/api/calendar/book` | 3 catch blocks: all added `sentry_sdk.capture_exception()`. `/api/calendar/book` was wrapped in new try/except (had none). |

#### Frontend (11 files, 18 catch blocks)

| File | Catch blocks | Fix |
|:---|:---|:---|
| 4 API proxy routes | 4 | `Sentry.captureException()` on catch + `Sentry.captureMessage()` on non-ok responses |
| `TestChatArea.tsx` | 5 | localStorage parse, msg insert, Supabase error, simulate error, bot toggle, sandbox feedback |
| `ChatArea.tsx` | 2 | DB insert error, simulation trigger |
| `AgendaView.tsx` | 2 | fetchEvents, handleBook |
| `TestConfigPanel.tsx` | 2 | fetchTenantConfig, handleSavePrompt |
| `GlobalFeedbackButton.tsx` | 1 | handleSend |
| `admin-feedback/page.tsx` | 1 | handleDelete (was missing try/catch entirely, now wrapped) |
| `auth/confirm/page.tsx` | 1 | Session error → `Sentry.captureMessage()` |

#### Additional Fixes (bundled in same commit)

| Fix | Detail |
|:---|:---|
| **CORS** | `main.py`: replaced `ia-whatsapp-crm.pages.dev` with `ia-whatsapp-crm.tomasgemes.workers.dev` |
| **RLS DELETE** | Supabase migration: `messages_delete_own` + `test_feedback_delete_tenant` policies for `authenticated` |
| **GCal Secret** | `GOOGLE_CALENDAR_CREDENTIALS` v4: re-uploaded as raw JSON (was base64-encoded) |

### Verification — CONFIRMED ✅

- `npm run build` → SUCCESS (0 errors, 19 routes compiled)
- Commit `5ba489d` pushed to `main` → auto-deploy triggered (backend Cloud Build + frontend Workers Builds)
- **User confirmed (2026-04-09):** Chat working, calendar check availability working, appointment booking working, system responding correctly via LLM

---

## Remaining Phases

### Phase 3: Internal E2E Validation — IN PROGRESS 🔄

> **⚠️ SCOPE: This phase is INTERNAL ONLY. No WhatsApp/Meta connection. The system is tested entirely via the simulator (`/api/simulate`), the frontend UI, and direct API calls. WhatsApp integration happens in Phase 5.**

> **⚠️ PREREQUISITE (Preamble): Before ANY E2E testing begins, Sentry must be connected to Discord via OTel/webhooks so that ALL errors — including gracefully handled ones — trigger immediate Discord notifications. This must be done by consulting the official docs FIRST (Sentry Alerts docs, Discord integration docs). The goal is: if ANYTHING goes wrong anywhere in the system, from the smallest caught exception to a full crash, we are notified immediately in Discord. No silent failures.**

**Preamble — Sentry → Discord Real-Time Alerts ✅ COMPLETE (2026-04-09):**

Following the official docs ([Sentry Alerts](https://docs.sentry.io/product/alerts/), [Sentry Discord Integration](https://docs.sentry.io/organization/integrations/notification-incidents/discord/)):

| Step | Result |
|:---|:---|
| Discord integration | ✅ INSTALLED — "StarCompanion's server" (guild `1491131005719810360`), bot has channel access |
| Alert Rule | ✅ CREATED — **"All Issues → Discord (CRM Observability)"** (Rule ID `16897799`) |
| WHEN triggers | "A new issue is created" OR "The issue changes state from resolved to unresolved" |
| THEN actions | 1) Send Discord notification to channel `1491131005719810363` (#general) 2) Send to Suggested Assignees + Active Members |
| Action interval | 5 minutes |
| E2E verification | ✅ Hit `/api/debug-exception` → Captain Hook webhook arrived (manual) + Sentry Bot alert arrived (automatic) |
| Test notification | ✅ "Send Test Notification" from Sentry dashboard → Discord received |

**Two notification channels now active:**
1. **Captain Hook** (manual `discord_notifier.py` webhook) — fires immediately from specific backend code paths (global exception handler, tool errors, pipeline crashes)
2. **Sentry Bot** (official Sentry integration) — fires automatically for ALL new issues and reopened issues captured by `sentry_sdk`

**GCP Project ID:** `saas-javiera` (NOT `tuasistentevirtual` — that's the Sentry org name)  
**Cloud Run Production URL:** `https://ia-backend-prod-ftyhfnvyla-ew.a.run.app`

**Partially tested (user confirmed 2026-04-09):**
- ✅ Dashboard loads
- ✅ Chat loads, real-time messages work
- ✅ Agenda loads with Google Calendar events
- ✅ CheckAvailabilityTool (get_merged_availability) works correctly
- ✅ BookAppointmentTool (book_round_robin) works correctly

**3A: Every CRM Component — Exhaustive UI Verification (8 pages + 2 chat sub-modes):**

The `/chats` route has **two completely separate UI modes** controlled by contact phone:
- **Regular mode** (any contact) → `ChatArea` + `ClientProfilePanel`
- **Test Sandbox mode** (phone `56912345678`) → `TestChatArea` + `TestConfigPanel`

`TestChatArea` features dedicated **action buttons**:
- 🗑️ DESCARTAR PRUEBA — confirm dialog → clears message state
- ✉️ ENVIAR PRUEBA (FINALIZAR) — POST to `/api/test-feedback` → saves chat + notes → clears sandbox → toast
- ✨ CAMBIAR MODELO — placeholder button
- ⚙️ CONFIGURACIÓN — opens `TestConfigPanel`
- ⋯ MÁS OPCIONES — placeholder button
- Inline note system: click AI msg → textarea → "Guardar Nota" → localStorage persistence + yellow dot indicator

`TestConfigPanel` features:
- Realtime-subscribed system prompt editor (loads from `tenants.system_prompt`, saves on "GUARDAR CAMBIOS")
- Bot status badge (EJECUTANDO / EN PAUSA)
- Metrics card (static placeholders)

`/config` (outside (panel) layout) features:
- LLM Provider dropdown (OpenAI / Gemini) -> dynamically changes model list
- LLM Model dropdown (o4-mini, gpt-5-mini, gpt-4o-mini / gemini-3.1-pro-preview, gemini-3.1-flash-lite-preview)
- System prompt textarea with character counter (X / 2000) -- see BUG-2
- Google Calendar connection status + connect/disconnect buttons
- "Solicitar Custom LLM" CTA

**Full page checklist (VERIFIED 2026-04-09):**
- [x] `/dashboard` loads OK
- [x] `/chats` regular mode: contact selection, chat rendering, profile panel, bot toggle, realtime OK
- [x] `/chats` sandbox mode: all 5 action buttons, note system, send/receive flow, spinner OK
- [x] `/chats` sandbox: TestConfigPanel prompt editing, save, realtime sync, bot status OK
- [x] `/agenda` loads with 3 appointments, Box 1/Box 2, occupancy metrics OK
- [x] `/pacientes` loads with 2 contacts, full columns OK
- [x] `/reportes` loads without errors (desktop only) OK
- [x] `/finops` loads without errors (desktop only) OK
- [x] `/admin-feedback` loads, shows test_feedback rows OK
- [x] `/config` LLM config loads, Google Calendar status, prompt editing OK (BUG-2: char counter shows 2000 limit)
- [ ] Cross-cutting: logout (skipped), responsive mobile (not tested)

**3B: Every LLM Tool (PARTIALLY VERIFIED 2026-04-09):**
- [x] CheckAvailabilityTool (get_merged_availability): function call executed OK
- [x] BookAppointmentTool (book_round_robin): function call executed OK
- [x] CheckMyAppointmentsTool (get_my_appointments): function call executed, correct response OK
- [ ] UpdateAppointmentTool (update_appointment): requires existing appointment
- [ ] DeleteAppointmentTool (delete_appointment): requires existing appointment
- [!] EscalateHumanTool (request_human_escalation): **BUG-1** LLM responded in text without calling tool
- [!] UpdatePatientScoringTool (update_patient_scoring): **BUG-1** LLM responded in text without calling tool
- [ ] Each tool failure must appear in Sentry with full traceback + tool context

**3C: Internal E2E Flow (VERIFIED 2026-04-09):**
- [x] Simulator to LLM to tool call to tool execution to response to message persisted to Realtime to frontend OK
- [x] Multi-turn: 6+ messages in sequence, conversation context maintained OK
- [x] Tool chaining: availability check then booking in sequence OK
- [x] Error path: `/api/debug-exception` graceful error + Sentry capture + Discord notification OK

**3D: Observability Verification (VERIFIED 4/5):**
- [x] Intentional error: Sentry event within 30s, Discord notification arrives OK
- [x] Frontend Sentry SDK configured (withSentryConfig in next.config.ts) OK
- [ ] Workers Logs show invocation details in CF dashboard (visual check deferred)
- [x] Cloud Run logs show structured JSON for backend requests OK
- [x] Zero blind spots: 30+ catch blocks instrumented with sentry_sdk.capture_exception OK

**3E: Critical Bug Fixes (must resolve before Phase 4/5):**

> Bugs discovered during Phase 3 testing. Must be fixed before connecting WhatsApp.

BUG-1: LLM Tool-Calling Silent Failure
- Root cause: `tool_choice="auto"` in `openai_adapter.py:29` + no post-LLM validation in `use_cases.py:144-146`
- The LLM can generate text about performing actions without actually calling the tools
- Fix strategy must be researched via official OpenAI Function Calling docs
- See README section 0.6 for complete root cause analysis

BUG-2: Character Counter Limit
- Root cause: Hardcoded `2000` in `Frontend/app/config/page.tsx:160-161`
- Fix: Change to `4000`, threshold rojo > 3500, add Sentry/Discord warning on save if > 4000

---

### Phase 4: Production / Development Environment Separation

> **⚠️ CRITICAL: Before making ANY changes in this phase, audit how ALL systems currently work and where they deploy. The goal is TWO completely independent ecosystems so we can be wild and break stuff in dev without affecting the live user experience in ANY way.**

> **⚠️ DOCS FIRST: Check official docs for Supabase branching/multi-project, Cloud Run multi-service, and Cloudflare Workers multi-environment BEFORE implementing anything.**

**Current Infrastructure (must be respected and not broken):**
- **Database:** TWO separate Supabase projects — production (`nemrjlimrnrusodivtoa`) and development (`nzsksjczswndjjbctasu`). Already exist and must remain independent.
- **Backend:** Cloud Run service `ia-backend-prod` in `europe-west1`, project `saas-javiera`. Auto-deploys from `main` via Cloud Build trigger.
- **Frontend:** Cloudflare Worker `ia-whatsapp-crm`. Auto-deploys from `main` via Workers Builds.

### Phase 4: Production / Development Environment Separation — COMPLETE ✅ (2026-04-10)

**Two fully independent ecosystems established:**

| Component | Production | Development |
|:---|:---|:---|
| **Backend** | `ia-backend-prod` (europe-west1) | `ia-backend-dev` (us-central1) |
| **Frontend** | `ia-whatsapp-crm` (CF Worker) | `dev-ia-whatsapp-crm` (CF Worker) |
| **Database** | `nemrjlimrnrusodivtoa` (Supabase) | `nzsksjczswndjjbctasu` (Supabase) |
| **Domain** | `dash.tuasistentevirtual.cl` | `ohno.tuasistentevirtual.cl` |
| **Branch** | `main` | `desarrollo` |
| **Sentry tag** | `environment=production` | `environment=development` |
| **Discord prefix** | (none) | `[🔧 DESARROLLO]` |
| **Calendar** | ✅ Connected (CasaVitaCure SA) | ❌ Intentionally disconnected (safety) |

**Key secrets:**
- `SUPABASE_SERVICE_ROLE_KEY` → prod only (nemrjlimrnrusodivtoa)
- `SUPABASE_SERVICE_ROLE_KEY_DEV` → dev only (nzsksjczswndjjbctasu)
- `GOOGLE_CALENDAR_CREDENTIALS` → prod only (CasaVitaCure SA — NOT safe for dev)

**Known limitation:** Calendar/Agenda features don't work in dev. The Google Calendar credentials belong to the client (CasaVitaCure) and connecting them to dev would risk test operations corrupting the live calendar. This is documented as Phase 6+ backlog: "Calendar Multi-Tenant Architecture Refactor".

**Schema sync strategy:** PR `desarrollo` → `main`. Auto-deploy fires for backend (Cloud Build) and frontend (Workers Builds). DB migrations applied manually via Supabase MCP to prod after verification on dev.

---

### Phase 5: Meta/WhatsApp Integration + Go-Live

> **⚠️ This phase ONLY begins after Phase 4 is complete and there is guaranteed isolation between prod and dev environments.**

> **⚠️ The WhatsApp webhook connection is the LAST step, not the first. Before connecting Meta, we must have a fully instrumented, thoroughly tested webhook simulation suite.**

**5A: Meta Webhook Simulation Suite ✅ COMPLETED (2026-04-10):**

Architecture decision: **HTTP runner → `POST /webhook`** (not direct function call). Rationale: tests the real FastAPI routing, dependency injection, payload parsing, and BackgroundTasks scheduling — identical to what Meta sends in production. The runner is re-targetable: works against `localhost:8000` or the deployed dev backend. Ref: [Meta Webhook Reference](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components/), [Meta Payload Examples](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples)

Scripts created in `Backend/scripts/simulation/`:
- [x] `payload_factory.py` — Meta-compliant payloads: text, status, image, location, reaction, malformed, edge cases
- [x] `scenarios.py` — 9 scenarios covering happy path, tool triggers, clinical escalation, status webhooks, malformed payloads, burst, concurrent, and edge cases
- [x] `runner.py` — CLI orchestrator with sequential/burst/concurrent modes, markdown report generation
- [x] `cleanup.py` — Dev DB cleanup with production safety guard + dry-run mode
- [x] `switch_env.py` — `.env` switcher (dev ↔ prod) for `SUPABASE_URL` and `ENVIRONMENT`

Observability hardening (5A-OBS) — audited all `except` blocks in the critical pipeline:
- [x] `dependencies.py` — Added Sentry + Discord (had neither before)
- [x] `tool_registry.py` — Added Discord alerts (had Sentry only)
- [x] `gemini_adapter.py` — Added Sentry + Discord (had neither before)
- [x] `openai_adapter.py` — Added Discord alerts (had Sentry only)
- [x] `use_cases.py` — Added Discord to msg persistence error + processing lock cleanup error

Results: **9/9 scenarios passed** against local dev backend (2026-04-10). DB verification confirmed: 12 contacts created, escalation contacts correctly have `bot_active=false`, zero stuck processing locks.

**5B: Version Tag + Final Production Deploy:**
- [ ] Merge observability hardening changes to `main` branch
- [ ] Deploy to production via Cloud Build auto-deploy
- [ ] Run simulation suite against deployed dev backend (cloud verification)
- [ ] Once clean: `git tag v1.0` on `main`, `git push origin main --tags`
- [ ] Verify: production frontend and backend running the v1.0 code

**5C: Connect Meta/WhatsApp (LIVE):**

> **System User token required** — the current token is expired (401 in Sentry). A System User must be created in Meta Business Manager with `whatsapp_business_messaging` + `whatsapp_business_management` permissions. Ref: [Meta System Users](https://developers.facebook.com/docs/marketing-api/system-users/)

> **AI Chatbot Policy compliance** — Meta prohibits "general-purpose" AI chatbots (Jan 2026 policy). CasaVitaCure is compliant as a task-specific assistant (booking, scoring, escalation). No Tech Provider status needed for first client.

- [ ] Create System User → generate permanent access token
- [ ] Update `ws_token` in production Supabase `tenants` table
- [ ] Update `ws_phone_id` to match real Meta `phone_number_id` (currently placeholder `123456789012345`)
- [ ] Configure webhook URL in Meta Dashboard → `ia-backend-prod-ftyhfnvyla-ew.a.run.app/webhook`
- [ ] Verify webhook verification handshake (GET /webhook with verify_token)
- [ ] Send a real WhatsApp message → confirm full pipeline:
  - [ ] Message received by webhook
  - [ ] LLM inference completes
  - [ ] Response sent back via Meta API
  - [ ] Message appears in frontend CRM chat in real time
  - [ ] Sentry shows clean trace (no errors)
  - [ ] No Discord error notifications (clean run)

**5D: Production Validation — System 100% Operational:**
- [ ] Multiple real WhatsApp conversations tested
- [ ] Calendar booking tested end-to-end (WhatsApp → LLM → GCal API → confirmation message)
- [ ] Escalation tested (user requests human → bot paused → alert in CRM + Discord)
- [ ] Sentry dashboard clean — no unexpected errors
- [ ] Discord alerts only fire for legitimate issues
- [ ] System declared production-ready 🚀
