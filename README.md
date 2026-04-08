# AI WhatsApp CRM — Documentación Técnica

> **SaaS Multi-tenant B2B** para automatizar la primera línea de atención al cliente vía WhatsApp mediante LLMs con Function Calling, bajo paradigma Human-In-The-Loop (HITL).

---

## 0. Estado Actual del Proyecto (2026-04-08)

**Estado global:** 🟡 En estabilización — producción inestable, primera clienta esperando.

| Pieza | Estado | Detalle |
|:---|:---|:---|
| **Backend (Cloud Run)** | 🟡 Desplegado, funcionalidad parcial | Última serie de commits son todos fixes. CORS abierto, tracebacks expuestos, endpoints sin auth |
| **Frontend (CF Pages)** | 🔴 Inestable | Chat y agenda reportan errores de conexión. Auth guard inexistente. Logout no invalida sesión |
| **BD Producción** | 🟡 Funcional, config sin verificar | RLS activo. Realtime probablemente habilitado. Schema y datos por confirmar vía MCP |
| **BD Desarrollo** | ⚪ Sin verificar | Existe (`nzsksjczswndjjbctasu`). No confirmado si tiene schema ni datos actualizados |
| **Rama `main`** | 🟡 10 archivos modificados sin commit | Cambios probablemente de sesión anterior (Gemini Flash). Deben revisarse antes de aceptar |
| **Rama `desarrollo`** | ⚪ 5 commits detrás de main | Se sincroniza DESPUÉS de estabilizar main |
| **Monitoreo** | 🟡 Parcial | Sentry inicializado pero frontend instrumentation deshabilitada. Discord recibe algunos errores, no todos |

### Plan de Go-Live (en ejecución)

```
FASE 0: Pre-flight ──► FASE 1: Estabilizar main ──► FASE 2: Monitoreo ──► FASE 3: Separación entornos ──► FASE 4: Meta + Go-Live
```

| Fase | Objetivo | Estado |
|:---|:---|:---|
| **Fase 0** | Limpiar working tree, inspeccionar diffs sospechosos, tag de restauración | Pendiente |
| **Fase 1** | Diagnosticar y arreglar producción (auth, logout, CORS, agenda, chat) | Pendiente |
| **Fase 2** | Sentry completo + Discord para TODOS los errores + email fallback | Pendiente |
| **Fase 3** | Separar `main`→prod (`dash.tuasistentevirtual.cl`) y `desarrollo`→dev (`ohno.tuasistentevirtual.cl`) | Pendiente |
| **Fase 4** | Conectar webhook de Meta, test end-to-end, go-live | Pendiente |

> **⚠️ PENDIENTE DE VERIFICACIÓN:** La configuración exacta de los auto-deploys (build commands, env vars inyectadas, service accounts, regiones), los esquemas de ambas bases de datos, y el estado real de Cloud Run y Cloudflare Pages requieren auditoría directa vía herramientas MCP de Supabase y Google Cloud Run. Se verificará al iniciar las Fases 1 y 3.

### Herramientas MCP Configuradas

Para auditoría y gestión de infraestructura, se dispone de 4 MCP servers:

| MCP | Config Key | Protocolo | Función |
|:---|:---|:---|:---|
| Google Cloud Run | `cloudrun` | CLI (`npx @google-cloud/cloud-run-mcp`) | Servicios, env vars, logs, deploys del backend |
| Supabase Producción | `supabase-prod` | HTTP (`mcp.supabase.com`, ref: `nemrjlimrnrusodivtoa`) | Schema, RLS, datos, realtime de BD producción |
| Supabase Desarrollo | `supabase-dev` | HTTP (`mcp.supabase.com`, ref: `nzsksjczswndjjbctasu`) | Schema, datos de BD desarrollo |
| Cloudflare | `cloudflare` | CLI (`npx mcp-remote → bindings.mcp.cloudflare.com`) | Config de Cloudflare Pages, dominios, bindings |

Config en: `~/.gemini/antigravity/mcp_config.json`

### Identificadores de Infraestructura

| Recurso | Identificador | Notas |
|:---|:---|:---|
| Cloud Run service URL | `ia-backend-prod-645489345350.europe-west1.run.app` | Hardcodeada en `next.config.js` como fallback |
| GCP project number | `645489345350` | Implícito en la URL de Cloud Run |
| Supabase prod project | `nemrjlimrnrusodivtoa` | `nemrjlimrnrusodivtoa.supabase.co` |
| Supabase dev project | `nzsksjczswndjjbctasu` | `nzsksjczswndjjbctasu.supabase.co` |
| Cloudflare Pages project | `ia-whatsapp-crm` | En `wrangler.toml` |
| Frontend dominio prod | `dash.tuasistentevirtual.cl` | Custom domain en CF Pages |
| Frontend dominio dev | `ohno.tuasistentevirtual.cl` | Pendiente de configurar |
| GitHub repo | `YggrYergen/ia-whatsapp-crm` | Auto-deploys desde rama `main` |
| Sentry DSN | `b5b7a769848286fc...@o4511179991416832` | En `wrangler.toml` y `sentry.client.config.ts` |

---

## 1. Arquitectura del Sistema

Tres componentes distribuidos:

