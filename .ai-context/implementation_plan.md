# AI CRM Production Stabilization — Implementation Plan

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por docs oficiales actualizados. Leer docs PRIMERO, implementar DESPUÉS. Sin excepciones.

> **⚠️ LEY POST-IMPLEMENTACIÓN:** Toda solución confirmada como funcional DEBE ser documentada EN ESE MOMENTO con: (1) qué se hizo, (2) por qué funciona, (3) links a los docs oficiales que lo respaldan. Esto previene que futuras sesiones de LLM rompan lo que ya funciona por desconocimiento.

> **⚠️ LEY DE DOCUMENTACIÓN (v5 — 2026-04-11):** Todos los Deep Dives v3 contienen **60+ URLs de documentación oficial exacta**. Cada paso de ejecución tiene su link. **CONSULTAR antes de implementar.**
> - [Deep Dive A v3 — Response Quality](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) — 11+ OpenAI doc URLs
> - [Deep Dive B v3 — Multi-Channel](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md) — 15+ Meta/WhatsApp doc URLs
> - [Deep Dive C v3 — Dashboard + Observability](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md) — 15+ Infrastructure doc URLs
> - [Master Plan v5](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/master_plan.md) — Corrected financials, model decision

## Status: Phase 0-5C COMPLETE ✅ | Phase 5D IN PROGRESS 🔴 | Sprint 1 PLANNED ⭐

> [!CAUTION]
> **CRITICAL CORRECTIONS (2026-04-11 v5 Research):**
> 1. **Codebase uses DEPRECATED `gpt-4o-mini`** in 3 files — must change to `gpt-5.4-mini` or `gpt-5.4-nano` ASAP
> 2. **Pricing was WRONG** — `gpt-5.4-mini` is $0.75/$4.50/1M, NOT $0.25/$2.00. Margins: 73% not 80% at 7 tenants
> 3. **BSUID already active** in webhooks (April 2026) — add `bsuid` column to contacts
> 4. **Graph API v19.0 DEPRECATED May 21, 2026** — update to v25.0 in `meta_graph_api.py`
> 5. **Tool schemas lack `strict: true`** — LLM can hallucinate parameters

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
- ✅ Phase 3: E2E Validation — COMPLETE (3A-3F all done, BUGs 1-3 resolved, see README §0.6)
- ✅ Phase 4: Prod/Dev Separation — COMPLETE (2 ecosystems, calendar excluded by design)
- ✅ Phase 5A: Simulation Suite — COMPLETE (9/9 scenarios, see README §0.8)
- ✅ Phase 5B: Version Tag — `v1.0`, rev `00074-jx4`
- ✅ Phase 5C: Meta/WhatsApp LIVE — Webhook verified, System User token, E2E confirmed
- 🔴 Phase 5D: Production Validation — IN PROGRESS, critical issues found (BUG-5, BUG-6, see §0.9)

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

### Phase 3: Internal E2E Validation — COMPLETE ✅

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
**Cloud Run Production URL:** `https://ia-backend-prod-645489345350.us-central1.run.app` (migrated from europe-west1 on 2026-04-11)

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
- LLM Model dropdown (gpt-5.4-mini [Recomendado], gpt-5.4-nano [Económico] / gemini-3.1-pro-preview, gemini-3.1-flash-lite-preview)
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

**5B: Version Tag + Final Production Deploy ✅ COMPLETED (2026-04-10):**

- [x] Merge observability hardening changes to `main` branch
  - Commit `8d95ec2`: `fix(5a-obs): hardened observability` (5 files)
  - Commit `f0da91b`: `feat(phase5a): Meta webhook simulation suite + docs update`
- [x] Deploy to production via Cloud Build auto-deploy
  - Revision `ia-backend-prod-00074-jx4` — deployed `13:14:42 UTC`, startup clean, zero errors
  - `gemini_adapter.py:9` FutureWarning confirms updated code is live
