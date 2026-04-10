# AI WhatsApp CRM — Documentación Técnica

> **SaaS Multi-tenant B2B** para automatizar la primera línea de atención al cliente vía WhatsApp mediante LLMs con Function Calling, bajo paradigma Human-In-The-Loop (HITL).

> **⚠️ REGLA #1 — DOCS FIRST:** Antes de implementar CUALQUIER cambio, fix, o integración, consultar la documentación oficial más actualizada del servicio correspondiente (Supabase, Cloudflare, Google Cloud, Sentry, Meta, etc.). No asumir comportamiento basado en experiencia previa — las APIs cambian entre versiones. Esta regla existe porque su violación ya costó horas de debugging innecesario (ver §0.1).

---

## 0. Estado Actual del Proyecto (2026-04-10 04:20 CLT)

**Estado global:** 🟡 En estabilización — Fases 0-3F completas. Phase 3 E2E Validation finalizada con todos los bugs resueltos. Listo para Phase 4 (Separación Prod/Dev).

| Pieza | Estado | Detalle |
|:---|:---|:---|
| **Backend (Cloud Run)** | 🟢 Operativo + Observable | Rev `00052-7xc`, 100% tráfico. Sentry ✅, Discord alertas ✅, Cloud Logging JSON ✅ |
| **Frontend (CF Workers)** | 🟢 Operativo + Observable | OpenNext (Workers). Sentry SDK captura errores ✅. CF Workers Logs ✅. Deploy auto via Workers Builds |
| **BD Producción** | 🟢 Funcional | RLS activo. Migraciones aplicadas: `alerts` RLS + `is_read` + GCal OAuth columns |
| **BD Desarrollo** | 🟢 Sincronizada | `is_read` column aplicada. Schema funcional |
| **Rama `main`** | 🟢 Al día | Auto-deploy backend (Cloud Build) + frontend (Workers Builds) |
| **Rama `desarrollo`** | ⚪ Detrás de main | Se sincroniza DESPUÉS de estabilizar main |
| **Monitoreo Backend** | 🟢 Completo | Sentry + Discord + Cloud Logging JSON — todo verificado |
| **Monitoreo Frontend** | 🟢 Completo | Sentry SDK (client errors) ✅ + CF Workers Logs (server/routing) ✅ |

### Plan de Go-Live (en ejecución)

```
FASE 0: Pre-flight ✅ ──► FASE 1: Estabilizar main ✅ ──► FASE 2: Monitoreo ✅ ──► FASE 3: E2E Interno 🔄 ──► FASE 4: Separación Prod/Dev ──► FASE 5: WhatsApp + Go-Live
```

| Fase | Objetivo | Estado |
|:---|:---|:---|
| **Fase 0** | Limpiar working tree, inspeccionar diffs sospechosos, tag de restauración | ✅ Completada |
| **Fase 1A** | Infraestructura: env vars, backend URLs, SQL migrations | ✅ Completada |
| **Fase 1B** | Seguridad: auth guard, logout, CORS, traceback removal | ✅ Completada |
| **Fase 1C** | **Auth PKCE callback** | ✅ **Completada** — login/logout funcional (ver §0.1) |
| **Fase 1D** | Backend deploy (Cloud Build) | ✅ **Completada** — 3 root causes resueltos (ver §4) |
| **Fase 2A** | Sentry Backend (FastAPI) | ✅ **Completada** — errores capturados en Sentry + Discord (ver §0.2) |
| **Fase 2B** | Sentry Frontend (Next.js) | ✅ **Completada** — Client-side via `instrumentation-client.ts` en OpenNext Workers (ver §0.2, §0.3) |
| **Fase 2D** | Discord alertas | ✅ **Completada** — Captain Hook webhook funcional |
| **Fase 2E** | OpenNext Migration (CF Pages → Workers) | ✅ **Completada** — ver §0.3 |
| **Fase 2F** | Sentry Coverage Hardening + CORS + RLS DELETE + GCal secret | ✅ **Completada** — commit `5ba489d` (ver §0.4) |
| **Fase 3** | E2E validation interno + bug fixes + observability hardening | ✅ **Completada** — 3E (bug fixes) + 3F (post-testing fixes). OTel deferred (Workers Free). Ver §0.6 |
| **Fase 4** | Separación prod/dev: ecosistemas 100% independientes (`dash.` prod, `ohno.` dev), 2 backends, 2 frontends, 2 BDs | Pendiente |
| **Fase 5** | Suite de simulación webhook Meta (desconectado) → tag `v1.0` → conectar WhatsApp → validación live | Pendiente |

### Bugs Resueltos (Fase 3)

| ID | Bug | Resolución | Estado |
|:---|:---|:---|:---|
| **BUG-1** | LLM responde sobre herramientas sin ejecutarlas (silent failure) | 4-layer fix: (L1) INTERNAL_TOOL_RULES inmutables, (L2) detección "Silence Pattern", (L3) forced tool_choice para escalación, (L4) logging mejorado | ✅ |
| **BUG-2** | Character counter en `/config` mostraba `/2000` | Actualizado a `/4000` con thresholds amber (>3000) y rojo (>3500). Sentry warning si >4000 (save NO bloqueado) | ✅ |
| **BUG-3** | Tool errors: no Sentry/Discord + LLM mentía sobre resultados | Business errors (relay natural) vs crashes (human notified). Todos `status:error` → Sentry+Discord con tenant_id | ✅ |
| **MISC-2** | Missing `import sentry_sdk` en `google_client.py` | Import top-level + eliminación de 5 inline imports redundantes | ✅ |
| **OTEL-1** | CF Workers OTel export a Sentry | Requiere Workers Paid ($5/mo). Comentado en `wrangler.toml`. Observabilidad no bloqueada | ✅ Deferred |
| **3F-1** | Sentry events sin tenant_id | `sentry_sdk.set_tag("tenant_id", ...)` al inicio del orquestador | ✅ |
| **3F-2** | Discord alerts sin tenant en título | Todos los `send_discord_alert()` incluyen `Tenant {id}` | ✅ |
| **3F-3** | Three dots (typing indicator) visible con IA pausada | Condición `&& selectedContact.bot_active` en ChatArea + TestChatArea | ✅ |

### Backlog Técnico (Phase 6+ — NO implementar ahora)

| Prioridad | Área | Tarea |
|:---|:---|:---|
| **🔴 Alta** | Config | **Tenant Assistant Config Revamp**: `/config` como controlador integral (prompt + modelo + tools on/off), sandbox como testing ground seguro, versionado con rollback, toggle de herramientas en tiempo real |
| **🔴 Alta** | UI/Agenda | **Agenda Visual Revamp**: layout mobile overflow, navegación días/semanas/meses, responsive redesign, gestos touch |
| **🟡 Media** | Observability | Bot pause notifications → Sentry + Discord + admins/staff del tenant |
| **🟡 Media** | Observability | Paused chat inbound alerts — actualmente ignora silenciosamente |
| **🟡 Media** | Backend | Tool Registry tracking: logging de tools registradas, schemas, historial |
| **🟡 Media** | DB/Backend | Tenant Config Versioning: tabla `tenant_config_versions` con snapshots JSON |
| **🟡 Media** | WhatsApp | Refrescar token Meta API (401 en Sentry) — necesario para Phase 5 |
| **🟢 Baja** | LLM | BUG-4: CheckMyAppointments hallucination — LLM inventa detalles de citas |



---

## 0.1. Autenticación OAuth PKCE — Solución Documentada (NO MODIFICAR sin leer esto)

> **⚠️ IMPORTANTE:** La solución de autenticación actual FUNCIONA y está respaldada 1:1 por la [documentación oficial de Supabase para SSR con Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs). Si algo deja de funcionar, revisar primero estos docs antes de cambiar código.

### Cómo funciona el flujo (paso a paso)