| Componente | Stack | Despliegue | Función |
|:---|:---|:---|:---|
| **Frontend** | Next.js 14.1.4 / React 18 / TailwindCSS 3.4 / shadcn/ui | Cloudflare Pages | Panel CRM administrativo con realtime |
| **Backend** | Python 3.11 / FastAPI 0.110+ / uvicorn | Google Cloud Run (Docker) | Procesamiento de webhooks, orquestación LLM, Function Calling |
| **Base de Datos** | PostgreSQL (Supabase) con RLS + Realtime | Supabase Cloud | Persistencia multi-tenant, pub/sub WebSocket |

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLUJO PRINCIPAL                                │
│                                                                        │
│  WhatsApp User ──► Meta Webhook ──► FastAPI (Cloud Run)                │
│                                        │                               │
│                                   ┌────┴────┐                          │
│                                   │ Resolve │ TenantContext             │
│                                   │ HITL?   │ bot_active check         │
│                                   └────┬────┘                          │
│                                        │                               │
│                          ┌─────────────┼─────────────┐                 │
│                          │    Background Task         │                 │
│                          │  ┌──────────────────────┐  │                 │
│                          │  │ 1. Persist inbound   │  │                 │
│                          │  │ 2. Mutex Lock check  │  │                 │
│                          │  │ 3. Fetch history(20) │  │                 │
│                          │  │ 4. Inject context    │  │                 │
│                          │  │ 5. LLM inference     │  │                 │
│                          │  │ 6. Tool execution    │  │ ──► GCal API   │
│                          │  │ 7. Synthesis pass    │  │                 │
│                          │  │ 8. Persist + Send    │  │ ──► Meta API   │
│                          │  └──────────────────────┘  │                 │
│                          └────────────────────────────┘                 │
│                                        │                               │
│                               Supabase Realtime                        │
│                                        │                               │
│                          Frontend (Cloudflare Pages)                    │
│                          Dashboard / Chats / Agenda                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### APIs Externas Integradas

| Servicio | Uso | Módulo |
|:---|:---|:---|
| Meta WhatsApp Cloud API v19.0 | Recepción/envío de mensajes | `infrastructure/messaging/` |
| Google Calendar API v3 | Consulta FreeBusy, CRUD de eventos, Round-Robin | `infrastructure/calendar/` |
| OpenAI API | Inferencia LLM + Function Calling (adaptador activo) | `infrastructure/llm_providers/openai_adapter.py` |
| Google Generative AI | Registrado en factory pero **adaptador NO implementado** (retorna mock) | `infrastructure/llm_providers/gemini_adapter.py` |
| Sentry | Error tracking y APM (backend + frontend) | `sentry_sdk`, `@sentry/nextjs` |
| Discord Webhooks | Alertas dev en tiempo real | `infrastructure/telemetry/discord_notifier.py` |
| Resend | Emails transaccionales de alerta al negocio | `infrastructure/email/email_service.py` |
| Supabase Auth | SSO Google para el panel administrativo | Frontend `AuthContext` + Supabase RLS |

---

## 2. Estructura del Repositorio

### Backend (`Backend/app/`)

Implementa **Screaming Architecture** (Domain-Driven Design + Puertos/Adaptadores). La estructura comunica intención de negocio; los detalles técnicos están aislados en `infrastructure/`.

```
Backend/app/
├── main.py                              # Application Factory: lifespan, CORS, routers,
│                                        # exception handlers, y 6 endpoints inline
│                                        # (simulate, test-feedback, calendar/events, 
│                                        #  calendar/book, debug-ping, debug-exception)
│
├── api/
│   └── dependencies.py                  # Extrae TenantContext del payload de Meta
│                                        # via ws_phone_id → query a tabla tenants
│
├── core/
│   ├── config.py                        # Pydantic Settings (14 variables de entorno)
│   ├── event_bus.py                     # Pub/Sub in-memory (asyncio.Queue)
│   ├── exceptions.py                    # AppBaseException, TenantNotFoundError,
│   │                                    # ProviderNotRegisteredError, WhatsAppAPIError
│   ├── models.py                        # TenantContext (id, ws_phone_id, llm_provider,
│   │                                    # llm_model, system_prompt, is_active, ws_token)
│   ├── proactive_worker.py              # Worker periódico (STUB: loop con pass)
│   └── security.py                      # Verificación de hub.verify_token de Meta
│
├── infrastructure/
│   ├── calendar/
│   │   └── google_client.py             # Singleton GCal service. FreeBusy, book_round_robin,
│   │                                    # delete, list. Credenciales: ENV JSON > file > ADC
│   ├── database/
│   │   ├── supabase_client.py           # SupabasePooler (AsyncClient singleton) + get_db()
│   │   └── repositories/
│   │       └── base.py                  # BaseRepository genérico (NO USADO en producción)
│   ├── email/
│   │   └── email_service.py             # Resend API. Emails hardcodeados a 2 destinatarios
│   ├── llm_providers/
│   │   ├── openai_adapter.py            # AsyncOpenAI chat.completions con tool_choice=auto
│   │   ├── gemini_adapter.py            # ⚠️ MOCK: retorna string estático, sin tool calling
│   │   └── mock_adapter.py              # Echo adapter para testing local (MOCK_LLM=True)
│   ├── messaging/
│   │   └── meta_graph_api.py            # httpx.AsyncClient singleton con pooling (50/100)
│   └── telemetry/
│       ├── logger_service.py            # QueueHandler async. JSON en prod, human en dev
│       └── discord_notifier.py          # Embeds con severity (error/warning/info) + traceback
│
└── modules/
    ├── clinical_triage/
    │   └── evaluator.py                 # Keyword matching ("dolor pecho", "sangrado").
    │                                    # ⚠️ Referencia tenant.staff_notification_number
    │                                    # que NO existe en TenantContext → AttributeError
    │
    ├── communication/
    │   ├── routers.py                   # GET /webhook (verify) + POST /webhook (enqueue)
    │   └── use_cases.py                 # ProcessMessageUseCase: orquestador principal.
    │                                    # Mutex lock, history fetch (20 msgs), context injection,
    │                                    # LLM call, tool loop (1 pasada), persist+send parallel
    │
    ├── integrations/
    │   └── google_oauth_router.py       # OAuth 2.0 multi-tenant. Fernet encryption de
    │                                    # refresh_token derivada de SUPABASE_SERVICE_ROLE_KEY
    │
    ├── intelligence/
    │   ├── router.py                    # LLMStrategy (ABC), LLMResponse (DTO), LLMFactory
    │   ├── tool_registry.py             # ToolRegistry singleton. register(), get_all_schemas(),
    │   │                                # execute_tool() con try/except → error JSON estándar
    │   └── tools/
    │       └── base.py                  # AITool (ABC): get_schema(provider) + execute(**kwargs)
    │
    └── scheduling/
        ├── services.py                  # SchedulingService: capa de negocio que invoca
        │                                # GoogleCalendarClient y publica eventos al EventBus
        └── tools.py                     # 7 AITools registradas:
                                         # - CheckAvailabilityTool (get_merged_availability)
                                         # - CheckMyAppointmentsTool (get_my_appointments) [RBAC]
                                         # - BookAppointmentTool (book_round_robin)
                                         # - UpdateAppointmentTool (delete+rebook atómico)
                                         # - DeleteAppointmentTool (zero-trust phone match)
                                         # - EscalateHumanTool (bot_active=False + alerta)
                                         # - UpdatePatientScoringTool (metadata jsonb update)
```

