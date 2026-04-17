# AI WhatsApp CRM — Technical Documentation

> **SaaS Multi-tenant B2B** — Automates first-line customer service via WhatsApp using LLMs with Function Calling, under a Human-In-The-Loop (HITL) paradigm.

> **⚠️ RULE #1 — DOCS FIRST:** Before implementing ANY change, fix, or integration, consult the latest official documentation of the relevant service (Supabase, Cloudflare, Google Cloud, Sentry, Meta, OpenAI). APIs change between versions. Violating this rule has cost hours of unnecessary debugging (see postmortems in `deep_dives_&_misc/`).

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Architecture](#2-architecture)
3. [Repository Structure](#3-repository-structure)
4. [Data Model](#4-data-model)
5. [Infrastructure & Deployment](#5-infrastructure--deployment)
6. [Critical Rules — Anti-Regression](#6-critical-rules--anti-regression)
7. [Environment Variables](#7-environment-variables)
8. [Design Patterns](#8-design-patterns)
9. [Dependencies](#9-dependencies)
10. [Roadmap](#10-roadmap)
11. [Documentation Index](#11-documentation-index)

---

## 1. Quick Start

```bash
# Backend
cd Backend
python -m venv venv && .\venv\Scripts\activate   # Windows
pip install -e ".[dev]"
cp .env.example .env                              # configure variables
uvicorn app.main:app --reload --port 8000

# Frontend (OpenNext + Wrangler dev)
cd Frontend
npm install
# .env.local has BACKEND_URL=http://localhost:8000 for dev
npm run dev                                        # localhost:3000
```

**Current status:** Sprint 1 (Emergency Stabilization) Blocks A-L **COMPLETE ✅**. Production live with first client (CasaVitaCure). Second tenant onboarding Tue Apr 15.

> For detailed sprint status, see [task_v2.md](file:///d:/WebDev/IA/.ai-context/task_v2.md). For execution log, see [execution_tracker.md](file:///d:/WebDev/IA/.ai-context/execution_tracker.md).

---

## 2. Architecture

Three distributed components:

| Component | Stack | Deploy | Function |
|:---|:---|:---|:---|
| **Frontend** | Next.js 15.5.15 / React 19 / TailwindCSS 3.4 / shadcn/ui | Cloudflare Workers (OpenNext) | Admin CRM panel with realtime |
| **Backend** | Python 3.11 / FastAPI 0.110+ / uvicorn | Google Cloud Run (Docker) | Webhook processing, LLM orchestration, Function Calling |
| **Database** | PostgreSQL (Supabase) with RLS + Realtime | Supabase Cloud | Multi-tenant persistence, pub/sub WebSocket |

```
WhatsApp User ──► Meta Webhook ──► FastAPI (Cloud Run)
                                       │
                                  ┌────┴────┐
                                  │ Resolve  │ TenantContext + HITL check
                                  └────┬────┘
                                       │
                         Background Task (async)
                        ┌──────────────────────────┐
                        │ 1. Persist inbound msg    │
                        │ 2. Atomic lock check      │
                        │ 3. Deduplicate (wamid)    │
                        │ 4. Fetch history (20 msgs)│
                        │ 5. Inject patient context │
                        │ 6. LLM inference          │
                        │ 7. Multi-round tool loop  │──► Native Calendar (Supabase)
                        │ 8. Synthesis pass         │      or GCal API (legacy)
                        │ 9. Persist + Send         │──► Meta Graph API v25.0
                        └──────────────────────────┘
                                       │
                              Supabase Realtime
                                       │
                         Frontend (CF Workers / OpenNext)
                         Dashboard / Chats / Agenda / CRM
```

> **Calendar architecture:** New tenants use the **native calendar** (Supabase tables: `resources`, `appointments`, `scheduling_config`). Legacy tenant CasaVitaCure retains Google Calendar integration. Both systems share the same AI tool interface.

### External APIs

| Service | Version | Module |
|:---|:---|:---|
| Meta WhatsApp Cloud API | **v25.0** | `infrastructure/messaging/meta_graph_api.py` |
| Google Calendar API | v3 | `infrastructure/calendar/google_client.py` |
| OpenAI Chat Completions | `/v1/chat/completions` | `infrastructure/llm_providers/openai_adapter.py` |
| OpenAI Responses API | `/v1/responses` | `infrastructure/llm_providers/openai_responses_adapter.py` |
| Google Generative AI | — | `infrastructure/llm_providers/gemini_adapter.py` (**MOCK — Sprint 2**) |
| Sentry | SDK v10+ | Backend: `sentry_sdk`, Frontend: `@sentry/nextjs` |
| Discord Webhooks | — | `infrastructure/telemetry/discord_notifier.py` |
| Resend | — | `infrastructure/email/email_service.py` |
| Supabase Auth | SSR | Frontend `AuthContext` + RLS |

---

## 3. Repository Structure

### Backend (`Backend/app/`)

Screaming Architecture (DDD + Ports/Adapters):

```
Backend/app/
├── main.py                                # App factory: lifespan, CORS, routers, exception handlers
├── api/dependencies.py                    # TenantContext extraction from Meta webhook payload
├── core/
│   ├── config.py                          # Pydantic Settings (14 env vars)
│   ├── event_bus.py                       # Pub/Sub in-memory (asyncio.Queue)
│   ├── exceptions.py                      # AppBaseException, TenantNotFoundError
│   ├── models.py                          # TenantContext dataclass (default: gpt-5.4-mini)
│   └── security.py                        # Meta webhook verify_token check
├── infrastructure/
│   ├── calendar/google_client.py          # GCal singleton: FreeBusy, book_round_robin, CRUD
│   ├── database/supabase_client.py        # AsyncClient singleton + get_db()
│   ├── email/email_service.py             # Resend API email alerts
│   ├── llm_providers/
│   │   ├── openai_adapter.py              # AsyncOpenAI + multi-round tool calling + strict schemas (Chat Completions)
│   │   ├── openai_responses_adapter.py    # Responses API adapter: streaming + reasoning.effort + tools
│   │   ├── gemini_adapter.py              # ⚠️ MOCK: returns static string (Sprint 2)
│   │   └── mock_adapter.py               # Echo adapter for MOCK_LLM=True
│   ├── messaging/meta_graph_api.py        # httpx singleton, Graph API v25.0, 50/100 pool
│   └── telemetry/
│       ├── logger_service.py              # JSON prod / human dev, async QueueHandler
│       └── discord_notifier.py            # Embeds with severity + traceback
└── modules/
    ├── communication/
    │   ├── routers.py                     # GET/POST /webhook + /api/sandbox/chat
    │   └── use_cases.py                   # ProcessMessageUseCase: orchestrator, multi-round
    │                                      #   tool loop, dedup, atomic lock, rapid-fire batching
    ├── intelligence/
    │   ├── router.py                      # LLMStrategy ABC, LLMFactory
    │   ├── tool_registry.py               # ToolRegistry singleton: register, get_schemas, execute
    │   └── tools/base.py                  # AITool ABC: get_schema(provider) + execute(**kwargs)
    └── scheduling/
        ├── native_service.py              # NativeCalendarService: Supabase-backed scheduling engine
        ├── services.py                    # SchedulingService → GoogleCalendarClient + EventBus
        └── tools.py                       # 7 AITools: Check/Book/Update/Delete Appointment,
                                           #   CheckMyAppointments, EscalateHuman, UpdatePatientScoring
```

### Frontend (`Frontend/`)

Next.js 15 App Router, deployed as **Cloudflare Worker via OpenNext** (see §5):

```
Frontend/
├── app/
│   ├── layout.tsx, global-error.tsx       # Root layout + Sentry render error capture
│   ├── login/page.tsx                     # Cinematic login: Vortex bg + CLI text + glassmorphic card
│   ├── auth/callback/, auth/confirm/      # OAuth PKCE flow (see deep_dives_&_misc/)
│   ├── config/page.tsx                    # LLM provider/model, system prompt, GCal OAuth
│   ├── api/                               # Proxy routes → Cloud Run backend
│   │   └── sandbox/chat/                  # Dedicated sandbox chat endpoint (OpenAI Responses API)
│   └── (panel)/                           # Auth-guarded route group (Sidebar + CrmProvider)
│       ├── dashboard/                     # Live alerts, INTERVENCIÓN MANUAL, glassmorphic stats
│       ├── chats/                         # Dual-mode: Regular (ChatArea) vs Sandbox (TestChatArea)
│       ├── agenda/                        # Native calendar (resources + appointments + scheduling_config)
│       ├── pacientes/                     # CRM: patient profiles, lead scoring, notes
│       ├── reportes/, finops/             # ⚠️ MOCK: placeholder data
│       └── admin-feedback/               # QA table (admin-only)
├── contexts/                              # AuthContext, ChatContext, UIContext, CrmContext
├── components/
│   ├── CRM/, Conversations/, Dashboard/   # Feature modules
│   ├── Layout/, Onboarding/               # Layout shell + 3-step onboarding flow
│   └── ui/                                # Primitives: Vortex, CliText, shadcn, etc.
├── instrumentation-client.ts              # ⚠️ DO NOT DELETE — Sentry client init
├── wrangler.toml                          # CF Worker config (see §5)
├── open-next.config.ts                    # OpenNext minimal config
└── next.config.js                         # Rewrites /api/* → Cloud Run + Sentry
```

---

## 4. Data Model (Supabase PostgreSQL)

> **Canonical source:** The live database schema. Verify with `information_schema.columns` when in doubt.

```sql
-- ═══════════════════════════════════════════════════════════════
-- CORE TABLES (Sprint 1)
-- ═══════════════════════════════════════════════════════════════

tenants (
    id UUID PK,
    name TEXT NOT NULL,
    ws_phone_id TEXT UNIQUE,                  -- Meta Phone Number ID (webhook routing)
    ws_token TEXT,                            -- WhatsApp permanent access token
    llm_provider TEXT CHECK IN ('openai','gemini'),
    llm_model TEXT,                           -- 'gpt-5.4-mini' (default)
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT TRUE,           -- Global kill-switch
    is_setup_complete BOOLEAN DEFAULT FALSE,  -- Onboarding gate
    calendar_ids JSONB DEFAULT '[]',          -- GCal calendar IDs (legacy)
    google_refresh_token_encrypted TEXT,       -- Fernet-encrypted OAuth refresh token
    google_calendar_email TEXT,
    google_calendar_status TEXT,              -- 'connected' | 'disconnected' | 'error'
    google_calendar_connected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)

contacts (
    id UUID PK,
    tenant_id UUID FK → tenants,
    phone_number TEXT,
    name TEXT,
    bot_active BOOLEAN DEFAULT TRUE,          -- HITL kill-switch per contact
    role TEXT CHECK IN ('cliente','staff','admin'),
    status TEXT DEFAULT 'lead',
    is_processing_llm BOOLEAN DEFAULT FALSE,  -- Atomic processing lock
    metadata JSONB DEFAULT '{}',              -- Scoring, clinical notes
    notes TEXT DEFAULT '',                    -- Staff editable notes (PacientesView)
    bsuid TEXT,                               -- Meta Business-Scoped User ID (Phase 1 capture)
    last_message_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,                   -- Auto via trigger trg_contacts_updated_at
    created_at TIMESTAMPTZ,
    UNIQUE(tenant_id, phone_number)
)

messages (
    id UUID PK,
    contact_id UUID FK → contacts,
    tenant_id UUID FK → tenants,              -- Denormalized for RLS
    sender_role TEXT CHECK IN ('user','assistant','human_agent','system_alert'),
    content TEXT,
    wamid TEXT,                               -- WhatsApp Message ID (deduplication)
    note TEXT,                                -- Inline QA notes from sandbox
    timestamp TIMESTAMPTZ
)

alerts (
    id UUID PK,
    tenant_id UUID FK → tenants,
    contact_id UUID FK → contacts (NULLABLE),
    type TEXT,                                -- 'escalation', 'cancellation', etc.
    message TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ
)

profiles (
    id UUID PK FK → auth.users,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    is_superadmin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

tenant_users ( id UUID PK, tenant_id UUID FK, user_id UUID FK → auth.users, role TEXT CHECK IN ('admin','staff','viewer') DEFAULT 'staff', UNIQUE(tenant_id, user_id) )
test_feedback ( id UUID PK, tenant_id UUID FK, patient_phone TEXT, history JSONB, notes JSONB, tester_email TEXT, created_at TIMESTAMPTZ )

-- ═══════════════════════════════════════════════════════════════
-- ONBOARDING TABLES (Block R)
-- ═══════════════════════════════════════════════════════════════

tenant_onboarding (
    id UUID PK,
    tenant_id UUID FK → tenants UNIQUE,
    step_current INT DEFAULT 1,               -- Onboarding wizard step (1-3)
    business_name TEXT,
    business_type TEXT,
    business_description TEXT,
    target_audience TEXT,
    services_offered JSONB DEFAULT '[]',
    business_hours TEXT,
    tone_of_voice TEXT,
    special_instructions TEXT,
    greeting_message TEXT,
    escalation_rules TEXT,
    faq_items JSONB DEFAULT '[]',
    raw_conversation JSONB DEFAULT '[]',
    configuration_complete BOOLEAN DEFAULT FALSE,
    generated_system_prompt TEXT,
    phone_number TEXT,                        -- Owner's personal phone (billing, support)
    resource_count INT DEFAULT 1,             -- Number of team members/resources
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

onboarding_messages (
    id UUID PK,
    tenant_id UUID FK → tenants,
    role TEXT CHECK IN ('user','assistant','system','event'),
    content TEXT DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ
)

-- ═══════════════════════════════════════════════════════════════
-- NATIVE CALENDAR TABLES (Block S-T)
-- ═══════════════════════════════════════════════════════════════

resources (
    id UUID PK,
    tenant_id UUID FK → tenants,
    name TEXT NOT NULL,                       -- e.g., "Equipo 1", "Dr. López"
    label TEXT,
    color TEXT DEFAULT '#6366f1',
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

appointments (
    id UUID PK,
    tenant_id UUID FK → tenants,
    resource_id UUID FK → resources,
    contact_id UUID FK → contacts (NULLABLE),
    service_id UUID FK → tenant_services (NULLABLE),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    duration_minutes INT DEFAULT 30,
    client_name TEXT,
    client_phone TEXT,
    service_name TEXT,                        -- Denormalized for display
    status TEXT CHECK IN ('confirmed','cancelled','completed','no_show') DEFAULT 'confirmed',
    booked_by TEXT CHECK IN ('ai_assistant','manual_ui','api') DEFAULT 'ai_assistant',
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

scheduling_config (
    id UUID PK,
    tenant_id UUID FK → tenants UNIQUE,
    business_hours JSONB,                     -- {monday: {start: "09:00", end: "19:00"}, ...}
    default_duration_minutes INT DEFAULT 30,
    slot_interval_minutes INT DEFAULT 30,
    buffer_between_minutes INT DEFAULT 0,
    round_robin_enabled BOOLEAN DEFAULT TRUE,
    timezone TEXT DEFAULT 'America/Santiago',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)

tenant_services (
    id UUID PK,
    tenant_id UUID FK → tenants,
    name TEXT NOT NULL,                       -- e.g., "Fumigación General"
    description TEXT,
    price INT CHECK (price >= 0),             -- CLP, nullable = "consultar"
    price_is_variable BOOLEAN DEFAULT FALSE,
    duration_minutes INT,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

### Row Level Security (RLS)

All tables use `get_user_tenant_ids()` (queries `tenant_users` by `auth.uid()`). Backend bypasses RLS via `SUPABASE_SERVICE_ROLE_KEY`.

### Supabase Realtime

Enabled on `contacts`, `messages`, `alerts`. Frontend channels: `chat_contacts_changes`, `chat_messages_changes`, `alerts-realtime-ui`.

---

## 5. Infrastructure & Deployment

### Infrastructure Identifiers

| Resource | Identifier | Notes |
|:---|:---|:---|
| **PRODUCTION** | | |
| Cloud Run (prod) | `ia-backend-prod` (**us-central1**) | Auto-deploy from `main` via Cloud Build |
| Cloud Run URL (prod) | `ia-backend-prod-645489345350.us-central1.run.app` | |
| CF Worker (prod) | `ia-whatsapp-crm` | **Worker, NOT Pages** |
| CF Workers URL (prod) | `ia-whatsapp-crm.tomasgemes.workers.dev` | |
| Frontend domain (prod) | `dash.tuasistentevirtual.cl` | Custom domain on CF Workers |
| Supabase (prod) | `nemrjlimrnrusodivtoa` | Secret: `SUPABASE_SERVICE_ROLE_KEY` |
| GCal credentials | `GOOGLE_CALENDAR_CREDENTIALS` (Secret Manager) | ⚠️ CasaVitaCure SA — prod only |
| **DEVELOPMENT** | | |
| Cloud Run (dev) | `ia-backend-dev` (**us-central1**) | Min=0, Max=1. Auto-deploy from `desarrollo` |
| Cloud Run URL (dev) | `ia-backend-dev-645489345350.us-central1.run.app` | |
| CF Worker (dev) | `dev-ia-whatsapp-crm` | |
| Frontend domain (dev) | `ohno.tuasistentevirtual.cl` | |
| Supabase (dev) | `nzsksjczswndjjbctasu` | Secret: `SUPABASE_SERVICE_ROLE_KEY_DEV` |
| **SHARED** | | |
| GCP Project | `saas-javiera` | Cloud Build, IAM, Secret Manager |
| GitHub repo | `YggrYergen/ia-whatsapp-crm` | `main` → prod, `desarrollo` → dev |
| Sentry DSN | Shared DSN, filtered by `environment` tag | `production` / `development` |

### Branch Topology

| Branch | Database | Frontend | Backend |
|:---|:---|:---|:---|
| `main` | Supabase Prod | CF Worker `ia-whatsapp-crm` (auto-deploy) | Cloud Run `ia-backend-prod` (auto-deploy) |
| `desarrollo` | Supabase Dev | CF Worker `dev-ia-whatsapp-crm` (auto-deploy) | Cloud Run `ia-backend-dev` (auto-deploy) |

### Backend Deploy (Cloud Run)

**Dockerfile** (`Backend/Dockerfile`): Multi-stage, non-root `crmuser`, `python:3.11-slim`.
**CMD:** `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log`

**Secrets** (via Secret Manager — SA needs `roles/secretmanager.secretAccessor` per secret):

| Env Var | Secret Manager Name |
|:---|:---|
| `WHATSAPP_VERIFY_TOKEN` | `WHATSAPP_VERIFY_TOKEN` |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| `GEMINI_API_KEY` | `GEMINI_API_KEY` |
| `SUPABASE_URL` | `SUPABASE_URL` |
| `SUPABASE_SERVICE_ROLE_KEY` | `SUPABASE_SERVICE_ROLE_KEY` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | `GOOGLE_CALENDAR_CREDENTIALS` |

**Update secrets:** `gcloud run services update ia-backend-prod --project=saas-javiera --region=us-central1 --update-secrets="..."`

**Cloud Build Trigger:** Push to `main` → 3-step pipeline (Build → Push → Deploy). Trigger uses `Backend/Dockerfile` with context `Backend/`. Service account: `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`.

> **Docs:** [FastAPI Quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service), [Continuous Deployment](https://cloud.google.com/run/docs/continuous-deployment), [Configure Secrets](https://cloud.google.com/run/docs/configuring/services/secrets)

### Frontend Deploy (Cloudflare Workers — OpenNext)

- **Adapter:** OpenNext (`@opennextjs/cloudflare`)
- **Build:** `npx opennextjs-cloudflare build` → `.open-next/worker.js`
- **Deploy:** `npx wrangler deploy --keep-vars` (auto via Workers Builds on push to `main`)
- **Root directory:** `Frontend`

**Two types of env vars (configured in CF dashboard):**

| Type | Where | When Read | Variables |
|:---|:---|:---|:---|
| Build vars | Settings → Builds → Variables | During `next build` | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SENTRY_DSN`, `BACKEND_URL` |
| Runtime vars | Settings → Variables | Worker runtime | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SENTRY_DSN` |

> **Docs:** [OpenNext Get Started](https://opennext.js.org/cloudflare/get-started), [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars), [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)

### Meta / WhatsApp (LIVE)

- **Webhook:** `POST https://ia-backend-prod-645489345350.us-central1.run.app/webhook`
- **System User token:** Permanent (never-expiring), stored in `tenants.ws_token`
- **Subscribed events:** `messages`, `message_status`
- **AI Chatbot Policy:** Compliant — task-specific assistant (booking, scoring, escalation)

> **Docs:** [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks), [AI Chatbot Policy](https://developers.facebook.com/docs/whatsapp/overview/ai-chatbot-policy), [System Users](https://developers.facebook.com/docs/marketing-api/system-users/)

---

## 6. Critical Rules — Anti-Regression

> **These rules exist because violations caused real production incidents.** Each has a linked postmortem.

### Frontend — DO NOT

| # | Rule | Why |
|:---|:---|:---|
| 1 | **DO NOT re-create `sentry.client.config.ts`** | DEPRECATED. Use `instrumentation-client.ts` (Next.js 15+) |
| 2 | **DO NOT add `disableClientInstrumentation: true`** to next.config.js | Kills all frontend Sentry capture |
| 3 | **DO NOT downgrade Next.js below 15.x** | `instrumentation-client.ts` doesn't exist in 14.x |
| 4 | **DO NOT delete `app/global-error.tsx`** | Required for React render error capture |
| 5 | **DO NOT revert to `@cloudflare/next-on-pages`** | DEPRECATED. Doesn't support `instrumentation-client.ts` |
| 6 | **DO NOT commit `.env.local`** | Contains `BACKEND_URL=http://localhost:8000` — crashes prod Worker |
| 7 | **DO NOT put DEV values in `wrangler.toml [vars]`** | `[vars]` ALWAYS overwrite CF dashboard values, even with `--keep-vars`. Caused P0 incident 2026-04-17: PROD pointed to DEV for 24+h. Keep `--keep-vars` AND verify `[vars]` match PROD. |
| 8 | **DO NOT lower `compatibility_date`** below `2025-08-16` in wrangler.toml | Breaks Sentry SDK `https.request` |

### Backend — DO NOT

| # | Rule | Why |
|:---|:---|:---|
| 9 | **DO NOT use `except: pass`** anywhere | Every `except` → `sentry_sdk.capture_exception()` + `send_discord_alert()` + logger |
| 10 | **DO NOT upload base64-encoded secrets** to Secret Manager | Backend expects raw JSON for `GOOGLE_CALENDAR_CREDENTIALS` |
| 11 | **DO NOT change `gpt-5.4-mini`** model default without testing | Validated model. `gpt-4o-mini` is DEPRECATED. |
| 12 | **DO NOT remove `strict: true`** from tool schemas | Prevents LLM parameter hallucination |
| 13 | **DO NOT remove webhook HMAC-SHA256 verification** | Security: validates requests come from Meta |
| 14 | **DO NOT connect GCal dev credentials to prod calendar** | Risk of test operations corrupting live calendar |

### Deployment — MUST

| # | Rule | Why |
|:---|:---|:---|
| 15 | **MUST verify migrations on BOTH DEV and PROD** | Schema drift = crashes after merge |
| 16 | **MUST run health check after every PROD change** | Apr 12 incident: broken change was invisible 12+ hours |
| 17 | **Hardcoded backend URL fallback** in `next.config.js` is `europe-west1` | `BACKEND_URL` MUST be set as build var pointing to `us-central1` |

> **Detailed postmortems:** See `deep_dives_&_misc/` for Auth PKCE, Sentry/Next.js 15, OpenNext migration, Sentry coverage hardening.

---

## 7. Environment Variables

### Backend (14 vars in `config.py`)

| Variable | Required | Default | Use |
|:---|:---|:---|:---|
| `ENVIRONMENT` | No | `"development"` | Log format (JSON vs human) |
| `LOG_LEVEL` | No | `"DEBUG"` | Logging level |
| `MOCK_LLM` | No | `False` | Bypass real LLMs with MockStrategy |
| `WHATSAPP_VERIFY_TOKEN` | **Yes** | — | Meta webhook verification |
| `OPENAI_API_KEY` | **Yes** | — | OpenAI auth |
| `GEMINI_API_KEY` | **Yes** | — | Gemini auth (required even if adapter is mock) |
| `SUPABASE_URL` | **Yes** | — | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | **Yes** | — | Admin key (bypasses RLS) |
| `DISCORD_WEBHOOK_URL` | No | `None` | Discord alerts URL |
| `RESEND_API_KEY` | No | `None` | Email alerts via Resend |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | No | `None` | Google Calendar credentials (raw JSON string) |
| `GOOGLE_OAUTH_CLIENT_ID` | No | `None` | OAuth for multi-tenant calendar |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | `None` | OAuth secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | No | `None` | OAuth callback URI |

### Frontend (4 vars — see §5 for build vs runtime strategy)

| Variable | Type | Use |
|:---|:---|:---|
| `NEXT_PUBLIC_SUPABASE_URL` | Build + Runtime | Supabase browser client |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Build + Runtime | Anonymous key (RLS-restricted) |
| `NEXT_PUBLIC_SENTRY_DSN` | Build + Runtime | Sentry error tracking |
| `BACKEND_URL` | **Build only** | Compiles `/api/*` rewrites into routes-manifest.json |

---

## 8. Design Patterns

| Pattern | Implementation | Location |
|:---|:---|:---|
| **Strategy** | `LLMFactory` → `OpenAIStrategy`, `GeminiStrategy`, `MockStrategy` per tenant | `intelligence/router.py` |
| **Registry** | `ToolRegistry` registers 7 tools at boot | `intelligence/tool_registry.py` |
| **Pub/Sub** | `EventBus` (asyncio.Queue) decouples side effects | `core/event_bus.py` |
| **Singleton** | `SupabasePooler`, `MetaGraphAPIClient`, `GoogleCalendarClient` | Respective modules |
| **Background Tasks** | FastAPI responds 200 to Meta within 3s, processes async | `communication/routers.py` |
| **Atomic Lock** | `is_processing_llm` mutex prevents concurrent LLM calls per contact, TTL 90s | `communication/use_cases.py` |
| **RBAC** | `caller_role` injected in tool kwargs | `scheduling/tools.py` |
| **Zero-Trust** | Delete appointment verifies phone match; escalation validates caller | `scheduling/tools.py` |
| **Multi-Round Tool Loop** | Agentic loop: LLM → tool calls → `role:tool` results → re-inference → until no more tools | `communication/use_cases.py` |

---

## 9. Dependencies

### Backend (`pyproject.toml`)

```
fastapi>=0.110.0           uvicorn>=0.27.1            supabase>=2.3.6
openai>=1.14.0             google-generativeai>=0.4.1  pydantic>=2.6.4
pydantic-settings>=2.2.1   httpx>=0.27.0              python-dotenv>=1.0.1
orjson>=3.9.15             pytz>=2024.1               google-api-python-client>=2.122.0
google-auth-oauthlib>=1.2.0 sentry-sdk[fastapi]>=2.0.0 cryptography>=42.0.0

Dev: pytest>=8.0.0, pytest-asyncio>=0.23.5, coverage>=7.4.0
```

> ⚠️ `google-generativeai` is deprecated (FutureWarning on startup). Sprint 2: migrate to `google-genai`.

### Frontend (`package.json`)

```
next@15.5.15               react@^19.0.0              @supabase/ssr@^0.10.0
@supabase/supabase-js@^2.98.0  @sentry/nextjs@^10.47.0  lucide-react@^1.7.0
date-fns@^4.1.0            recharts@^3.8.1            radix-ui@^1.4.3
shadcn@^4.1.2              class-variance-authority    clsx@^2.1.1
tailwind-merge@^2.6.1      tailwindcss-animate@^1.0.7 tw-animate-css@^1.4.0

Dev: typescript@^5.4.3, tailwindcss@^3.4.3, eslint@^8.57.0, eslint-config-next@15.5.15
```

---

## 10. Roadmap

> **Detailed execution plan:** [task_v2.md](file:///d:/WebDev/IA/.ai-context/task_v2.md)
> **Full implementation history:** [implementation_plan.md](file:///d:/WebDev/IA/.ai-context/implementation_plan.md)

### Sprint 1: Emergency Stabilization (Apr 11-15) — ✅ COMPLETE

| Block | Status | Summary |
|:---|:---|:---|
| A-H | ✅ Complete | Quick wins, strict tools, agentic loop, resilience, observability, BSUID, deploy |
| I | ✅ Complete | Response quality fix (5 steps: adapter, prompt v2, dedup, batching, rapid-fire) |
| J | ✅ Complete | Escalation UX (badge, resolve, filter, pulse, NotificationFeed) |
| K | ✅ Complete | Tenant provisioning (automated via onboarding flow) |
| L | ✅ Complete | Dashboard + mobile frontend overhaul (glassmorphic, live alerts, patient profiles) |
| M-Q | ✅ Complete | CasaVitaCure live, fumigation tenant provisioned |

### Sprint 1.5: Onboarding + Native Calendar (Apr 13-16) — IN PROGRESS

| Block | Status | Summary |
|:---|:---|:---|
| R | ✅ Complete | Self-service onboarding: 3-step wizard (Welcome → ConfigChat → Completion) with AI config agent |
| S | ✅ Complete | Native calendar engine: resources, appointments, scheduling_config, round-robin booking |
| T | ✅ Complete | Agenda UI: real business hours, progress bars per resource, native calendar read/write |
| U | ✅ Complete | Sandbox chat: dedicated `/api/sandbox/chat` endpoint, OpenAI Responses API, session persistence |
| V | ✅ Complete | Login overhaul: Vortex particle simulation, dark matter dust, CLI pre-suasion text, glassmorphic card |
| W | ⏳ In Progress | README update, observability audit, mobile polish, E2E testing, PROD migration gate |

### Sprint 2: Product Expansion (Apr 16-25)

| Priority | Feature |
|:---|:---|
| 🟢 | Responses API adapter (`openai_responses_adapter.py`) — `reasoning.effort` + tools + streaming. Built for onboarding agent (Block R). |
| 🔴 | WhatsApp pipeline → Responses API migration — swap `openai_adapter.py` after onboarding adapter proven |
| 🔴 | Instagram DM integration — SELLING POINT |
| 🔴 | Multi-squad booking engine — SELLING POINT |
| 🔴 | Dashboard MVP (charts, KPIs, real metrics) |
| 🟡 | Gemini adapter real (`google-genai` SDK) |
| 🟡 | Credits/billing system (`tenant_plans`, `consume_credits()`) |
| 🟡 | SuperAdmin panel (all tenants overview) |

### Sprint 3: Scale (Apr 26 - May 4)

| Priority | Feature |
|:---|:---|
| 🔴 | Meta App Review (Tech Provider — required at 7+ clients) |
| 🟡 | Facebook Messenger (reuses 90% of Instagram adapter) |
| 🟡 | Customer Intelligence v1 (enriched profiles, 30-day inactivity) |
| 🟡 | FinOps dashboard (revenue vs cost per tenant) |

---

## 11. Documentation Index

All planning and operational documents live in `.ai-context/`:

| Document | Purpose |
|:---|:---|
| [task_v2.md](file:///d:/WebDev/IA/.ai-context/task_v2.md) | **Source of truth** for current sprint status — open items at top, completed at bottom |
| [task.md](file:///d:/WebDev/IA/.ai-context/task.md) | Legacy task tracker with full Sprint 1 execution plan |
| [execution_tracker.md](file:///d:/WebDev/IA/.ai-context/execution_tracker.md) | Day-by-day execution log with verification evidence |
| [implementation_plan.md](file:///d:/WebDev/IA/.ai-context/implementation_plan.md) | Full implementation history: Phase 0-5D + Sprint 1 blocks |
| [master_plan.md](file:///d:/WebDev/IA/.ai-context/master_plan.md) | Business plan: financials, GTM, risk register, client pipeline |
| [SESSION_PROMPT.md](file:///d:/WebDev/IA/.ai-context/SESSION_PROMPT.md) | Session context for AI agents — rules, identifiers, current state |

### Deep Dives & Postmortems (`deep_dives_&_misc/`)

| Document | Content |
|:---|:---|
| `deep_dive_a_response_quality.md` | BUG-6 root cause analysis (7 issues), 11+ OpenAI doc URLs |
| `deep_dive_b_multi_channel.md` | BSUID migration, Instagram DM, Meta compliance, 15+ doc URLs |
| `deep_dive_c_dashboard_ux.md` | Dashboard design (4 blocks), observability, correlation IDs |
| `reasoning_effort_diagnostic.md` | `reasoning_effort` + tools incompatibility, Responses API migration plan |
| `fumigation_prompt_template.md` | System prompt template for fumigation tenant onboarding |