```
1. Usuario clickea "Continuar con Google" en /login
   └─► signInWithOAuth() de @supabase/ssr createBrowserClient
       ├─ Genera code_verifier aleatorio
       ├─ Lo guarda como cookie (document.cookie, path=/, SameSite=Lax)
       └─ Redirige a Supabase /auth/v1/authorize

2. Supabase redirige a Google OAuth → usuario aprueba

3. Google redirige a Supabase /auth/v1/callback
   └─ Supabase genera un auth code propio

4. Supabase redirige a nuestra app: /auth/confirm?code=XXX
   (configurado via redirectTo en signInWithOAuth)

5. /auth/confirm/page.tsx (client component) se carga
   └─ createBrowserClient() singleton se auto-inicializa
      └─ _initialize() detecta ?code=XXX en window.location
         ├─ Lee code_verifier de la cookie
         ├─ Llama exchangeCodeForSession() internamente
         └─ Dispara onAuthStateChange con evento SIGNED_IN

6. Nuestro listener en /auth/confirm escucha SIGNED_IN
   └─ router.replace('/dashboard') → usuario autenticado ✅
```

### Root cause del error anterior

El error `PKCE code verifier not found in storage` ocurría porque llamábamos `exchangeCodeForSession()` **manualmente** en un `useEffect`. Pero `createBrowserClient` es un **singleton** que ejecuta `_initialize()` automáticamente. Esta auto-inicialización ya detectaba el `?code=` en la URL y llamaba `exchangeCodeForSession` internamente, **consumiendo el code_verifier**. Cuando nuestro `useEffect` lo llamaba después, el verifier ya no existía.

### La solución (oficial)

**NO llamar `exchangeCodeForSession()` manualmente.** En su lugar:
1. Dejar que el singleton se auto-inicialice (esto ocurre al hacer `createClient()`)
2. Escuchar `onAuthStateChange` para el evento `SIGNED_IN`
3. Redirigir al dashboard cuando se recibe el evento

**Archivos involucrados:**

| Archivo | Rol |
|:---|:---|
| `lib/supabase.ts` | Browser client singleton (`createBrowserClient` de `@supabase/ssr`) |
| `app/login/page.tsx` | Llama `signInWithOAuth({redirectTo: '/auth/confirm'})` |
| `app/auth/callback/route.ts` | Thin redirect: `?code=` → `/auth/confirm?code=` (preserva params) |
| `app/auth/confirm/page.tsx` | **Solo escucha `onAuthStateChange`**, NO llama `exchangeCodeForSession` |

### Docs de referencia