### Frontend (`Frontend/`)

Next.js 14 con App Router, shadcn/ui, TailwindCSS. Desplegado como **static export** en Cloudflare Pages.

```
Frontend/
├── app/
│   ├── layout.tsx                       # Root: Inter font, metadata "AI CRM Enterprise"
│   ├── page.tsx                         # Redirect → /dashboard
│   ├── globals.css                      # Tailwind directives + CSS vars (oklch) + scrollbar
│   ├── login/page.tsx                   # Google SSO via Supabase Auth
│   ├── auth/callback/                   # OAuth redirect handler
│   ├── config/page.tsx                  # Configuración: LLM provider/model selector,
│   │                                    # system prompt editor, Google Calendar OAuth connect
│   ├── api/                             # Next.js API routes (proxy al backend)
│   │   ├── calendar/events/route.ts     # Proxy → Backend /api/calendar/events
│   │   ├── calendar/book/route.ts       # Proxy → Backend /api/calendar/book
│   │   ├── simulate/route.ts           # Proxy → Backend /api/simulate
│   │   └── test-feedback/route.ts      # Proxy → Backend /api/test-feedback
│   └── (panel)/                         # Route group — Layout con Sidebar + CrmProvider
│       ├── layout.tsx                   # CrmProvider → AuthProvider+ChatProvider+UIProvider
│       ├── dashboard/page.tsx           # KPIs y métricas (⚠️ datos HARDCODEADOS, no reales)
│       ├── chats/page.tsx               # Chat bidireccional con realtime (FUNCIONAL)
│       ├── agenda/page.tsx              # Vista calendario integrada con Google Calendar (FUNCIONAL)
│       ├── pacientes/page.tsx           # Tabla CRM de contactos (FUNCIONAL, datos de Supabase)
│       ├── reportes/page.tsx            # ⚠️ MOCK: "Módulo en Construcción", datos estáticos
│       ├── finops/page.tsx              # ⚠️ MOCK: métricas de costos con datos estáticos
│       └── admin-feedback/page.tsx      # Panel dev para revisar test_feedback (admin-only)
│
├── components/
│   ├── Layout/
│   │   ├── Sidebar.tsx                  # Navegación lateral responsive (desktop/mobile)
│   │   ├── GlobalNotifications.tsx      # Toast overlay para alertas realtime
│   │   ├── NotificationFeed.tsx         # Panel de historial de alertas con mark-as-read
│   │   └── GlobalFeedbackButton.tsx     # Widget flotante para feedback de QA
│   ├── CRM/
│   │   ├── AgendaView.tsx               # Calendario semanal con drag & book (29KB)
│   │   ├── PacientesView.tsx            # Tabla de contactos con filtros y estado (12KB)
│   │   └── FinopsView.tsx               # Métricas de costos LLM (9KB, datos mock)
│   ├── Conversations/
│   │   ├── ContactList.tsx              # Lista de conversaciones con last_message preview
│   │   ├── ChatArea.tsx                 # Chat real con envío de mensajes (human_agent)
│   │   ├── TestChatArea.tsx             # Chat simulación (phone 56912345678)
│   │   ├── ClientProfilePanel.tsx       # Panel lateral con datos del contacto
│   │   └── TestConfigPanel.tsx          # Config de simulación (prompt, provider)
│   ├── Dashboard/
│   │   └── DashboardView.tsx            # 4 bloques: PAZ MENTAL, LEADS, INTERVENCIÓN,
│   │                                    # DESEMPEÑO (⚠️ TODOS con datos hardcodeados)
│   └── ui/                              # 9 primitivas shadcn/ui:
│                                        # badge, button, card, dialog, dropdown-menu,
│                                        # input, select, skeleton, tooltip
│
├── contexts/
│   ├── AuthContext.tsx                  # Supabase session + dashboardRole (admin|staff)
│   ├── ChatContext.tsx                  # contacts[], messages[], realtime subscriptions
│   ├── UIContext.tsx                    # toasts, notifications (alerts table), Web Notifications,
│   │                                    # AudioContext sound, mark-as-read
│   └── CrmContext.tsx                   # Shim: compone Auth+Chat+UI y re-exporta useCrm()
│
├── lib/
│   ├── supabase.ts                      # createBrowserClient (Supabase SSR)
│   └── utils.ts                         # cn() = clsx + tailwind-merge
│
├── next.config.js                       # Rewrites /api/* → Cloud Run URL + Sentry config
├── wrangler.toml                        # Cloudflare Pages: output dir, compat flags
├── sentry.client.config.ts              # DSN + tracesSampleRate=0.3
├── sentry.server.config.ts              # Server-side Sentry init
├── tailwind.config.js                   # shadcn/ui theme con CSS variables
├── postcss.config.js                    # autoprefixer
├── tsconfig.json                        # paths: @/* → ./*
├── components.json                      # shadcn/ui config (rsc:false, style:default)
└── package.json                         # 15 deps runtime + 8 devDeps
```