- [x] `git tag v1.0` on `main` → `git push origin v1.0`
- [x] Production verified: `ia-backend-prod-ftyhfnvyla-ew.a.run.app` serving revision 00074

**5C: Connect Meta/WhatsApp (LIVE) — ✅ COMPLETED (2026-04-10 ~14:45 UTC):**

> **All steps below were successfully executed.** Webhook verified, messages flowing E2E, System User permanent token installed. See task.md for detailed execution log.

> ⚠️ IMPORTANT: No code changes needed. This is 100% manual configuration in Meta's web UIs + one SQL query in Supabase.

> **AI Chatbot Policy compliance** — Meta prohibits "general-purpose" AI chatbots (Jan 2026 policy). CasaVitaCure is compliant as a task-specific assistant (booking, scoring, escalation). No Tech Provider / Solution Partner status needed for first client. Ref: [Meta AI Chatbot Policy](https://developers.facebook.com/docs/whatsapp/overview/ai-chatbot-policy)

> **Your backend is already fully configured.** The webhook handler, payload parser, LLM pipeline, and reply sender are all deployed and verified. You only need to give Meta the right URL and give the backend the right token.

---

#### PREREQUISITE CHECKLIST — Before Starting

Before you touch anything:

- [ ] **You have a Meta Business account** (the one that owns the CasaVitaCure WhatsApp number). If you don't, go to [business.facebook.com](https://business.facebook.com/) and create one.
- [ ] **You have a Meta Developer account** and an App already created. If you don't, go to [developers.facebook.com](https://developers.facebook.com/), click **My Apps → Create App**, select **Business**, and add the **WhatsApp** product.
- [ ] **Business Verification is complete.** Go to [business.facebook.com/settings/](https://business.facebook.com/settings/) → left sidebar → **Business Info** (or **Security Center**) → check that verification status is ✅. If not, you need to complete this first (takes 1-5 business days). You need a verified business to go live.
- [ ] **Privacy Policy URL and Terms of Service URL** are set in your Meta App. Go to [developers.facebook.com](https://developers.facebook.com/) → Your App → **Settings → Basic** → fill in both URLs. Without these, you cannot switch to Live Mode.
- [ ] **App is in Live Mode**, NOT Development Mode. At the top of your App Dashboard, there's a toggle showing "Development" or "Live". If it says "Development", toggle it to **Live**. In Development mode, webhooks only work for registered test numbers.

---

#### STEP 1 — Create a System User in Meta Business Manager

**WHY:** The temporary tokens Meta gives you expire in ~24 hours. A System User generates a permanent, never-expiring token.

**WHERE TO GO:**

🔗 **URL:** [https://business.facebook.com/settings/](https://business.facebook.com/settings/)

If that URL doesn't work (Meta loves moving things), try these alternatives:
- [https://business.facebook.com/settings/system-users](https://business.facebook.com/settings/system-users)
- Go to [business.facebook.com](https://business.facebook.com/) → click the ⚙️ **gear icon** (bottom-left sidebar) → **Business Settings**

**WHAT TO DO:**

1. **Make sure you're in the right business account.** Look at the top-left corner — it should show your business name (the one that owns the CasaVitaCure WABA). If you have multiple businesses, click the dropdown and switch.

2. **Find "System Users"** in the left sidebar. Look for:
   - **Users** → **System users**
   - OR it might be under **People and assets** → **System users**
   - OR search for "system users" if there's a search bar

3. **Click the blue "Add" button** (top-right area)

4. **Fill in the popup:**
   - **System user name:** `javiera-crm-bot` (or whatever you want — this is just a label)
   - **System user role:** Select **Admin** (NOT Employee — Employee doesn't have enough permissions)
   - Click **Create system user**

5. **Verify it appeared in the list.** You should see `javiera-crm-bot` listed with role "Admin".

---

#### STEP 2 — Assign Assets to the System User

**WHY:** The system user needs permission to access your WhatsApp app AND your WhatsApp Business Account. Without both, the token won't work.

**STILL ON THE SAME PAGE** (business.facebook.com/settings → System Users)

1. **Click on `javiera-crm-bot`** in the list (select the row)

2. **Click "Assign assets"** button (it may say "Add Assets" instead)

3. **A dialog appears with tabs at the top.** You need to do TWO assignments:

   **Assignment A — The App:**
   - Click the **"Apps"** tab
   - You'll see a list of your Meta apps. Find your WhatsApp Business app (the one you created in developers.facebook.com)
   - Click on it to select it
   - On the right side, a permission toggle appears. **Toggle ON "Full control"** (or "Manage app")
   - Click **Save Changes** (or if there's no save, the toggle auto-saves — but look for a save button)

   **Assignment B — The WhatsApp Business Account (WABA):**
   - Click the **"WhatsApp accounts"** tab (it might just say "WhatsApp")
   - You'll see your WhatsApp Business Account listed (the one tied to CasaVitaCure's phone number)
   - Click on it to select it
   - On the right side, **toggle ON "Full control"** (or "Manage WhatsApp Business Account")
   - Click **Save Changes**

4. **Verify:** After saving, when you click on `javiera-crm-bot`, you should see two assigned assets: one App and one WhatsApp account, both with "Full control".

---

#### STEP 3 — Generate a Permanent Access Token

**STILL ON THE SAME PAGE** (business.facebook.com/settings → System Users → javiera-crm-bot selected)

1. **Click "Generate new token"** button (should be visible when the system user is selected — might be on the right side or as a blue button at the top)

2. **A dialog appears. Fill it in CAREFULLY:**

   - **App:** Select your WhatsApp Business app from the dropdown (the same one you assigned in Step 2A)

   - **Token expiration:** Select **"Never"** (this makes it permanent). If you don't see "Never", select the longest duration available and set a calendar reminder to renew it.

   - **Permissions:** You need to scroll through a list of checkboxes and check **exactly these three**:

     ☑️ `whatsapp_business_messaging` — this is what lets the token SEND messages via the WhatsApp Cloud API

     ☑️ `whatsapp_business_management` — this lets the token manage phone numbers, templates, etc.

     ☑️ `business_management` — this is a prerequisite for the other two

     > **⚠️ If you can't find these permissions:** Scroll down! There are usually 50+ permissions listed alphabetically. `business_management` starts with B, `whatsapp_*` are at the very bottom of the list near W. Use Ctrl+F in your browser to search if needed.

3. **Click "Generate token"**

4. **🚨🚨🚨 A popup shows your token. THIS IS THE ONLY TIME YOU WILL SEE IT. 🚨🚨🚨**
   - The token looks like a very long string (200+ characters), starts with `EAA...`
   - **Copy it RIGHT NOW.** Ctrl+C or click the copy icon
   - **Paste it into your password manager, a secure note, or a text file immediately**
   - DO NOT close this dialog until you've confirmed you have the token saved
   - If you lose this token, you'll have to generate a new one (the old one is gone forever)

5. **Verify your token starts with `EAA` and is over 150 characters long.** If it's short (like 20 chars), something went wrong.

---

#### STEP 4 — Find Your Phone Number ID

**WHY:** The backend uses the Phone Number ID (NOT the phone number itself) to route incoming messages to the right tenant. The current value in the database is `123456789012345` — a placeholder that needs to be replaced with the real one.

**WHERE TO GO:**

🔗 **URL:** [https://developers.facebook.com/apps/](https://developers.facebook.com/apps/)

**WHAT TO DO:**

1. **Click on your WhatsApp Business app** in the list

2. **In the left sidebar, look for "WhatsApp" section** and click **"API Setup"**
   - If you don't see "API Setup", try: **WhatsApp → Getting Started** or **WhatsApp → Quickstart**
   - Alternative path: **Use Cases** (left sidebar) → click **Customize** on the WhatsApp use case → **API Setup**

3. **Look for a section called "Send and receive messages"** or **"From"** or **"Phone numbers"**
   - You'll see your registered business phone number (the CasaVitaCure number)
   - **Right below or next to the phone number**, there's a field called **Phone Number ID**
   - It's a long numeric string like `375028372012345`

4. **Copy the Phone Number ID.** This is NOT the same as the phone number.

   **How to tell them apart:**
   - Phone number: `+56 9 1234 5678` (has country code, may have spaces/dashes)
   - Phone Number ID: `375028372012345` (just digits, no + or spaces, usually 15 digits)

**ALTERNATIVE — If you can't find it in the App Dashboard:**

🔗 Try [https://business.facebook.com/wa/manage/phone-numbers/](https://business.facebook.com/wa/manage/phone-numbers/)

This is the WhatsApp Manager. Click on your phone number and the Phone Number ID should be shown in the details.

---

#### STEP 5 — Update the Production Database (Supabase)

**WHY:** Your backend reads `ws_token` and `ws_phone_id` from the Supabase `tenants` table at runtime. You need to replace the placeholders with the real values from Steps 3 and 4.

**WHERE TO GO:**

🔗 **URL:** [https://supabase.com/dashboard/project/nemrjlimrnrusodivtoa/sql/new](https://supabase.com/dashboard/project/nemrjlimrnrusodivtoa/sql/new)

(That's the SQL Editor for the PRODUCTION Supabase project)

If that URL doesn't work, go to [supabase.com/dashboard](https://supabase.com/dashboard) → click on the production project (the one that says `nemrjlimrnrusodivtoa`) → click **SQL Editor** in the left sidebar → click **New query**

**WHAT TO DO:**

1. **Paste this SQL** (replace the two placeholder values with YOUR real values from Steps 3 and 4):

```sql
UPDATE tenants
SET
  ws_token = 'EAAxxxxxxxx_PASTE_YOUR_ENTIRE_TOKEN_HERE_xxxxxxxx',
  ws_phone_id = '375028372012345'
WHERE name = 'CasaVitaCure';
```

> **⚠️ CAREFUL:** Make sure you paste the ENTIRE token between the single quotes. No leading/trailing spaces. The token is usually 200+ characters, so it will be a very long line — that's normal.

2. **Click "Run"** (or press Ctrl+Enter)

3. **Verify it worked.** Run this query:

```sql
SELECT name, ws_phone_id, LENGTH(ws_token) as token_length,
       SUBSTRING(ws_token, 1, 10) as token_preview
FROM tenants
WHERE name = 'CasaVitaCure';
```

**Expected result:**
| name | ws_phone_id | token_length | token_preview |
|---|---|---|---|
| CasaVitaCure | 375028372012345 | 200+ | EAAxxxxxx |

If `token_length` is less than 100, the token didn't copy correctly. Redo it.

---

#### STEP 6 — Find Your WHATSAPP_VERIFY_TOKEN

**WHY:** When you configure the webhook in Meta's dashboard (next step), Meta asks for a "Verify Token". This must match EXACTLY what your backend expects. Your backend reads it from the `WHATSAPP_VERIFY_TOKEN` environment variable in Cloud Run.

**WHERE TO GO:**

🔗 **URL:** [https://console.cloud.google.com/run/detail/europe-west1/ia-backend-prod/revisions?project=saas-javiera](https://console.cloud.google.com/run/detail/europe-west1/ia-backend-prod/revisions?project=saas-javiera)

If that doesn't work: Go to [console.cloud.google.com](https://console.cloud.google.com/) → select project **saas-javiera** → side menu → **Cloud Run** → click **ia-backend-prod**

**WHAT TO DO:**

1. Click on the **latest revision** (should be `ia-backend-prod-00074-jx4` or newer)
2. Click the **"Edit & Deploy New Revision"** button (or look for a tab called "Variables" or "Environment Variables")
3. Scroll through the list of environment variables
4. Find **`WHATSAPP_VERIFY_TOKEN`** — copy its value exactly (case-sensitive, no extra spaces)
5. **You'll need this value in the next step.** Paste it somewhere accessible (clipboard, notepad)

> **⚠️ Don't change this value!** Just read it. If you change it here, you'd also need to change it in Meta's dashboard, and vice versa. They must match.

---

#### STEP 7 — Configure the Webhook URL in Meta

**WHY:** This tells Meta WHERE to send incoming WhatsApp messages. Right now, Meta doesn't know about your server. After this step, every WhatsApp message to CasaVitaCure's number will be forwarded to your backend.

**WHERE TO GO:**

🔗 **URL:** [https://developers.facebook.com/apps/](https://developers.facebook.com/apps/) → click your app

**WHAT TO DO:**

1. **In the left sidebar**, click **WhatsApp → Configuration**
   - If you don't see "Configuration", try: **WhatsApp → Getting Started** and look for a webhook section
   - Alternative path: **Use Cases** → **Customize** → **Configuration**

2. **Find the "Webhook" section** on the page. There should be a subsection with fields for Callback URL and Verify Token, with an **"Edit"** button.

3. **Click "Edit"** (or "Configure" if it says that instead)

4. **Fill in EXACTLY these values:**

   | Field | What to type |
   |---|---|
   | **Callback URL** | `https://ia-backend-prod-645489345350.us-central1.run.app/webhook` |
   | **Verify Token** | *(paste the WHATSAPP_VERIFY_TOKEN value from Step 6)* |

   > **⚠️ TRIPLE CHECK the Callback URL:** It must be EXACTLY `https://ia-backend-prod-645489345350.us-central1.run.app/webhook` — no trailing slash, no `/api/` prefix, and it's `https` not `http`.

5. **Click "Verify and Save"**

   **What happens behind the scenes:** Meta sends a GET request to your URL with the verify token. Your backend (the code in `security.py`) checks if the token matches and returns a challenge number. If everything matches, Meta confirms the webhook.

6. **Check the result:**
   - ✅ **Green checkmark / "Verified"** = SUCCESS! Move to Step 8.
   - ❌ **Error / "Verification failed"** = Something is wrong. See troubleshooting below.

   **Troubleshooting verification failures:**
   - **"URL could not be validated"** → Your backend might be down. Check Cloud Run logs.
   - **"Verification failed"** → The verify token doesn't match. Double-check Step 6 — copy the value again, make sure there are no invisible spaces.
   - **Other error** → Check Cloud Run logs for a `WARNING: WhatsApp Webhook verification failed` entry. This means the request reached your server but the token didn't match.

---

#### STEP 8 — Subscribe to Webhook Events

**WHY:** Verifying the webhook only sets up the connection. You also need to tell Meta WHICH events to send you. Without subscribing to `messages`, you'll never receive incoming WhatsApp messages.

**STILL ON THE SAME PAGE** (developers.facebook.com → Your App → WhatsApp → Configuration)

1. **Look for "Webhook fields"** section (usually right below where you just configured the webhook URL)

2. **Click "Manage"** (or "Subscribe" or "Edit")

3. **A list of event types appears.** Find and **subscribe** to:

   - **`messages`** → Toggle this ON / click Subscribe ✅
     - This is the critical one — it sends you incoming user messages

4. **Optionally subscribe to:**
   - **`message_status`** → delivery/read receipts. Currently the backend handles these gracefully (skips LLM call, just acknowledges). Useful for debugging.

5. **Click "Done"** or just close the modal — subscriptions are usually saved immediately when you toggle them.

---

#### STEP 9 — Send a Test Message & Verify EVERYTHING Works

**This is the moment of truth. 🎉**

1. **Open WhatsApp on your phone** (personal account is fine)

2. **Send a message to the CasaVitaCure WhatsApp number** — something simple like:

   > "Hola, me gustaría saber sobre sus servicios"

3. **Wait 2-10 seconds.** The AI should respond via WhatsApp.

4. **While waiting, monitor these (open all of them in separate tabs):**

   | What to check | Where | What you should see |
   |---|---|---|
   | **Cloud Run Logs** | [GCP Console → Cloud Run → ia-backend-prod → Logs](https://console.cloud.google.com/run/detail/europe-west1/ia-backend-prod/logs?project=saas-javiera) | `POST /webhook` → Status 200 |
   | **Sentry** | Your Sentry dashboard | **No new errors** (clean) |
   | **Discord** | Your alerts channel | **No new alerts** (clean) |
   | **CRM Frontend** | [https://dash.tuasistentevirtual.cl](https://dash.tuasistentevirtual.cl) | New chat appears in the conversations list |
   | **Supabase contacts** | [Production Supabase → Table Editor → contacts](https://supabase.com/dashboard/project/nemrjlimrnrusodivtoa/editor) | New row with `bot_active=true` |
   | **Supabase messages** | Same → messages table | Two new rows: user message + AI response |

5. **If the AI responded on WhatsApp → 🎉 YOU'RE DONE. IT WORKS.**

---

#### TROUBLESHOOTING — If Something Goes Wrong

| Symptom | Cause | Fix |
|---|---|---|
| No webhook received at all (empty Cloud Run logs) | Webhook not configured or app in Development mode | Redo Step 7, and make sure app is in **Live** mode (toggle at top of App Dashboard) |
| Webhook received but `Tenant Not Found` in Discord/Sentry | `ws_phone_id` in Supabase doesn't match Meta's Phone Number ID | Redo Step 5 — double-check the Phone Number ID from Step 4 |
| Webhook received, LLM responds, but WhatsApp message never arrives | `ws_token` is wrong or permissions are missing | Redo Step 3 — verify all 3 permissions were checked |
| WhatsApp shows "This message failed to send" | Token expired or Meta rate limit | Check Sentry for 401 errors. Regenerate token if needed. |
| Cloud Run logs show `403 Verification failed` | Verify token mismatch | Redo Step 6+7 — the token in Meta Dashboard must match the env var exactly |
| Everything works but CRM frontend doesn't show the chat | Frontend issue, not a Meta issue | Check browser console for errors; verify Supabase realtime is enabled |
| AI responds but response is weird/empty | System prompt issue or LLM error | Check Sentry for LLM-related errors |

**5D: Production Validation — 🔴 CRITICAL ISSUES FOUND:**

**What has been verified ✅:**
- [x] Webhook handshake with Meta (GET /webhook → 200, challenge returned)
- [x] Inbound messages from real WhatsApp number (`56931374341`) reach backend
- [x] LLM (OpenAI) generates contextual responses following system prompt
- [x] Outbound messages sent via Meta Graph API reach user's WhatsApp
- [x] Messages persisted in Supabase (contacts + messages tables, 10+ messages verified)
- [x] Conversation appears in CRM frontend dashboard
- [x] Sentry telemetry active (events captured correctly)
- [x] System User permanent token installed (never-expiring)
- [x] Direct Meta Graph API test call returned `200` with `wa_id` confirmation

**Critical issues found in live testing 🔴:**
- [ ] **BUG-6: Response Quality**: 7 root causes diagnosed. Fix spec: [Deep Dive A v3](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md). Key docs: [Function Calling](https://platform.openai.com/docs/guides/function-calling), [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs).
- [ ] **BUG-5: Silent Failure Detector**: 95%+ false positives. **Decisión: Desactivar completamente.**
- [ ] **Escalation workflow**: NON-FUNCTIONAL in practice. Missing: chat highlighting, tracking, notifications, staff UX.
- [ ] **Scoring/Customer Intelligence**: `UpdatePatientScoringTool` never worked. Full CIS needed.

**Critical Corrections (v5 Research) 🔴:**
- [ ] **CC-1:** Model string `gpt-4o-mini` DEPRECATED in 3 files. Change to `gpt-5.4-mini`. [Models](https://platform.openai.com/docs/models)
- [ ] **CC-3:** BSUID dormant capture (Phase 1): add `bsuid` column, extract `user_id`, store + backfill. Phase 2 (lookup swap) before June 2026. [Deep Dive B §1](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md)
- [ ] **CC-4:** Graph API `v19.0` → `v25.0`. Deprecated May 21. [Changelog](https://developers.facebook.com/docs/graph-api/changelog)
- [ ] **CC-5:** Add `strict: true` to all tool schemas. [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

**Still pending 🟡:**
- [ ] API Version Update: Code uses Graph API `v19.0`, Meta latest is `v25.0`. [Changelog](https://developers.facebook.com/docs/graph-api/changelog)
- [ ] Publish App to Live Mode: App currently in Development mode. [App Review](https://developers.facebook.com/docs/app-review)
- [ ] Calendar booking E2E via real WhatsApp conversation
- [ ] Sentry cleanup: resolve/dismiss false positive warnings
- [ ] System declared production-ready 🚀 (Resilient MVP)

---

## Sprint 1: Emergency Stabilization (Apr 12-15, 2026) — REVISED v2

> **⭐ ACTIVE SPRINT.** Goal: Fix BUG-6 + BUG-5, add resilience layer, onboard 2nd tenant.
> **Strategy (user-approved):** Deploy quick wins FIRST. Dashboard MVP → Sprint 2. Time → prompts + resilience.
> **Model decision: `gpt-5.4-mini`** for PROD, `gpt-5.4-nano` for dev/budget (both API-compatible).
> **Full execution plan with per-step doc links:** See [task.md §Sprint 1](file:///d:/WebDev/IA/.ai-context/task.md).
> **Deep Dives with 60+ doc URLs:** See `.ai-context/deep_dive_a|b|c*.md` (v3, fully cited).

> [!CAUTION]
> **MANDATORY:** Before implementing ANY block below, the implementing agent MUST open and review ALL linked documentation for that block. Every URL exists because it contains information critical to correct implementation. Skipping doc review = guaranteed implementation errors.

### Day-by-Day Overview (REVISED)

| Day | Focus | Key Docs | Key Changes from v1 |
|:---|:---|:---|:---|
| **Sat Apr 12** | Block A → **DEPLOY IMMEDIATELY** → Blocks B-H | [Function Calling](https://platform.openai.com/docs/guides/function-calling), [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs), [Chat API](https://platform.openai.com/docs/api-reference/chat/create), [Models](https://platform.openai.com/docs/models), [Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching), [asgi-correlation-id](https://github.com/snok/asgi-correlation-id), [Meta Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started), [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), [Graph API Changelog](https://developers.facebook.com/docs/graph-api/changelog), [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/), [Cloud Run Memory](https://cloud.google.com/run/docs/configuring/memory-limits) | Added: resilience layer (6 tasks in Block E) |
| **Sun Apr 13** | System prompts (3-4h), Escalation UX, Provisioning script | [Supabase Python Client](https://supabase.com/docs/guides/getting-started/quickstarts/python), [Next.js 15](https://nextjs.org/docs) | **REPLACED:** Dashboard MVP → prompt quality + provisioning script |
| **Mon Apr 14** | Tenant #2 via script, E2E testing, Meta audit | [Phone Number Management](https://developers.facebook.com/docs/whatsapp/business-management-api/manage-phone-numbers), [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), [Meta Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started) | Added: Meta audit, shadow-forward verification |
| **Tue Apr 15** | Onboarding 🚀, monitor, post-onboarding | [Meta App Review](https://developers.facebook.com/docs/app-review), [Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching), [Message Templates](https://developers.facebook.com/docs/whatsapp/message-templates) | Added: rescue template, prompt refinement with client |

### Execution Blocks (Blocks A-Q)

> [!IMPORTANT]
> **Each block's "Key Docs" column lists ALL official documentation that MUST be reviewed before starting that block.** The implementing agent MUST open each URL and confirm understanding before writing any code. This is non-negotiable.

| Block | Task | Est. | Day | Key Docs (MUST review before implementing) |
|:---|:---|:---|:---|:---|
| **A** | Quick wins + cost cap + **DEPLOY** | 30 min | Sat AM | [OpenAI Models](https://platform.openai.com/docs/models), [Graph API Changelog](https://developers.facebook.com/docs/graph-api/changelog), [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create) |
| B | `strict: true` tool schemas (all 7 tools) | 1 hr | Sat | [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) §"Supported schemas", [Deep Dive A §3](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) |
| C | Adapter: preserve text + usage tracking | 30 min | Sat | [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create) (response/usage objects), [Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) |
| **D** | **Agentic loop rewrite** (role:tool, multi-round, parallel) | **3-5 hr** | Sat | [Function Calling](https://platform.openai.com/docs/guides/function-calling) §"Multi-turn" **CRITICAL**, [Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create), [Deep Dive A §3 Phase 4](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) |
| **E** | **Resilience: webhook sig, rate limit, lock TTL, shadow-forward, health, cache** | **90 min** | Sat | [Meta Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests), [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), [WhatsApp Send Message](https://developers.facebook.com/docs/whatsapp/cloud-api/messages/text-messages), [Cloud Run Memory](https://cloud.google.com/run/docs/configuring/memory-limits), [cachetools](https://pypi.org/project/cachetools/) |
| F | Observability: correlation IDs + Sentry tags + logging | 30 min | Sat | [asgi-correlation-id](https://github.com/snok/asgi-correlation-id), [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/), [Deep Dive C §3](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md) |
| G | BSUID Dormant Capture (Phase 1): DB migration + webhook extract + store + backfill | 20 min | Sat | [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) (BSUID format), [Deep Dive B §1](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md), [BSUID Forensic](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/bsuid_full_forensic.md) |
| H | Test & deploy Day 1 | 30 min | Sat PM | — |
| **I** | **System prompt engineering** (CasaVitaCure + fumigation draft) | **3-4 hr** | Sun | [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering), [Function Calling](https://platform.openai.com/docs/guides/function-calling) |
| J | Escalation UX minimal | 2 hr | Sun | [Next.js 15](https://nextjs.org/docs) |
| K | Tenant provisioning script | 1 hr | Sun | [Supabase Python Client](https://supabase.com/docs/guides/getting-started/quickstarts/python) |
| L | Simple status page (replaces Dashboard MVP) | 30 min | Sun | [Supabase Python Client](https://supabase.com/docs/guides/getting-started/quickstarts/python) |
| M | Fumigation tenant setup | 2 hr | Mon | [Phone Number Management](https://developers.facebook.com/docs/whatsapp/business-management-api/manage-phone-numbers), [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks) |
| N | Full E2E testing | 3 hr | Mon | All above — integration verification |
| O | Meta audit (permissions, webhooks, token, mTLS) | 30 min | Mon | [Meta Webhook Security](https://developers.facebook.com/docs/graph-api/webhooks/getting-started), [WhatsApp Business Management](https://developers.facebook.com/docs/whatsapp/business-management-api) |
| P | Go-live 🚀 | — | Tue | [Meta App Review](https://developers.facebook.com/docs/app-review) |
| Q | Post-onboarding: prompt refinement + rescue template | 1 hr | Tue PM | [Message Templates](https://developers.facebook.com/docs/whatsapp/message-templates), [Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) |

### Deferred to Sprint 2

| Item | Sprint 2 Priority |
|:---|:---|
| Dashboard MVP (Blocks 1-2) | 🔴 First thing Sprint 2 |
| Instagram DM | 🔴 SELLING POINT |
| Multi-squad booking | 🔴 SELLING POINT |
| `gpt-5.4-nano` dev testing | 🟡 After mini stable |

**Detailed task breakdown with per-step doc links:** See [task.md §Sprint 1](file:///d:/WebDev/IA/.ai-context/task.md).