- [Supabase SSR + Next.js — Creating a Client](https://supabase.com/docs/guides/auth/server-side/nextjs)
- [Supabase SSR — Advanced Guide (PKCE)](https://supabase.com/docs/guides/auth/server-side/advanced-guide)
- [Ejemplo oficial Next.js](https://github.com/supabase/supabase/tree/master/examples/auth/nextjs)
- [`@supabase/ssr` v0.10.0](https://www.npmjs.com/package/@supabase/ssr) — almacena code_verifier en cookies, NO en localStorage

### Regla de oro para futuras implementaciones

> **Siempre consultar la documentación oficial MÁS ACTUALIZADA de cada servicio (Supabase, Cloudflare, Google Cloud) ANTES de implementar o debuggear.** No asumir comportamiento basándose en experiencia previa — las APIs cambian entre versiones.

---

## 0.2. Frontend Sentry + Next.js 15 Upgrade — Solución Documentada (NO MODIFICAR sin leer esto)

> **⚠️ CRÍTICO — NO HACER DOWNGRADE de Next.js por debajo de 15.x. Romperá la integración de Sentry en el frontend.**

> **Estado: ✅ FUNCIONAL** — Sentry captura errores del frontend en producción (confirmado 2026-04-09).

### Por qué se hizo el upgrade (Next.js 14.1.4 → 15.5.15)

Sentry SDK v10 requiere que la inicialización del cliente se haga en `instrumentation-client.ts`, una **convención de archivo de Next.js 15+** que NO existe en Next.js 14. El archivo anterior `sentry.client.config.ts` está **DEPRECADO** por Sentry.

Además, `next.config.js` tenía `disableClientInstrumentation: true`, que **deshabilitaba silenciosamente toda la captura de errores del frontend**. Esta flag se puso originalmente para prevenir crashes de Edge runtime en Next.js 14.

**Nota histórica:** Después del upgrade, Sentry seguía SIN capturar errores debido a que `@cloudflare/next-on-pages` (el viejo adapter) no procesaba `instrumentation-client.ts`. El problema se resolvió migrando a OpenNext (§0.3).

### Archivos involucrados

| Archivo | Rol | Estado |
|:---|:---|:---|
| `instrumentation-client.ts` | **Inicialización de Sentry en el browser** — reemplaza al deprecado `sentry.client.config.ts` | ✅ NUEVO — NO ELIMINAR |
| `app/global-error.tsx` | **Captura errores de render de React** — sin esto, errores de componentes no llegan a Sentry | ✅ NUEVO — NO ELIMINAR |
| `next.config.js` | Config de Sentry — **SIN `disableClientInstrumentation`** | ✅ MODIFICADO |
| `sentry.client.config.ts` | ❌ ELIMINADO — deprecado por Sentry SDK v10 | ❌ NO RE-CREAR |
| `sentry.server.config.ts` | ❌ ELIMINADO — server-side Sentry ahora funciona via OpenNext Workers runtime | ❌ NO RE-CREAR |

### Lo que NO se debe hacer (causa regresiones)

1. **NO re-crear `sentry.client.config.ts`** — está deprecado. Sentry SDK v10 usa `instrumentation-client.ts`
2. **NO agregar `disableClientInstrumentation: true`** a `next.config.js` — mata toda captura de errores
3. **NO hacer downgrade de Next.js a 14.x** — `instrumentation-client.ts` no existe en 14
4. **NO eliminar `app/global-error.tsx`** — necesario para capturar errores de render de React
5. **NO eliminar la exportación `onRouterTransitionStart`** de `instrumentation-client.ts` — necesario para tracing de navegación
6. **NO revertir a `@cloudflare/next-on-pages`** — deprecated, no soporta `instrumentation-client.ts`. Usar OpenNext.

### Docs de referencia

- [Sentry Next.js Manual Setup](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) — explica `instrumentation-client.ts`
- [Sentry Next.js on Cloudflare](https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/) — requisitos de Cloudflare Workers
- [Next.js instrumentation-client.ts](https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client) — convención de archivo
- [Next.js 15 Upgrade Guide](https://nextjs.org/docs/app/building-your-application/upgrading/version-15) — breaking changes
- [Sentry global-error.tsx](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/#capture-react-render-errors) — captura de render errors

### Breaking changes manejados en el upgrade

| Cambio | De | A | Por qué |
|:---|:---|:---|:---|
| Next.js | 14.1.4 | 15.5.15 | Habilitar `instrumentation-client.ts` para Sentry |
| React | 18.x | 19.x | Requerido por Next.js 15 |
| react-dom | 18.x | 19.x | Requerido por Next.js 15 |
| @types/react | 18.x | 19.x | Tipos de React 19 |
| @types/react-dom | 18.x | 19.x | Tipos de React 19 |
| eslint-config-next | 14.1.4 | 15.5.15 | Debe coincidir con versión de Next.js |
| lucide-react | 0.364.0 | 1.7.0 | v0.364 solo soporta React 16-18. v1.x agrega React 19. [Migration](https://lucide.dev/guide/react/migration) — solo se removieron brand icons (no usamos ninguno) |

---

## 0.3. OpenNext Migration (Cloudflare Pages → Workers) — Solución Documentada (NO MODIFICAR sin leer esto)

> **⚠️ CRÍTICO — NO revertir a `@cloudflare/next-on-pages`. Está DEPRECATED y NO soporta `instrumentation-client.ts` (required by Sentry SDK v10).**

> **Estado: ✅ FUNCIONAL** — Frontend desplegado como Cloudflare Worker via OpenNext. Sentry ✅, Workers Logs ✅, API rewrites ✅, custom domain ✅.

### Por qué se migró

| Problema con `@cloudflare/next-on-pages` | Solución con OpenNext |
|:---|:---|
| **DEPRECATED** por Cloudflare | OpenNext es el [reemplazo oficialmente recomendado](https://opennext.js.org/cloudflare/get-started) |
| NO soporta `instrumentation-client.ts` | OpenNext procesa TODOS los file conventions de Next.js 15 |
| Static export only (sin SSR, sin rewrites server-side) | Full Node.js-compatible runtime en Workers (SSR, rewrites, middleware) |
| No server-side Sentry | Server-side Sentry funciona via `@sentry/nextjs` + `compatibility_date >= 2025-08-16` |

### Arquitectura actual del frontend

```
GitHub Push (main)
       │
       ▼
Workers Builds (CI/CD automático en Cloudflare)
  ├─ Build: npx opennextjs-cloudflare build
  │    └─ Lee "Variables de compilación" para incrustar NEXT_PUBLIC_* y BACKEND_URL
  └─ Deploy: npx wrangler deploy --keep-vars
       └─ Despliega .open-next/worker.js como Cloudflare Worker
       └─ Preserva "Variables de ejecución" del dashboard (--keep-vars)

Cloudflare Worker (ia-whatsapp-crm)
  ├─ Sirve Next.js via OpenNext adapter
  ├─ Variables de entorno via process.env (nodejs_compat)
  ├─ API /api/* → rewrites a Cloud Run backend (compilados en routes-manifest.json)
  ├─ Sentry cliente via instrumentation-client.ts
  ├─ Sentry servidor via @sentry/nextjs (requiere compatibility_date >= 2025-08-16)
  └─ Observabilidad:
       ├─ Workers Logs → CF Dashboard (console.log + invocación) — 3 días retención free tier
       ├─ OTel Traces → Sentry (via destino "sentry-traces") [pendiente configurar destinos]
       └─ OTel Logs → Sentry (via destino "sentry-logs") [pendiente configurar destinos]
```

### Archivos clave del frontend (OpenNext)

| Archivo | Rol | ⚠️ Regla |
|:---|:---|:---|
| `wrangler.toml` | Config del Worker: nombre, assets, compat date, observabilidad | NO cambiar `compatibility_date` a < 2025-08-16 (rompe Sentry) |
| `open-next.config.ts` | Config de OpenNext (mínima, usa defaults) | No se necesita modificar normalmente |
| `next.config.js` | Rewrites `/api/*` → backend + Sentry build config + `initOpenNextCloudflareForDev()` | NO agregar `disableClientInstrumentation: true` |
| `.env.local` | **SOLO para desarrollo local** (`BACKEND_URL=http://localhost:8000`) | **EN .gitignore** — si se comitea, el build de producción redirige API calls a localhost y CRASHEA |
| `.dev.vars` | Variables de Cloudflare para desarrollo local (`NEXTJS_ENV=development`) | EN .gitignore |
| `instrumentation-client.ts` | Sentry SDK init en el browser | NO ELIMINAR |
| `app/global-error.tsx` | Captura React render errors para Sentry | NO ELIMINAR |

### Variables de entorno — Estrategia (CRÍTICO entender esto)

> **Doc oficial:** [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars#production)

Hay **DOS tipos** de variables que se configuran en **DOS lugares diferentes** del dashboard de Cloudflare:

| Tipo | Dónde se configura | Cuándo se lee | Variables |
|:---|:---|:---|:---|
| **Build variables** | Configuración → Compilaciones → Variables y secretos | Durante `next build` (incrustadas en JS) | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SENTRY_DSN`, `BACKEND_URL` |
| **Runtime variables** | Configuración → Variables y secretos | Cuando el Worker procesa requests | `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SENTRY_DSN` |

> **⚠️ `BACKEND_URL` es SOLO build variable.** Se usa en `next.config.js` para compilar los rewrites de `/api/*` en el `routes-manifest.json`. Si no se configura, el fallback (`https://ia-backend-prod-ftyhfnvyla-ew.a.run.app`) se usa. Si `.env.local` existe con `BACKEND_URL=http://localhost:8000` y se comitea a git, **CRASHEA el Worker entero** con `TypeError: Expected "8000" to be a string` (bug descubierto 2026-04-09).

> **⚠️ `--keep-vars` en el deploy command es CRÍTICO.** Sin él, `wrangler deploy` borra las runtime variables del dashboard. [Doc oficial](https://opennext.js.org/cloudflare/howtos/env-vars#runtime-variables).

### Configuración de `wrangler.toml` — Explicación campo por campo

```toml
name = "ia-whatsapp-crm"              # Nombre del Worker en CF dashboard
main = ".open-next/worker.js"          # Output de opennextjs-cloudflare build
compatibility_date = "2025-08-16"      # >= 2025-08-16 REQUERIDO para Sentry (https.request)
compatibility_flags = ["nodejs_compat"] # Habilita process.env, Buffer, etc.
upload_source_maps = true              # Stack traces legibles en Sentry

[assets]
directory = ".open-next/assets"        # Static assets (JS, CSS, images)
binding = "ASSETS"                     # Binding name para el Worker

[[services]]
binding = "WORKER_SELF_REFERENCE"      # Self-reference para OpenNext routing
service = "ia-whatsapp-crm"

[observability]                        # CF Workers Logs + OTel export
enabled = true
head_sampling_rate = 1                 # 100% → captura TODAS las requests

[observability.logs]
enabled = true
invocation_logs = true                 # Log de cada request con URL, method, status
destinations = [ "sentry-logs" ]       # Exporta a Sentry via OTLP (nombre debe coincidir con CF dashboard)

[observability.traces]
enabled = true
destinations = [ "sentry-traces" ]     # Exporta traces a Sentry via OTLP
```

**Docs de referencia para wrangler.toml:**
- [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/)
- [Export to Sentry via OTel](https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/sentry/)
- [Sentry Cloudflare compatibility_date](https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/)
- [Sentry source maps](https://docs.sentry.io/platforms/javascript/guides/cloudflare/#step-3-add-readable-stack-traces-with-source-maps-optional)

### Observabilidad — 3 capas

| Capa | Qué captura | Estado | Doc |
|:---|:---|:---|:---|
| **Sentry SDK** (`@sentry/nextjs`) | Errores JS en browser + server, React render crashes, navigation traces | ✅ Funcional | [Sentry Next.js](https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/) |
| **CF Workers Logs** | `console.log`, invocación logs (URL, status, duration) en CF dashboard | ✅ Funcional | [Workers Logs](https://developers.cloudflare.com/workers/observability/logs/workers-logs/) |
| **OTel Export → Sentry** | Traces/logs nativos de CF exportados a Sentry via OTLP | ⚠️ Pendiente crear destinos en CF dashboard | [Export to Sentry](https://developers.cloudflare.com/workers/observability/exporting-opentelemetry-data/sentry/) |

### Lo que NO se debe hacer (causa regresiones)

1. **NO revertir a `@cloudflare/next-on-pages`** — deprecated, no soporta `instrumentation-client.ts`
2. **NO bajar `compatibility_date`** por debajo de `2025-08-16` — rompe Sentry SDK (`https.request` no disponible)
3. **NO quitar `upload_source_maps = true`** — sin esto, stack traces en Sentry son ilegibles
4. **NO quitar `--keep-vars`** del deploy command — borra variables de entorno del dashboard
5. **NO comitear `.env.local`** a git — contiene `BACKEND_URL=http://localhost:8000` que crashea producción
6. **NO poner `NEXT_PUBLIC_*` en `[vars]` de `wrangler.toml`** — deben ir en el dashboard (build + runtime)
7. **NO quitar `nodejs_compat`** — requerido por Next.js 15 y Sentry SDK para `process.env`, `Buffer`, etc.
8. **NO quitar `initOpenNextCloudflareForDev()`** de `next.config.js` — necesario para dev local

### Docs de referencia (OpenNext migration)

- [OpenNext Get Started (existing apps)](https://opennext.js.org/cloudflare/get-started#existing-nextjs-apps)
- [OpenNext Env Vars](https://opennext.js.org/cloudflare/howtos/env-vars)
- [OpenNext Dev & Deploy](https://opennext.js.org/cloudflare/howtos/dev-deploy)
- [Workers Builds Configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
- [CF Workers Env Vars](https://developers.cloudflare.com/workers/configuration/environment-variables/)

### Rollback

- **Git tag:** `pre-opennext-migration` (commit `f1494c9`)
- **Persistent KI:** `knowledge/opennext-migration-rollback/artifacts/rollback.md`
- **Comando:** `git reset --hard pre-opennext-migration && git push --force-with-lease`

---

## 0.4. Sentry Coverage Hardening + CORS + RLS DELETE — Solución Documentada (2026-04-09)

> **Estado: ✅ FUNCIONAL** — 17 archivos modificados, 30+ catch blocks instrumentados. Commit `5ba489d`. Verificado en producción.

### Problema descubierto

Fallos "silenciosos" sistémicos: más de 30 bloques `catch` en backend y frontend registraban errores en consola/Cloud Logging pero **nunca los enviaban a Sentry**. Esto hacía imposible debuggear en producción fallos de herramientas LLM, errores de credenciales, y operaciones de datos del frontend.

**El punto ciego más crítico:** `tool_registry.execute_tool()` — TODAS las 7 herramientas LLM fallaban silenciosamente aquí. El catch block logeaba localmente y tragaba la excepción sin enviarla a Sentry.

### Lo que se hizo

**Backend (6 archivos, 12 catch blocks):**

| Archivo | Ubicación | Fix |
|:---|:---|:---|
| `tool_registry.py` | `execute_tool()` | `sentry_sdk.capture_exception()` + `set_context("tool_execution", {tool_name, kwargs_keys})` |
| `tools.py` | `EscalateHumanTool` | Reemplazó `except Exception: pass` con logging + Sentry |
| `tools.py` | `UpdatePatientScoringTool` | Agregó `sentry_sdk.capture_exception()` |
| `use_cases.py` | 4 catch blocks | Contact creation, msg persistence, tool loop, cleanup — todos con Sentry |
| `google_client.py` | Carga de credenciales | Agregó `sentry_sdk.capture_exception()` |
| `meta_graph_api.py` | Errores HTTP + red | `sentry_sdk.capture_exception()` + `set_context("meta_graph_api", ...)` |
| `main.py` | 3 endpoints | `/api/simulate`, `/api/test-feedback`, `/api/calendar/book` |

**Frontend (11 archivos, 18 catch blocks):**

| Archivo | Catches | Fix |
|:---|:---|:---|
| 4 API proxy routes | 4 | `Sentry.captureException()` + `captureMessage()` en respuestas non-ok |
| `TestChatArea.tsx` | 5 | localStorage, msg insert, Supabase, simulate, bot toggle, sandbox feedback |
| `ChatArea.tsx` | 2 | DB insert, simulation trigger |
| `AgendaView.tsx` | 2 | fetchEvents, handleBook |
| `TestConfigPanel.tsx` | 2 | fetchTenantConfig, handleSavePrompt |
| `GlobalFeedbackButton.tsx` | 1 | handleSend |
| `admin-feedback/page.tsx` | 1 | handleDelete (no tenía try/catch, se agregó) |
| `auth/confirm/page.tsx` | 1 | Error de sesión PKCE → `Sentry.captureMessage()` |

**Fixes adicionales incluidos en el mismo commit:**

| Fix | Detalle |
|:---|:---|
| **CORS** | `main.py`: reemplazó `ia-whatsapp-crm.pages.dev` con `ia-whatsapp-crm.tomasgemes.workers.dev` |
| **RLS DELETE** | Migración Supabase: políticas `messages_delete_own` + `test_feedback_delete_tenant` para `authenticated` con scope `get_user_tenant_ids()` |
| **GCal Secret Manager** | `GOOGLE_CALENDAR_CREDENTIALS` v4: re-subido como JSON raw (era base64, causaba fallo de `json.loads()`) |

### Resultado

- El botón "Enviar Prueba" ahora sí elimina mensajes del sandbox (RLS DELETE policy)
- Google Calendar funciona correctamente (credenciales raw JSON)
- CORS acepta requests del Workers URL correcto
- **Todo error en cualquier catch block llega a Sentry** — eliminamos puntos ciegos

### Lo que NO se debe hacer

1. **NO quitar `sentry_sdk.capture_exception()`** de ningún catch block — volverá a crear puntos ciegos
2. **NO usar `except: pass`** — siempre loguear + enviar a Sentry
3. **NO subir secretos codificados en base64** a Secret Manager — el backend espera JSON raw
4. **NO revertir el CORS** al URL viejo de Pages (`ia-whatsapp-crm.pages.dev`) — el frontend ya es Workers

### Docs de referencia

- [Sentry Python: capture_exception](https://docs.sentry.io/platforms/python/usage/#capturing-errors)
- [Sentry Python: Enriching Events](https://docs.sentry.io/platforms/python/enriching-events/context/)
- [Sentry Next.js: captureException](https://docs.sentry.io/platforms/javascript/guides/nextjs/usage/)
- [Cloud Run: Configure Secrets](https://cloud.google.com/run/docs/configuring/services/secrets)

---

### Herramientas MCP Configuradas

Para auditoría y gestión de infraestructura, se dispone de 4 MCP servers:

| MCP | Config Key | Protocolo | Función |
|:---|:---|:---|:---|
| Google Cloud Run | `cloudrun` | CLI (`npx @google-cloud/cloud-run-mcp`) | Servicios, env vars, logs, deploys del backend |
| Supabase Producción | `supabase-prod` | HTTP (`mcp.supabase.com`, ref: `nemrjlimrnrusodivtoa`) | Schema, RLS, datos, realtime de BD producción |
| Supabase Desarrollo | `supabase-dev` | HTTP (`mcp.supabase.com`, ref: `nzsksjczswndjjbctasu`) | Schema, datos de BD desarrollo |
| Cloudflare | `cloudflare` | CLI (`npx mcp-remote → bindings.mcp.cloudflare.com`) | Config de Cloudflare Workers, dominios, bindings |

Config en: `~/.gemini/antigravity/mcp_config.json`

### Identificadores de Infraestructura

| Recurso | Identificador | Notas |
|:---|:---|:---|
| Cloud Run service URL | `ia-backend-prod-ftyhfnvyla-ew.a.run.app` | Hardcodeada en `next.config.js` como fallback |
| GCP project ID | `saas-javiera` | Para Cloud Build, IAM, etc. |
| Supabase prod project | `nemrjlimrnrusodivtoa` | `nemrjlimrnrusodivtoa.supabase.co` |
| Supabase dev project | `nzsksjczswndjjbctasu` | `nzsksjczswndjjbctasu.supabase.co` |
| Cloudflare Worker | `ia-whatsapp-crm` | En `wrangler.toml`. **Worker, NO Pages** |
| CF Workers URL | `ia-whatsapp-crm.tomasgemes.workers.dev` | URL directa del Worker |
| Frontend dominio prod | `dash.tuasistentevirtual.cl` | Custom domain en CF Workers |
| Frontend dominio dev | `ohno.tuasistentevirtual.cl` | Pendiente de configurar |
| GitHub repo | `YggrYergen/ia-whatsapp-crm` | Auto-deploys: backend (Cloud Build) + frontend (Workers Builds) |
| Sentry DSN | `b5b7a769848286fc...@o4511179991416832` | Hardcodeado en `instrumentation-client.ts` + como build/runtime var en CF dashboard |

---

## 0.5. Frontend Routes, Pages & Test Chat Sandbox — Mapa Completo

> **El sistema tiene 8 rutas de panel (layout compartido) + 3 rutas standalone (login, config, auth).**

### Rutas del Panel (`/(panel)/layout.tsx` — requiere auth)

| Ruta | Sidebar Label | Componente Principal | Tipo |
|:---|:---|:---|:---|
| `/dashboard` | Panel | Dashboard con métricas, actividad reciente | Todos |
| `/chats` | Chats | **Dual-mode:** Regular vs Test Sandbox (ver abajo) | Todos |
| `/agenda` | Agenda | `AgendaView` — Google Calendar con acciones de booking | Todos |
| `/pacientes` | CRM | Lista de contactos con datos de Supabase | Todos |
| `/reportes` | Reportes | Reportes y métricas (desktop only en sidebar) | Desktop |
| `/finops` | FinOps | Operaciones financieras (desktop only en sidebar) | Desktop |
| `/admin-feedback` | Auditoría Dev | Tabla `test_feedback` — resultados de pruebas de sandbox | Admin only¹ |
| `/config` | ⚙️ (standalone) | **Configuración Global**: LLM provider/model, system prompt, Google Calendar | Todos |

¹ Visible solo para: `tomasgemes@gmail.com`, `alejandra.tamar.rojas@gmail.com`, `instagramelectrimax@gmail.com`

### `/chats` — Sistema Dual-Mode (CRÍTICO entender esto)

La ruta `/chats` tiene **dos modos completamente distintos** que se activan según el contacto seleccionado:

```
ContactList (izquierda)
     │
     ├── Contacto regular → ChatArea.tsx + ClientProfilePanel.tsx
     │     └── Chat estándar: enviar/recibir mensajes, pausar bot, ver perfil
     │
     └── Contacto test (phone === '56912345678') → TestChatArea.tsx + TestConfigPanel.tsx
           └── Sandbox Auditoría: simular conversaciones, agregar notas, enviar feedback
```

### `TestChatArea.tsx` — Botones de Acción del Sandbox

La barra inferior (action bar) del sandbox tiene 5 botones primarios + inline note system:

| Botón | Acción | Backend Route | Efecto |
|:---|:---|:---|:---|
| 🗑️ **DESCARTAR PRUEBA** | `confirm()` → limpia state `messages` | — | Solo limpia frontend, no borra de DB |
| ✉️ **ENVIAR PRUEBA (FINALIZAR)** | POST history + notes al backend, luego DELETE mensajes del contacto en DB, reset notas en localStorage | `/api/test-feedback` | Guarda en tabla `test_feedback`, limpia sandbox completamente |
| ✨ **CAMBIAR MODELO** | Placeholder (no conectado) | — | Solo renderiza, sin acción |
| ⚙️ **CONFIGURACIÓN** | `setShowDesktopInfo(true)` | — | Abre `TestConfigPanel` |
| ⋯ **MÁS OPCIONES** | Placeholder (no conectado) | — | Solo renderiza, sin acción |

**Inline Note System:** Al clickear un mensaje de IA, se abre un `textarea` inline. "Guardar Nota" persiste en `localStorage('sandbox_notes')` y muestra un indicador visual (dot amarillo) sobre el mensaje.

### `TestConfigPanel.tsx` — Panel Config del Agente

| Sección | Función | Persistencia |
|:---|:---|:---|
| Status card (gradient indigo/violet) | Muestra nombre del tenant + estado del bot (EJECUTANDO/EN PAUSA) | Realtime Supabase |
| System Prompt textarea | Editar instrucciones de la IA para el tenant. Botón "GUARDAR CAMBIOS" | Supabase `tenants.system_prompt` |
| Warning banner | Advertencia sobre impacto de cambios en el prompt | — |
| Metrics card | Contexto 95%, Acierto A+ | Estático/placeholder |

**Realtime subscription**: El panel se suscribe a `postgres_changes` en la tabla `tenants` (filtro `id=eq.{tenant_id}`) para actualizar el prompt si se modifica externamente (ej: desde `/config`).

### `/config` — Configuración Global del Tenant

| Sección | Campos | Persistencia |
|:---|:---|:---|
| Cerebro del Asistente | LLM Provider (OpenAI/Gemini), LLM Model (dinámico por provider), System Prompt (con character counter) | `tenants.llm_provider`, `tenants.llm_model`, `tenants.system_prompt` |
| Google Calendar | Estado de conexión (Conectado/Desconectado), email, botones Connect/Disconnect | `tenants.google_calendar_status`, `tenants.google_calendar_email` |
| Custom LLM CTA | "Solicitar Custom LLM" | — (marketing) |

**Modelos disponibles por provider:**
- OpenAI: `o4-mini`, `gpt-5-mini`, `gpt-4o-mini` (legacy)
- Gemini: `gemini-3.1-pro-preview`, `gemini-3.1-flash-lite-preview`

### `/admin-feedback` — Tabla de Resultados de Auditoría

- Fetch: `SELECT * FROM test_feedback WHERE tenant_id = {user_tenant}`
- Muestra: `history` (JSON conversación), `notes` (observaciones del tester), `tester_email`, `created_at`
- Acciones: botón DELETE para limpiar rows

### Sidebar Navigation (`components/Layout/Sidebar.tsx`)

| Elemento | Tipo | Visibilidad |
|:---|:---|:---|
| 7 nav items (Panel, Chats, Agenda, CRM, Reportes, FinOps, Dev) | Links | Algunos desktop-only |
| Notification bell | Toggle `NotificationFeed` | Mobile + Desktop |
| Config (⚙️) | Link a `/config` | Desktop only |
| Logout | `signOut()` → redirect `/login` | Desktop only |

---

## 0.6. Fase 3 E2E Verification — Hallazgos y Bugs Activos (2026-04-09)

> **Estado: 51/65 items verificados.** Dos bugs críticos identificados que deben resolverse antes de conectar WhatsApp.

### Matriz de Verificación (resumen)

| Sub-fase | Items | Verificados | Pendientes | Estado |
|:---|:---|:---|:---|:---|
| **3A: UI/Sandbox** (8 páginas + sandbox) | ~30 | ~28 | Logout, responsive mobile | ✅ |
| **3B: LLM Tools** (7 tools) | 7 | 5 | UpdateAppointment, DeleteAppointment | ⚠️ BUG-1 |
| **3C: E2E Pipeline** (simulator→frontend) | 4 | 4 | — | ✅ |
| **3D: Observability** (Sentry→Discord) | 5 | 4 | CF Workers Logs visual check | ✅ |

### BUG-1: LLM Tool-Calling Silent Failure — Root Cause Analysis

**Síntoma:** Al enviar "Necesito hablar con un humano, tengo una queja seria" por el sandbox, el LLM respondió:
> "Entiendo que necesitas asistencia humana. Permíteme un momento para escalar tu solicitud. Voy a notificar a un agente..."

Pero **NO ejecutó** `request_human_escalation`. Verificado en DB:
- `contacts.bot_active` permaneció en `true` (debería ser `false`)
- No se creó registro en tabla `alerts`
- `messages` muestra el texto pero sin tool call

**Mismo patrón con `update_patient_scoring`:** el LLM respondió sobre "celulitis leve" pero `contacts.metadata` quedó `{}`.

**Root Cause Técnico (código actual):**

```python
# openai_adapter.py:29 — tool_choice="auto" permite al LLM elegir NO llamar tools
tool_choice="auto" if tools else None

# use_cases.py:143-144 — el orchestrator loguea has_tool_calls pero NO valida
response_dto = await llm_strategy.generate_response(...)
logger.info(f"✅ [ORCH] LLM Reply received. ToolCalls={response_dto.has_tool_calls}")
# Si has_tool_calls=False, el orchestrator simplemente usa response_dto.content como texto
# NO hay detección de que el LLM "mintió" sobre haber ejecutado una acción
```

**Por qué `tool_choice="auto"` no es suficiente:**
- Según [docs oficiales de OpenAI](https://platform.openai.com/docs/guides/function-calling): `"auto"` = el modelo decide si llamar tools o responder en texto. Es el default.
- `"required"` = el modelo DEBE llamar al menos una tool. Pero fuerza tool calls incluso cuando no son necesarias.
- La solución NO es simplemente cambiar a `"required"` (rompería conversaciones normales de chat).

**Fix requerido (basado en docs oficiales):**
1. **Detección post-LLM:** Si `has_tool_calls=False` pero el contenido de texto contiene patrones que indican intención de tool (ej: "escalar", "notificar a un agente", "actualizar scoring"), loguear WARNING + alertar a Sentry/Discord
2. **Logging mejorado:** Loguear siempre el contenido completo de la respuesta LLM junto con `has_tool_calls` para trazabilidad
3. **Evaluar `tool_choice` condicional:** Para ciertos prompts (ej: forzar escalation con keywords clínicos como ya hace `force_escalation` en `use_cases.py:72-75`), podría usarse `tool_choice={"type":"function","name":"request_human_escalation"}` para forzar la llamada

**Contexto clave para el fix:**
- `use_cases.py:72-75`: Ya existe `force_escalation` que detecta keywords clínicos → ya se inyecta "⚠️ RIESGO" en el system prompt. Pero esto solo SUGIERE al LLM que use la tool, no lo FUERZA.
- `openai_adapter.py:29`: `tool_choice` es donde se controla el comportamiento
- `tool_registry.py:23-35`: `execute_tool()` ya tiene Sentry + logging — el problema es que nunca llega aquí porque el LLM no emitió el tool call

### BUG-2: Character Counter Limit Incorrecto

**Síntoma:** `/config` muestra `3099 / 2000 caracteres` en ROJO. El prompt actual tiene 3097 chars.

**Root Cause:**
```
Frontend/app/config/page.tsx:160-161:
  {tenant.system_prompt?.length > 1000 ? 'text-rose-600 ...' : 'text-slate-400'}
  {tenant.system_prompt?.length || 0} / 2000 caracteres
```

**Fix:** Cambiar `2000` → `4000` en display, threshold rojo `> 1000` → `> 3500`. Agregar warning Sentry/Discord si se intenta guardar un prompt > 4000.

### Tools Verificadas (Phase 3B)

| Tool | Nombre interno | Estado | Evidencia |
|:---|:---|:---|:---|
| CheckAvailabilityTool | `get_merged_availability` | ✅ | Function call ejecutada, GCal API consultada |
| BookAppointmentTool | `book_round_robin` | ✅ | Function call ejecutada, evento creado en GCal |
| CheckMyAppointmentsTool | `get_my_appointments` | ✅ | Function call ejecutada, respuesta "no tienes citas agendadas" |
| UpdateAppointmentTool | `update_appointment` | 🔲 No testeada | Requiere cita existente para el contacto sandbox |
| DeleteAppointmentTool | `delete_appointment` | 🔲 No testeada | Requiere cita existente para el contacto sandbox |
| EscalateHumanTool | `request_human_escalation` | ⚠️ BUG-1 | LLM respondió en texto sin ejecutar function call |
| UpdatePatientScoringTool | `update_patient_scoring` | ⚠️ BUG-1 | LLM respondió en texto sin ejecutar function call |

### Arquitectura de Tool-Calling (para contexto de debugging)

```
use_cases.py:137  →  tool_registry.get_all_schemas(provider)  →  7 tool JSON schemas
                                                                      ↓
use_cases.py:143  →  llm_strategy.generate_response(prompt, history, tools)
                                                                      ↓
openai_adapter.py:25-30  →  client.chat.completions.create(tools=tools, tool_choice="auto")
                                                                      ↓
                              ┌─── message.tool_calls exists? ───┐
                              │                                   │
                           YES (has_tool_calls=True)           NO (has_tool_calls=False)
                              │                                   │
                     use_cases.py:149-159                  use_cases.py:146
                     Execute each tool via                 reply_text = content ← SILENT FAILURE POINT
                     tool_registry.execute_tool()          (no validation that LLM should have called a tool)
```

---

## 1. Arquitectura del Sistema

Tres componentes distribuidos:

| Componente | Stack | Despliegue | Función |
|:---|:---|:---|:---|
| **Frontend** | Next.js 15.5.15 / React 19 / TailwindCSS 3.4 / shadcn/ui | Cloudflare Workers (OpenNext) | Panel CRM administrativo con realtime |
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
│                          Frontend (Cloudflare Workers / OpenNext)
                          Dashboard / Chats / Agenda                     │
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

Next.js 15 con App Router, shadcn/ui, TailwindCSS. Desplegado como **Cloudflare Worker via OpenNext** (ver §0.3).

```
Frontend/
├── app/
│   ├── layout.tsx                       # Root: Inter font, metadata "AI CRM Enterprise"
│   ├── global-error.tsx                 # ⚠️ NO ELIMINAR — captura render errors para Sentry
│   ├── page.tsx                         # Redirect → /dashboard
│   ├── globals.css                      # Tailwind directives + CSS vars (oklch) + scrollbar
│   ├── login/page.tsx                   # Google SSO via Supabase Auth
│   ├── auth/callback/                   # OAuth redirect handler (client-side, ver §0.1)
│   ├── config/page.tsx                  # Configuración: LLM provider/model selector,
│   │                                    # system prompt editor, Google Calendar OAuth connect
│   ├── api/                             # Next.js API routes (proxy al backend via rewrites)
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
├── components/                          # (same structure as before — ver §2)
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
├── next.config.js                       # Rewrites /api/* → Cloud Run + Sentry + initOpenNextCloudflareForDev()
│                                        # ⚠️ NO agregar disableClientInstrumentation: true
│                                        # ⚠️ BACKEND_URL must be set as build var (ver §0.3)
├── instrumentation-client.ts            # ⚠️ NO ELIMINAR — Sentry client init (ver §0.2)
├── wrangler.toml                        # CF Worker config: name, assets, compat, observability (ver §0.3)
├── open-next.config.ts                  # OpenNext config (minimal, uses defaults)
├── .env.local                           # ⚠️ SOLO dev local — EN .gitignore — NO COMITEAR
├── .dev.vars                            # Cloudflare dev vars — EN .gitignore
├── tailwind.config.js                   # shadcn/ui theme con CSS variables
├── postcss.config.js                    # autoprefixer
├── tsconfig.json                        # paths: @/* → ./*
├── components.json                      # shadcn/ui config (rsc:false, style:default)
└── package.json                         # 16 deps runtime + 9 devDeps
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
| messages | SELECT/INSERT/DELETE restringido por `tenant_id` | DELETE agregado en Phase 2F (policy `messages_delete_own`) — requerido para "Enviar Prueba" |
| alerts | SELECT/UPDATE restringido por `tenant_id` | Mismo mecanismo |
| test_feedback | DELETE restringido por `tenant_id` | Policy `test_feedback_delete_tenant` (Phase 2F) — requerido para admin-feedback page |

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
| `main` (producción) | Supabase Producción | Cloudflare Workers via OpenNext (Workers Builds auto-deploy) | Google Cloud Run (Cloud Build auto-deploy) |
| `desarrollo` | Supabase Desarrollo | — | — |

> **⚠️ PENDIENTE DE VERIFICACIÓN:** La configuración exacta de los auto-deploys (build commands, env variables inyectadas, service accounts, regiones) y los esquemas/datos de ambas bases de datos (producción y desarrollo) requieren auditoría directa. Esta verificación se realizará cuando se conecten las herramientas MCP de Supabase y Google Cloud Run.

### Backend (Google Cloud Run)

> **⚠️ DOCS FIRST — Cloud Run:** Antes de modificar CUALQUIER aspecto del deploy del backend (Dockerfile, Cloud Build, IAM, logging), consultar las docs oficiales vigentes:
> - [FastAPI Quickstart (Cloud Run)](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service) — estructura de proyecto oficial
> - [Continuous Deployment from Git](https://cloud.google.com/run/docs/continuous-deployment) — configuración de trigger Cloud Build
> - [Cloud Build IAM](https://cloud.google.com/build/docs/securing-builds/configure-access-control) — permisos requeridos
> - [Cloud Logging](https://cloud.google.com/logging/docs) — retención y acceso a logs
>
> **El deploy DEBE producir logs visibles.** Si un deploy falla sin logs, el problema de logging se resuelve PRIMERO.

#### Diagnóstico: 3 Root Causes del Deploy (todos resueltos 2026-04-08)

**Estado: ✅ RESUELTO — Pipeline completo Build→Push→Deploy funcionando. Revision `00046-hfx` sirviendo 100% tráfico, API 200 OK.**

**Root Cause 1 — Error `iam.serviceaccounts.actAs` (RESUELTO ✅):**
La cuenta de servicio del build NO tenía `roles/iam.serviceAccountUser`. Documentado en [Continuous Deployment docs](https://cloud.google.com/run/docs/continuous-deployment): la SA necesita `roles/cloudbuild.builds.builder` + `roles/run.admin` + **`roles/iam.serviceAccountUser`**.

**Root Cause 2 — Trigger sin paso de Deploy (RESUELTO ✅):**
El trigger original solo hacía `docker build` — no incluía pasos de Push ni Deploy. El [Cloud Build deploy docs](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run) especifica 3 pasos: Build → Push → Deploy (usando `gcr.io/google.com/cloudsdktool/cloud-sdk` con `gcloud run services update`).

**Root Cause 3 — Secretos no configurados en Secret Manager (RESUELTO ✅):**
Los deploys anteriores (via `gcloud run deploy --source .` con buildpacks) tenían las credenciales baked into la imagen. Con Dockerfile propio, los secretos deben estar en **Secret Manager** y configurados con `--update-secrets`. Doc: [Configure secrets](https://cloud.google.com/run/docs/configuring/services/secrets).

**Estructura del Dockerfile (REESTRUCTURADO ✅):**
El [FastAPI Quickstart](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-fastapi-service) espera directorio self-contained. Se movió `Dockerfile` a `Backend/Dockerfile`.

```
ANTES (no estándar):                  DESPUÉS (patrón oficial):
/Dockerfile  (referencia Backend/)    /Backend/Dockerfile  (self-contained)
  COPY Backend/pyproject.toml ...       COPY pyproject.toml ...
  COPY Backend/ ./                      COPY . ./
  COPY Backend/app/ ./app/              COPY app/ ./app/

Cloud Build trigger:                  Cloud Build trigger:
  Source: /Dockerfile                   Source: /Backend/Dockerfile
  Context: /                            Context: /Backend/
```

**IAM roles aplicados (2026-04-08) a `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`:**

| Role | Por qué (según docs) |
|:---|:---|
| `roles/cloudbuild.builds.builder` | Ejecutar builds en Cloud Build |
| `roles/run.admin` | Deployar revisiones a Cloud Run |
| `roles/iam.serviceAccountUser` | Actuar como la service identity del servicio Cloud Run (**causa raíz del error `iam.serviceaccounts.actAs`**) |
| `roles/storage.admin` | Escribir imágenes a Artifact Registry |
| `roles/developerconnect.readTokenAccessor` | Leer código del repo GitHub vía Developer Connect |
| `roles/secretmanager.secretAccessor` | Leer secretos de Secret Manager (aplicado **por secreto**, no a nivel proyecto) |

Comandos ejecutados:
```bash
gcloud projects add-iam-policy-binding saas-javiera \
  --member=serviceAccount:ia-calendar-bot@saas-javiera.iam.gserviceaccount.com \
  --role=roles/cloudbuild.builds.builder --condition=None

gcloud projects add-iam-policy-binding saas-javiera \
  --member=serviceAccount:ia-calendar-bot@saas-javiera.iam.gserviceaccount.com \
  --role=roles/run.admin --condition=None

gcloud projects add-iam-policy-binding saas-javiera \
  --member=serviceAccount:ia-calendar-bot@saas-javiera.iam.gserviceaccount.com \
  --role=roles/iam.serviceAccountUser --condition=None

# Secret Manager access (por cada secreto):
gcloud secrets add-iam-policy-binding SECRET_NAME --project=saas-javiera \
  --member="serviceAccount:ia-calendar-bot@saas-javiera.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Cloud Build Trigger — Configuración Exacta (verificada)

**Trigger ID:** `7458b935-6cd5-48e2-b12b-b7115947e39d`
**Nombre:** `cloudrun-ia-backend-prod-europe-west1-YggrYergen-ia-whatsapptny`
**Región:** `europe-west1`
**Service Account:** `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`
**Evento:** Push a branch `main`
**Repo:** `YggrYergen/ia-whatsapp-crm` (vía Developer Connect)

```yaml
# Cloud Build trigger config (exportada con gcloud beta builds triggers export)
# Docs: https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run
build:
  images:
  - europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/ia-backend-prod:latest
  options:
    logging: CLOUD_LOGGING_ONLY
  steps:
  - id: Build
    args:
    - build
    - -t
    - europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/ia-backend-prod:latest
    - -f
    - Backend/Dockerfile        # ← Dockerfile DENTRO de Backend/ (self-contained)
    - Backend                   # ← Build context = Backend/ (NO raíz del repo)
    name: gcr.io/cloud-builders/docker
  - id: Push
    args:
    - push
    - europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/ia-backend-prod:latest
    name: gcr.io/cloud-builders/docker
  - id: Deploy
    args:
    - run
    - services
    - update
    - ia-backend-prod
    - --image=europe-west1-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/ia-backend-prod:latest
    - --region=europe-west1
    entrypoint: gcloud
    name: gcr.io/google.com/cloudsdktool/cloud-sdk
```

> **⚠️ NO MODIFICAR** la configuración del trigger sin consultar [Cloud Build deploy docs](https://cloud.google.com/build/docs/deploying-builds/deploy-cloud-run). Los 3 pasos (Build → Push → Deploy) y las rutas (`-f Backend/Dockerfile`, contexto `Backend`) son intencionales y siguen el patrón oficial.

#### Configuración del Servicio Cloud Run

**Dockerfile** (multi-stage en `Backend/Dockerfile`, self-contained):
1. **Builder:** `python:3.11-slim` → instala pip + venv en `/opt/venv` → `pip install .` desde pyproject.toml
2. **Runner:** `python:3.11-slim` → usuario no-root `crmuser` → copia solo `/opt/venv` + `app/`
3. **CMD:** `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log`

**Secrets (via Secret Manager — [docs](https://cloud.google.com/run/docs/configuring/services/secrets)):**

Los secretos se configuran con `--update-secrets` (NO como plain env vars). La service account
(`ia-calendar-bot@`) necesita `roles/secretmanager.secretAccessor` en cada secreto.

| Env Var | Secret Manager Name | Requerido |
|:---|:---|:---|
| `WHATSAPP_VERIFY_TOKEN` | `WHATSAPP_VERIFY_TOKEN` | ✅ |
| `OPENAI_API_KEY` | `OPENAI_API_KEY` | ✅ |
| `GEMINI_API_KEY` | `GEMINI_API_KEY` | ✅ |
| `SUPABASE_URL` | `SUPABASE_URL` | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | `SUPABASE_SERVICE_ROLE_KEY` | ✅ |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | `GOOGLE_CALENDAR_CREDENTIALS` | Opcional |

Para configurar/actualizar secretos en el servicio:
```bash
gcloud run services update ia-backend-prod \
  --project=saas-javiera --region=europe-west1 \
  --update-secrets="WHATSAPP_VERIFY_TOKEN=WHATSAPP_VERIFY_TOKEN:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,SUPABASE_URL=SUPABASE_URL:latest,SUPABASE_SERVICE_ROLE_KEY=SUPABASE_SERVICE_ROLE_KEY:latest,GOOGLE_SERVICE_ACCOUNT_JSON=GOOGLE_CALENDAR_CREDENTIALS:latest"
```

**Env vars adicionales (plain, no secretos):**
```
ENVIRONMENT=production                  # Set en Dockerfile
RESEND_API_KEY=<key>                    # Plain env var en Cloud Run UI
SENTRY_DSN=<dsn>                        # Plain env var (TODO: migrar a Secret Manager)
DISCORD_WEBHOOK_URL=<url>               # Opcional
GOOGLE_OAUTH_CLIENT_ID=<id>             # Opcional
GOOGLE_OAUTH_CLIENT_SECRET=<secret>     # Opcional
GOOGLE_OAUTH_REDIRECT_URI=<uri>         # Opcional
```

> **⚠️ IMPORTANTE:** Los secretos se resuelven al momento de startup (no de build). Si se agrega un secreto nuevo, se debe: (1) crearlo en Secret Manager, (2) dar acceso a `ia-calendar-bot@` con `roles/secretmanager.secretAccessor`, (3) ejecutar `--update-secrets` en el servicio.

### Frontend (Cloudflare Workers — OpenNext)

> **Ver §0.3 para documentación completa de la arquitectura, variables de entorno, y observabilidad.**

- **Adapter:** OpenNext (`@opennextjs/cloudflare`)
- **Build:** `npx opennextjs-cloudflare build` → genera `.open-next/worker.js` + `.open-next/assets/`
- **Deploy:** `npx wrangler deploy --keep-vars` (auto via Workers Builds en push a `main`)
- **Workers Builds config:**
  - Directorio raíz: `Frontend`
  - Build command: `npx opennextjs-cloudflare build`
  - Deploy command: `npx wrangler deploy --keep-vars`
- **Variables de compilación** (se incrustan en JS durante build):
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `NEXT_PUBLIC_SENTRY_DSN`
  - `BACKEND_URL` — usado para compilar rewrites en routes-manifest.json
- **Variables de ejecución** (disponibles via `process.env` en el Worker):
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

# Frontend (con OpenNext + Wrangler dev)
cd Frontend
npm install
# .env.local ya tiene BACKEND_URL=http://localhost:8000 para dev
npm run dev  # localhost:3000 (Next.js dev con bindings de Cloudflare)

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

> **⚠️ DOCS FIRST — Debugging:** Antes de diagnosticar o corregir CUALQUIER problema listado abajo, consultar la documentación oficial del servicio involucrado. La solución del auth PKCE (§0.1) demostró que el problema y la solución estaban documentados en los docs oficiales de Supabase desde el principio.

## 6. Problemas Conocidos y Deuda Técnica

### Críticos (bloquean go-live)

| # | Problema | Archivo(s) | Detalle |
|:--|:---|:---|:---|
| ~~1~~ | ~~**CORS abierto a `*`**~~ | ~~`main.py:122`~~ | **RESUELTO** — Phase 1B (restringido a dominios específicos) + Phase 2F (actualizado a Workers URL) |
| 2 | **Traceback completo en HTTP 500** | `main.py:302,321` | Stack trace expuesto a clientes. Información de paths, tablas, estructura interna |
| 3 | **Endpoints sin autenticación** | `main.py:148-256` | `/api/simulate`, `/api/test-feedback`, `/api/calendar/*`, `/api/debug-*` accesibles públicamente |
| ~~4~~ | ~~**Frontend sin auth guard**~~ | ~~`(panel)/layout.tsx`~~ | **RESUELTO** — Phase 1B: AuthGuard implementado en layout |
| ~~5~~ | ~~**Logout no invalida sesión**~~ | ~~`Sidebar.tsx:17`~~ | **RESUELTO** — Phase 1B: `supabase.auth.signOut()` implementado |
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
| ~~16~~ | ~~Next.js rewrites no aplican en Cloudflare~~ | **RESUELTO** — OpenNext habilita rewrites server-side en Workers (ver §0.3) |
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

### Frontend (4 variables — ver §0.3 para estrategia completa)

| Variable | Tipo | Uso |
|:---|:---|:---|
| `NEXT_PUBLIC_SUPABASE_URL` | Build + Runtime | URL de Supabase para el browser client |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Build + Runtime | Clave anónima (restricta por RLS) |
| `NEXT_PUBLIC_SENTRY_DSN` | Build + Runtime | DSN de Sentry para error tracking |
| `BACKEND_URL` | **Build only** | URL del backend Cloud Run para compilar rewrites de `/api/*` |

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
| Sentry Backend | ✅ | `sentry_sdk.init()` en lifespan, `capture_exception` en handlers, context enrichment en pipeline. Verificado: issues visibles en Sentry dashboard |
| Sentry Frontend | ✅ | `instrumentation-client.ts` + `global-error.tsx`. Funciona via OpenNext Workers (ver §0.2, §0.3). Confirmado 2026-04-09 |
| Vista Chats con realtime | ✅ | `ChatArea.tsx` funcional con WebSocket |
| Vista Agenda con Google Calendar | ✅ | `AgendaView.tsx` lee/escribe eventos reales |
| Vista Pacientes (CRM table) | ✅ | `PacientesView.tsx` con datos reales de Supabase |
| Vista Configuración (LLM + prompt + OAuth) | ✅ | Funcional, persiste en tabla `tenants` |
| Simulador de chat | ✅ | `TestChatArea.tsx` + contacto especial `56912345678` |
| Docker multi-stage (non-root) | ✅ | Imagen limpia, usuario `crmuser` |
| OpenNext Migration (CF Pages → Workers) | ✅ | Migración completa. Rewrites, Sentry, observabilidad, Workers Builds CI/CD. Ver §0.3 |
| CF Workers Logs | ✅ | Invocation logs + error logs en CF Dashboard. Config en `wrangler.toml` [observability] |
| Sentry Coverage Hardening (Phase 2F) | ✅ | 17 archivos, 30+ catch blocks instrumentados. Backend + frontend. Commit `5ba489d` (2026-04-09) |
| RLS DELETE policies (messages + test_feedback) | ✅ | Migración Supabase `add_delete_rls_policies`. Habilita "Enviar Prueba" y eliminación en admin-feedback |
| CORS fix (Pages → Workers URL) | ✅ | `main.py`: `ia-whatsapp-crm.pages.dev` → `ia-whatsapp-crm.tomasgemes.workers.dev` |
| GCal Secret Manager fix | ✅ | `GOOGLE_CALENDAR_CREDENTIALS` v4: raw JSON (era base64). Calendar funcional |

### 🚨 P0 — Bloqueantes (necesarios para go-live)

| Feature | Descripción |
|:---|:---|
| **Auth guard en frontend** | Verificar sesión en `(panel)/layout.tsx`. Sin sesión → redirect a login. Cuenta sin tenant → acceso denegado |
| **Logout real** | `Sidebar.tsx` debe llamar `supabase.auth.signOut()` antes de redirigir |
| ~~**Restringir CORS**~~ | ~~Cambiar `allow_origins=["*"]` a dominios específicos~~ | ✅ **RESUELTO** — Phase 1B + Phase 2F |
| **Eliminar tracebacks de HTTP 500** | No exponer stack traces en producción |
| **Autenticación de endpoints internos** | Proteger `/api/simulate`, `/api/calendar/*`, `/api/test-feedback`, `/api/debug-*` |
| ~~**Fix error de conexión Agenda**~~ | ~~Diagnosticar y resolver: proxy route, GCal credentials, o singleton init~~ | ✅ **RESUELTO** — Phase 2E (OpenNext rewrites) + Phase 2F (GCal JSON fix) |
| ~~**Fix carga del Chat**~~ | ~~Diagnosticar si chat carga correctamente en producción~~ | ✅ **RESUELTO** — Funcional via OpenNext Workers |
| ~~**Monitoreo completo**~~ | ~~Sentry en frontend + backend → Discord. Cualquier error = notificación~~ | ✅ **RESUELTO** — Phase 2A + 2B + 2D + 2F |

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
next@15.5.15               react@^19.0.0      ← Upgraded from 14.1.4/18.x (ver §0.2)
@supabase/ssr@^0.10.0      @supabase/supabase-js@^2.98.0
@sentry/nextjs@^10.47.0    lucide-react@^1.7.0        ← Upgraded from 0.364.0 (React 19 peer dep)
date-fns@^4.1.0            recharts@^3.8.1
radix-ui@^1.4.3            shadcn@^4.1.2
class-variance-authority    clsx@^2.1.1
tailwind-merge@^2.6.1      tailwindcss-animate@^1.0.7
tw-animate-css@^1.4.0      pg@^8.20.0

Dev: typescript@^5.4.3, tailwindcss@^3.4.3, eslint@^8.57.0, eslint-config-next@15.5.15
```