---

## 3. Modelo de Datos (Supabase PostgreSQL)

### Tablas

```sql
-- tenants: Nodo raíz multi-tenant. Cada fila = un negocio cliente del SaaS.
tenants (
    id UUID PK,
    name TEXT NOT NULL,
    ws_phone_id TEXT UNIQUE NOT NULL,     -- Meta Phone Number ID (enrutamiento webhook)
    ws_token TEXT NOT NULL,               -- WhatsApp permanent access token
    llm_provider TEXT CHECK IN ('openai','gemini'),
    llm_model TEXT,                       -- ej. 'gpt-4o-mini', 'o4-mini'
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT TRUE,       -- kill-switch global del tenant
    -- Campos Google Calendar OAuth (agregados post-schema):
    google_refresh_token_encrypted TEXT,  -- Fernet-encrypted refresh token
    google_calendar_email TEXT,
    google_calendar_status TEXT,          -- 'connected' | 'disconnected'
    google_calendar_connected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ
)

-- tenant_users: Mapea auth.users (Supabase Auth) → tenants para RLS.
tenant_users (
    id UUID PK,
    tenant_id UUID FK → tenants,
    user_id UUID FK → auth.users,
    UNIQUE(tenant_id, user_id)
)

-- contacts: Usuarios finales (pacientes/clientes de WhatsApp).
contacts (
    id UUID PK,
    tenant_id UUID FK → tenants,
    phone_number TEXT,
    name TEXT,
    bot_active BOOLEAN DEFAULT TRUE,      -- HITL kill-switch por contacto
    role TEXT CHECK IN ('cliente','staff','admin'),  -- RBAC
    status TEXT DEFAULT 'lead',
    is_processing_llm BOOLEAN DEFAULT FALSE,  -- Mutex debouncing lock
    metadata JSONB,                       -- CelluDetox score, clinical notes (usado por UpdatePatientScoringTool)
    last_message_at TIMESTAMPTZ,
    UNIQUE(tenant_id, phone_number)
)

-- messages: Historial conversacional. Trigger de Supabase Realtime para frontend.
messages (
    id UUID PK,
    contact_id UUID FK → contacts,
    tenant_id UUID FK → tenants,          -- Desnormalizado para RLS eficiente
    sender_role TEXT CHECK IN ('user','assistant','human_agent','system_alert'),
    content TEXT,
    timestamp TIMESTAMPTZ
)

-- alerts: Notificaciones del sistema (escalaciones, cancelaciones, triaje).
alerts (
    id UUID PK,
    tenant_id UUID FK → tenants,
    contact_id UUID FK → contacts (NULL OK),
    type TEXT,                            -- 'escalation', 'cancellation', etc.
    message TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ
)

-- test_feedback: Registros de QA del simulador de chat.
test_feedback (
    id UUID PK,
    tenant_id UUID,
    patient_phone TEXT,
    history JSONB,                        -- Array de mensajes simulados
    notes JSONB,                          -- Observaciones del tester
    tester_email TEXT,
    created_at TIMESTAMPTZ
)
```

### Row Level Security (RLS)

| Tabla | Política | Mecanismo |
|:---|:---|:---|
| tenants | SELECT/UPDATE solo si `id IN get_user_tenant_ids()` | Función SQL que consulta `tenant_users` filtrando por `auth.uid()` |
| contacts | SELECT/UPDATE/INSERT restringido por `tenant_id` | Mismo mecanismo |
| messages | SELECT/INSERT restringido por `tenant_id` | Mismo mecanismo |
| alerts | SELECT/UPDATE restringido por `tenant_id` | Mismo mecanismo |

