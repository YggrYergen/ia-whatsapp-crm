# AI CRM — Production Stabilization Tasks

> **⚠️ REGLA INQUEBRANTABLE:** Toda implementación DEBE ser respaldada por la doc oficial más actualizada. Sin excepciones.

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

## Phase 2: Sentry Observability — EXHAUSTIVA ← NEXT

### 2A: Sentry Backend (FastAPI)
Docs: [Sentry FastAPI](https://docs.sentry.io/platforms/python/integrations/fastapi/)
- [ ] Leer docs oficiales
- [ ] Verificar DSN en env vars de Cloud Run
- [ ] Capturas: excepciones, background tasks, timeouts, errores Supabase, function calling, HITL
- [ ] Test: error de prueba llega a Sentry

### 2B: Sentry Frontend Client-Side
Docs: [Sentry Next.js](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [ ] Error Boundaries, fetch failures, WebSocket errors
- [ ] Por componente: Chat, Agenda, Contactos, Notificaciones
- [ ] Test: error de prueba llega a Sentry

### 2C: Sentry Frontend Server-Side
Docs: [Sentry Next.js on Cloudflare](https://docs.sentry.io/platforms/javascript/guides/cloudflare/frameworks/nextjs/)
- [ ] Evaluar compatibilidad con Cloudflare Pages / OpenNext

### 2D: Alertas
- [ ] Discord webhook para errores críticos, email fallback

---

## Phase 3: E2E Validation — EXHAUSTIVA (DESPUÉS de Sentry confirmado)

### 3A: Componentes CRM
- [ ] Dashboard, Chat, Agenda, Contactos, Configuración

### 3B: Herramientas LLM (TODAS)
- [ ] Inventariar todas las tools
- [ ] Test individual: invocación → ejecución → resultado → Sentry si falla

### 3C: Flujo E2E Completo
- [ ] WhatsApp webhook → LLM → tool → response → Realtime → frontend

---

## Phase 4: Environment Separation
- [ ] `desarrollo` branch auto-deploy

## Phase 5: Go-Live
- [ ] Meta webhook, E2E real, Sentry production validation, launch
