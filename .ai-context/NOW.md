# NOW.md — Working Memory
> **Tier 1 | Updated:** 2026-04-16 19:36 CLT
> **Session:** 6550aa28-99cc-4157-9055-8be1a1ecce4b
> **Branch:** `desarrollo` | **Last commit:** `132602d`

---

## §0 — Current Focus

**Multi-Tenant CRM Stabilization — Sandbox Reset + Sentry + Env Vars**
Sandbox "Reiniciar" button fixed (native `confirm()` blocked by edge runtime → replaced with React inline confirmation). Sentry frontend configuration corrected (`instrumentation.ts` + hardcoded org/project + auth token). Wrangler.toml now version-controls all runtime env vars.

---

## §1 — Session Work Log (2026-04-16 — Full Day)

| # | What | Commit |
|---|------|--------|
| 1 | Agenda real hours + progress bars | `3b28116` |
| 2 | Cinematic login: Vortex (920 particles) | `3b28116` |
| 3 | CLI animated text (Tektur, 15 phrases) | `3b28116` |
| 4 | Glassmorphic login card | `3b28116` |
| 5 | README §2/§3/§4/§10 updated | `3b28116` |
| 6 | Observability audit — 0 silent blocks | manual |
| 7 | DB reset → fresh newcomer (instagramelectrimax) | DEV SQL |
| 8 | **BUG FIX** PGRST116 → `.maybe_single()` | `c5d4573` |
| 9 | **BUG FIX** Welcome step bypass → always 'welcome' when !isSetupComplete | `c5d4573` |
| 10 | **BUG FIX** "Contacto" check blob missing in ConfigProgress | `c5d4573` |
| 11 | **BUG FIX** Login mobile white border → `h-[100dvh]` | `c5d4573` |
| 12 | **BUG FIX** NoneType on provision → `if onb_res is None` | `d7f2a76` |
| 13 | **NEW** `_provision_generic_fallback()` — 1 service + 1 resource + scheduling | `d7f2a76` |
| 14 | **BUG FIX** WelcomeStep mobile overflow → `overflow-y-auto` + smaller sizes | `d7f2a76` |
| 15 | **BUG FIX** Provision circle → full green ring on final step | `d7f2a76` |
| 16 | **NEW** Sandbox `Enviar Prueba` button + per-bubble annotations → `test_feedback` | `83ae0f3` |
| 17 | **PROD FIX** `is_setup_complete` column missing on PROD → applied migration | direct SQL |
| 18 | **BUG FIX** Vortex black bars mobile → canvas uses container dims not `window.innerHeight` | `66b4f16` |
| 19 | **BUG FIX** `tenant_onboarding` UPDATE → upsert (survives reset users) | `007ad79` |
| 20 | **BUG FIX** Wrong columns in fallback (`resource_type`, `advance_booking_days`) → fixed to real schema | `007ad79` |
| 21 | **BUG FIX** Duplicate key on double-submit → upsert `on_conflict` | `007ad79` |
| 22 | DB reset (Round 5) | DEV SQL |
| 23 | **SECURITY** Tenant-scoped DashboardView, PacientesView, AgendaView | `9ca7af2` |
| 24 | **SECURITY** Renamed Pacientes → Clientes across UI | `9ca7af2` |
| 25 | **BUG FIX** Config page crash on pre-render → direct auth query pattern | `9ca7af2` |
| 26 | **BUG FIX** Sandbox initRef boolean → tenantId-aware re-init on tenant switch | `7561ba9` |
| 27 | **BUG FIX** Sandbox handleReset tenant_id scoping + 3-channel error reporting | `7561ba9` |
| 28 | **NEW** `instrumentation.ts` for server-side Sentry capture | `d356dcb` |
| 29 | **CONFIG** Hardcoded Sentry org/project in next.config.js + authToken from env | `d356dcb` |
| 30 | **BUG FIX** Sandbox Reiniciar: `confirm()` blocked by Edge runtime → React inline double-click confirmation | `3915990` |
| 31 | **CONFIG** wrangler.toml `[vars]` — version-controlled runtime env vars | `132602d` |
| 32 | **NEW** TD-7 added to BACKLOG (JWT app_metadata tenant resolution) | `7561ba9` |

---

## §2 — Infrastructure Identifiers

| Resource | ID / URL |
|:---|:---|
| **DEV Supabase** | `nzsksjczswndjjbctasu` |
| **PROD Supabase** | `nemrjlimrnrusodivtoa` |
| **DEV Frontend** | `ohno.tuasistentevirtual.cl` |
| **PROD Frontend** | `dash.tuasistentevirtual.cl` |
| **DEV Cloud Run** | `ia-backend-dev-645489345350.us-central1.run.app` |
| **PROD Cloud Run** | `ia-backend-prod-645489345350.us-central1.run.app` |
| **GCP Project** | `saas-javiera` |
| **GitHub** | `YggrYergen/ia-whatsapp-crm` |
| **Sentry Org** | `tuasistentevirtual` (project: `python`) |
| **Test user** | `instagramelectrimax@gmail.com` → tenant `f12ca5b3` (Jose Mancilla/FumigaMax) |
| **Client 1 (PROD)** | CasaVitaCure → tenant `d8376510` |

---

## §3 — Deployment State

| Environment | Frontend | Backend | DB |
|:---|:---|:---|:---|
| DEV | `132602d` (deployed) | `007ad79` (prior) | DEV Supabase |
| PROD | `699dae2` (prior session) | `699dae2` (prior session) | PROD Supabase |

> ⚠️ PROD not yet updated this session — awaiting E2E test pass + user approval

---

## §4 — Migration Parity (DEV vs PROD)

| Migration | DEV | PROD | Status |
|:---|:---|:---|:---|
| is_setup_complete on tenants | ✅ | ✅ | **PROD ✅ VERIFIED** |
| tenants ALTER (DROP NOT NULL ×3) | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| tenant_users ALTER (role, created_at) | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| profiles table + trigger + functions | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| tenant_onboarding table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| onboarding_messages table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| resources table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| tenant_services table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| scheduling_config table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| appointments table | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| Superadmin RLS policies (all tables) | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |
| Profile backfill + role assignment | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-16 session 9ee36370) |

---

## §5 — Known Remaining Issues

| # | Issue | Status |
|:---|:---|:---|
| Sandbox Reiniciar button | `confirm()` blocked by Edge runtime → replaced with React inline confirmation | ✅ FIXED (3915990) — awaiting user verification |
| Sentry auth token (build) | Token set in CF dashboard but needs to be in "Build variables and secrets" | ⚠️ User action required |
| Sentry instrumentation file warning | Created `instrumentation.ts` | ✅ FIXED (d356dcb) |
| Cursor tracking on deployed desktop | Pointer events may be CSP issue in CF Workers | Logged to BACKLOG — investigate after E2E pass |
| Speech-to-text on some mobile browsers | Opera incognito — not a bug | Closed |