**Nota:** El backend usa `SUPABASE_SERVICE_ROLE_KEY` que bypassea RLS. El webhook necesita escribir sin contexto de autenticación dentro del límite de 3 segundos de Meta.

### Supabase Realtime

Habilitado en tablas `contacts`, `messages` y `alerts`. El frontend suscribe tres channels:
- `chat_contacts_changes` → refresca lista de contactos
- `chat_messages_changes` → renderiza mensajes nuevos en el chat activo
- `alerts-realtime-ui` → toasts + Web Notifications + sonido

---

## 4. Despliegue

### Topología de Ramas

| Rama | Base de Datos | Frontend Deploy | Backend Deploy |
|:---|:---|:---|:---|
| `main` (producción) | Supabase Producción | Cloudflare Pages (auto-deploy) | Google Cloud Run (auto-deploy) |
| `desarrollo` | Supabase Desarrollo | — | — |

> **⚠️ PENDIENTE DE VERIFICACIÓN:** La configuración exacta de los auto-deploys (build commands, env variables inyectadas, service accounts, regiones) y los esquemas/datos de ambas bases de datos (producción y desarrollo) requieren auditoría directa. Esta verificación se realizará cuando se conecten las herramientas MCP de Supabase y Google Cloud Run.

### Backend (Google Cloud Run)

**Dockerfile** (multi-stage en `./Dockerfile` raíz + symlink en `Backend/deploy/Dockerfile`):
1. **Builder:** `python:3.11-slim` → instala pip + venv en `/opt/venv` → `pip install .` desde pyproject.toml
2. **Runner:** `python:3.11-slim` → usuario no-root `crmuser` → copia solo `/opt/venv` + `app/`
3. **CMD:** `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log`

Variables de entorno requeridas (inyectadas via GCP Secret Manager):
```
ENVIRONMENT=production
WHATSAPP_VERIFY_TOKEN=<token>
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
SUPABASE_URL=https://<id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=ey...
GOOGLE_SERVICE_ACCOUNT_JSON=<json>     # Credenciales de Google Calendar
DISCORD_WEBHOOK_URL=<url>              # Opcional
RESEND_API_KEY=<key>                   # Opcional
SENTRY_DSN=<dsn>
GOOGLE_OAUTH_CLIENT_ID=<id>           # Opcional, para OAuth Calendar
GOOGLE_OAUTH_CLIENT_SECRET=<secret>    # Opcional
GOOGLE_OAUTH_REDIRECT_URI=<uri>        # Opcional
```

### Frontend (Cloudflare Pages)

- Build output: configurado en `wrangler.toml` como `.vercel/output/static`
- Variables de entorno compiladas (`NEXT_PUBLIC_*`):
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `NEXT_PUBLIC_SENTRY_DSN`

### Desarrollo Local

```bash
# Backend
cd Backend
python -m venv venv && source venv/bin/activate  # o .\venv\Scripts\activate (Windows)
pip install -e ".[dev]"
cp .env.example .env  # configurar variables
uvicorn app.main:app --reload --port 8000

# Frontend
cd Frontend
npm install
cp .env.local.example .env.local  # configurar variables
npm run dev  # localhost:3000

# Docker (Backend)
docker-compose -f Backend/deploy/docker-compose.yml up --build
```

---

## 5. Patrones de Diseño Implementados

| Patrón | Implementación | Ubicación |
|:---|:---|:---|
| **Strategy** | `LLMFactory` instancia proveedores intercambiables por tenant (`OpenAIStrategy`, `GeminiStrategy`, `MockStrategy`) | `modules/intelligence/router.py` |
| **Registry** | `ToolRegistry` registra herramientas al boot sin modificar use_cases | `modules/intelligence/tool_registry.py` |
| **Pub/Sub** | `EventBus` con `asyncio.Queue` desacopla efectos secundarios (alertas, emails, Discord) del pipeline principal | `core/event_bus.py` |
| **Singleton** | `SupabasePooler._instance`, `MetaGraphAPIClient._http_client`, `_GoogleServiceSingleton._service` | Respectivos módulos |
| **Abstract Base** | `AITool(ABC)` y `LLMStrategy(ABC)` definen contratos de extensión | `tools/base.py`, `router.py` |
| **Background Tasks** | FastAPI `BackgroundTasks` para responder 200 OK a Meta inmediatamente | `communication/routers.py` |
| **Mutex Lock** | `is_processing_llm` en tabla contacts previene llamadas LLM concurrentes por contacto | `communication/use_cases.py` |
| **RBAC** | `caller_role` inyectado en kwargs de tools regula visibilidad y permisos | `scheduling/tools.py` |
| **Zero-Trust** | Delete appointment verifica phone match; escalation valida caller_phone | `scheduling/tools.py` |
| **Inversion of Control** | TenantContext inyectado como parámetro, no global | `api/dependencies.py` |

---

## 6. Problemas Conocidos y Deuda Técnica

### Críticos (bloquean go-live)

| # | Problema | Archivo(s) | Detalle |
|:--|:---|:---|:---|
| 1 | **CORS abierto a `*`** | `main.py:122` | Cualquier origen puede hacer requests al backend. Debe restringirse al dominio de CF Pages |
| 2 | **Traceback completo en HTTP 500** | `main.py:302,321` | Stack trace expuesto a clientes. Información de paths, tablas, estructura interna |
| 3 | **Endpoints sin autenticación** | `main.py:148-256` | `/api/simulate`, `/api/test-feedback`, `/api/calendar/*`, `/api/debug-*` accesibles públicamente |
| 4 | **Frontend sin auth guard** | `(panel)/layout.tsx` | El panel monta `CrmProvider` sin verificar sesión. Accesible sin login y con cuentas no autorizadas |
| 5 | **Logout no invalida sesión** | `Sidebar.tsx:17` | Hace `window.location.href = '/login'` sin llamar `supabase.auth.signOut()`. La sesión persiste |
| 6 | **`TriageEvaluator` roto** | `evaluator.py:24` | Referencia `tenant.staff_notification_number` que no existe en `TenantContext` |

### Arquitecturales

| # | Problema | Detalle |
|:--|:---|:---|
| 7 | `main.py` tiene 6 endpoints inline (326 LOC) | Viola Screaming Architecture. Calendar y simulate deberían tener routers propios |
| 8 | Tool results inyectados como `role: "user"` | OpenAI espera `role: "tool"` con `tool_call_id`. Puede confundir el modelo |
| 9 | Solo 1 pasada de tool calling | Si el LLM necesita tool → response → tool (cadena), falla |
| 10 | Calendar IDs hardcodeados en fallback | `google_client.py:67-70`. Todos los tenants sin config comparten calendarios |
| 11 | `ProactiveWorker` es stub vacío | Loop con `pass` cada hora. Consume recursos sin utilidad |
| 12 | `BaseRepository` no se usa | `repositories/base.py` define CRUD genérico pero nada lo importa |
| 13 | Dashboard con datos hardcodeados | `DashboardView.tsx` muestra KPIs estáticos, no queries reales |
| 14 | Reportes/FinOps son mocks | Datos estáticos, etiquetas "Próximamente" |
| 15 | 3 instancias de Supabase client en frontend | Cada Context crea su propio `createClient()` con WebSocket independiente |
| 16 | Next.js rewrites no aplican en Cloudflare | `next.config.js` define rewrites que solo funcionan en servidor Node.js, no static export |
| 17 | `email_service.py` usa `os.getenv` directo | No pasa por `Settings` centralizado. Destinatarios hardcodeados |
| 18 | EventBus loop infinito sin graceful shutdown | `start_processing()` no tiene mecanismo de cancelación limpia |

---

## 7. Archivos Innecesarios: Inventario y Justificación

### Raíz del repositorio

| Archivo | Razón para eliminar |
|:---|:---|
| `check_realtime.py` | Script de diagnóstico one-off. Ya está en `.gitignore` |
| `debug_gpt5_tools.py` | Script de debugging puntual. Ya en `.gitignore` |
| `extract.py`, `extracted_logs.txt` | Extractor de logs temporal |
| `read_utf16_logs.py` | Utilidad de lectura de logs legacy |
| `run_logs.bat` | Script Windows para correr logs |
| `test_gpt5_tools_feed.py` | Test manual aislado |
| `test_history.py`, `tmp_check_history.py` | Scripts de verificación one-off |
| `error.log`, `error_ai.txt`, `error_all.txt`, `error_bg.txt`, `error_clean.txt`, `error_latest.txt` | Logs de debugging local. No deben estar en repo |
| `curl_stderr.txt`, `curl_stdout.txt` | Output de curl guardado. Diagnóstico temporal |
| `last_msg.json`, `logs.json`, `logs_clean.json`, `orch_logs.json`, `output_debug.json` | Dumps de diagnóstico JSON |
| `schema.sql`, `schema_dev.sql` | Schemas locales probablemente desactualizados vs la BD real |
| `prod_data.sql`, `prod_public.sql`, `prod_schema.sql` | **⚠️ RIESGO:** dumps de producción con datos reales. No rastreados pero presentes |
| `implementation_plan.md`, `task.md` | Artefactos de sessiones de IA anteriores |
| `setup_dev_env.py` | Script de setup ya en `.gitignore` |

### Backend (`Backend/`)

| Archivo | Razón para eliminar |
|:---|:---|
| `report.md` (155KB), `reporter.py` | Reporte generado automáticamente + script generador. Dev artifacts |
| `latency_analysis.md` | Análisis de latencia puntual de una sesión pasada |
| `payload.json`, `simpayload.json`, `temp_contacts.json` | Payloads de test hardcodeados |
| `deploy_to_prod.sql` | Migration one-off ejecutada |
| `temp_fix_rls.sql` | Fix temporal de RLS ya aplicado |
| `tmp_clean_db.py` | Script de limpieza destructivo temporal |
| `run_all_migrations.py` | Script que ejecuta migrations sueltas. Sin sistema formal |
| `pytest.log` | Output de test runner |
| `Procfile` | Artefacto de Heroku/Railway. **No se usa** — el deploy es via Dockerfile |
| `.env.prod` | Variables de producción locales. No debería estar en filesystem |
| `Backend/temp/` | Directorio con `.env.new`, credenciales duplicadas, base64 de Google creds |
| `Backend/credentials/` | Archivo JSON de Google Service Account local. En prod se usa ENV var |
| `Backend/scripts/maintenance/` | `delete_contacts.py`, `migrate_contacts.py` — scripts destructivos one-off |
| `Backend/scripts/setup/` | `db_setup.py`, `enable_rt.py`, `fix_pub_pooler.py`, `fix_rls.py` — ejecutados y ya no relevantes |
| `Backend/sql/` | `fix_rls_production.sql`, `recreate_feedback_table.sql` — migrations ejecutadas |
| `Backend/app/infrastructure/database/repositories/base.py` | Código muerto: `BaseRepository` no es importado por ningún módulo |

### Frontend (`Frontend/`)

| Archivo | Razón para eliminar |
|:---|:---|
| `report.md` (274KB), `reporter.py` | Reporte generado + generador. Dev artifacts |
| `Frontend/scripts/refactor_page.py` | Script de refactoring one-off |
| `Frontend/.git/` | **⚠️ Directorio .git independiente dentro del frontend**. Indica que era un subrepo separado que se integró. Puede causar conflictos con el .git raíz |

---

## 8. Variables de Entorno

### Backend (14 variables en `config.py`)

| Variable | Requerida | Default | Uso |
|:---|:---|:---|:---|
| `ENVIRONMENT` | No | `"development"` | Controla formato de logs (JSON vs human) |
| `LOG_LEVEL` | No | `"DEBUG"` | Nivel de logging |
| `MOCK_LLM` | No | `False` | Bypasea LLM reales con MockStrategy |
| `WHATSAPP_VERIFY_TOKEN` | **Sí** | — | Verificación del webhook de Meta |
| `OPENAI_API_KEY` | **Sí** | — | Autenticación OpenAI |
| `GEMINI_API_KEY` | **Sí** | — | Autenticación Gemini (requerida aunque adapter sea mock) |
| `SUPABASE_URL` | **Sí** | — | URL del proyecto Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | **Sí** | — | Clave admin que bypassea RLS |
| `DISCORD_WEBHOOK_URL` | No | `None` | URL para alertas Discord |
| `RESEND_API_KEY` | No | `None` | API key para emails vía Resend |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | No | `None` | JSON string de credenciales de Google Calendar |
| `GOOGLE_OAUTH_CLIENT_ID` | No | `None` | OAuth client para calendar multi-tenant |
| `GOOGLE_OAUTH_CLIENT_SECRET` | No | `None` | OAuth secret |
| `GOOGLE_OAUTH_REDIRECT_URI` | No | `None` | URI de callback OAuth |
| `PROACTIVE_INTERVAL` | No | `3600` | Intervalo del worker proactivo (segundos) |

### Frontend (3 variables compiladas)

| Variable | Uso |
|:---|:---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL de Supabase para el browser client |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Clave anónima (restricta por RLS) |
| `NEXT_PUBLIC_SENTRY_DSN` | DSN de Sentry para error tracking |

---

## 9. Backlog y Roadmap

### ✅ Completado

| Feature | Estado | Notas |
|:---|:---|:---|
| Screaming Architecture (DDD + Puertos/Adaptadores) | ✅ | Separación `modules/` vs `infrastructure/` |
| Resolución de Body webhook (`Body(...)` en FastAPI) | ✅ | Evita consumo doble del stream |
| Protección I/O bloqueante (`asyncio.to_thread`) | ✅ | Google Calendar sync calls envueltas |
| Logging async (QueueHandler + JSON prod) | ✅ | Dual mode dev/prod |
| Connection pooling Meta (httpx singleton) | ✅ | 50 keepalive / 100 max connections |
| SSO Frontend (Google via Supabase Auth) | ✅ | Login page funcional |
| Seguridad de secretos (GCP Secret Manager) | ✅ | Variables inyectadas desde secrets |
| Multi-LLM dinámico (Strategy + Factory) | ✅ | OpenAI funcional. Gemini registrado pero mock |
| Debouncing cognitivo (Mutex `is_processing_llm`) | ✅ | Lock en BD + sleep(3) para consolidar ráfagas |
| Inyección dinámica de contexto (role, name, status) | ✅ | En system prompt antes de inferencia |
| Sistema de alertas real-time (tabla `alerts`) | ✅ | Reemplazó al viejo "chat de sistema". Toasts + Web Notifications + sonido |
| EventBus async (Pub/Sub in-memory) | ✅ | asyncio.Queue con fire-and-forget listeners |
| Tool Registry extensible (7 tools) | ✅ | Register pattern con Zero-Trust en delete |
| Google Calendar integration (FreeBusy + CRUD + Round-Robin) | ✅ | 2 boxes, slots 09:00-19:00 |
| Google Calendar OAuth multi-tenant | ✅ | Flow completo con Fernet encryption |
| Triaje clínico (keyword matching) | ✅ parcial | Funcional pero `TriageEvaluator` tiene bug (ver §6) |
| Patient Scoring (CelluDetox) | ✅ | `UpdatePatientScoringTool` escribe en `metadata` jsonb |
| Discord alertas (Webhooks) | ✅ | Embeds con traceback en errores |
| Email alertas (Resend) | ✅ | Notificación al negocio en escalaciones |
| Sentry (Backend + Frontend) | ✅ parcial | Inicializado pero frontend tiene instrumentation deshabilitada |
| Vista Chats con realtime | ✅ | `ChatArea.tsx` funcional con WebSocket |
| Vista Agenda con Google Calendar | ✅ | `AgendaView.tsx` lee/escribe eventos reales |
| Vista Pacientes (CRM table) | ✅ | `PacientesView.tsx` con datos reales de Supabase |
| Vista Configuración (LLM + prompt + OAuth) | ✅ | Funcional, persiste en tabla `tenants` |
| Simulador de chat | ✅ | `TestChatArea.tsx` + contacto especial `56912345678` |
| Docker multi-stage (non-root) | ✅ | Imagen limpia, usuario `crmuser` |

### 🚨 P0 — Bloqueantes (necesarios para go-live)

| Feature | Descripción |
|:---|:---|
| **Auth guard en frontend** | Verificar sesión en `(panel)/layout.tsx`. Sin sesión → redirect a login. Cuenta sin tenant → acceso denegado |
| **Logout real** | `Sidebar.tsx` debe llamar `supabase.auth.signOut()` antes de redirigir |
| **Restringir CORS** | Cambiar `allow_origins=["*"]` a `dash.tuasistentevirtual.cl`, `ohno.tuasistentevirtual.cl`, `localhost:3000` |
| **Eliminar tracebacks de HTTP 500** | No exponer stack traces en producción |
| **Autenticación de endpoints internos** | Proteger `/api/simulate`, `/api/calendar/*`, `/api/test-feedback`, `/api/debug-*` |
| **Fix error de conexión Agenda** | Diagnosticar y resolver: proxy route, GCal credentials, o singleton init |
| **Fix carga del Chat** | Diagnosticar si chat carga correctamente en producción |
| **Monitoreo completo** | Sentry en frontend + backend → Discord. Cualquier error en cualquier pieza = notificación |

### ⚡ P1 — Mejoras Arquitecturales (post go-live)

| Feature | Descripción |
|:---|:---|
| Implementar Gemini adapter real | O desregistrarlo del factory. No urgente: solo usamos OpenAI para la primera clienta |
| Fix TriageEvaluator | Agregar `staff_notification_number` a `TenantContext` o usar default |
| Extraer endpoints de `main.py` a routers | Calendar, simulate, feedback → routers dedicados |
| Tool observation format correcto | Enviar como `role: "tool"` con `tool_call_id` (spec OpenAI) |
| Multi-turn tool calling | Loop recursivo hasta que el LLM no pida más tools |
| Calendar IDs dinámicos por tenant | Columna `calendar_ids jsonb[]` en tabla `tenants` |
| Singleton Supabase en frontend | Un solo `createClient()` compartido entre contexts |
| TypeScript types | Interfaces para Contact, Message, Alert, Tenant (eliminar `any`) |
| Caché TenantContext | `cachetools` TTL=5min en `dependencies.py` |

### 💰 P2 — Plataforma Comercial (no urgente)

| Feature | Descripción |
|:---|:---|
| Telemetría FinOps (consumo LLM) | Capturar `prompt_tokens` + `completion_tokens` por request. Tabla `tenant_billing_logs` |
| Dashboard con datos reales | Queries a Supabase en vez de números hardcodeados. **Actualmente 100% hardcodeado** |
| Reportes funcionales | Gráficos de conversación, conversión, tiempos de respuesta. **Actualmente mock "en construcción"** |
| FinOps funcional | Métricas de costo. **Actualmente datos estáticos** |
| Panel SuperAdmin | Vista maestra con márgenes por tenant y kill-switch de morosos |
| RLS vinculante (eliminar políticas públicas) | Usar `auth.uid()` exclusivamente vía `get_user_tenant_ids()` |
| CI/CD pipeline (GitHub Actions) | Lint + type-check + tests antes de merge a main. `.github/workflows/` está vacío |
| Tests unitarios | ProcessMessageUseCase, ToolRegistry, SchedulingService. Test directory vacío |
| Migraciones SQL formales | Sistema de versionamiento (Prisma, dbmate, o manual ordenado) |
| ProactiveWorker real | Recordatorios -24h, follow-ups +24h, re-engagement 30 días |
| Rotar credenciales | Las API keys están en texto plano en `.env` local. En `.gitignore` pero deben rotarse |

---

## 10. Dependencias

### Backend (`pyproject.toml`)

```
fastapi>=0.110.0           uvicorn>=0.27.1
supabase>=2.3.6            openai>=1.14.0
google-generativeai>=0.4.1 pydantic>=2.6.4
pydantic-settings>=2.2.1   httpx>=0.27.0
python-dotenv>=1.0.1        orjson>=3.9.15
pytz>=2024.1               google-api-python-client>=2.122.0
google-auth-oauthlib>=1.2.0 sentry-sdk[fastapi]>=2.0.0
cryptography>=42.0.0

Dev: pytest>=8.0.0, pytest-asyncio>=0.23.5, coverage>=7.4.0
```

### Frontend (`package.json`)

```
next@14.1.4                react@^18.2.0
@supabase/ssr@^0.1.0       @supabase/supabase-js@^2.98.0
@sentry/nextjs@^10.47.0    lucide-react@^0.364.0
date-fns@^4.1.0            recharts@^3.8.1
radix-ui@^1.4.3            shadcn@^4.1.2
class-variance-authority    clsx@^2.1.1
tailwind-merge@^2.6.1      tailwindcss-animate@^1.0.7
tw-animate-css@^1.4.0      pg@^8.20.0

Dev: typescript@^5.4.3, tailwindcss@^3.4.3, eslint@^8.57.0
```