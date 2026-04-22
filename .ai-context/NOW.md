# NOW.md — Working Memory
> **Tier 1 | Updated:** 2026-04-21 22:26 CLT
> **Session:** 62eed18b-c412-4ec7-abe7-60e6462eb334
> **Branch:** `main` | **Last commit:** `ca93ddb`

---

## §0 — Current Focus

**WhatsApp Media Handling Pipeline + Documentation Sync**
Implementing zero-latency media processing for incoming WhatsApp attachments (images, documents, audio, video). Control Pest will receive payment receipts from clients. Pipeline design: synchronous type detection → fire-and-forget background download/upload to Supabase Storage → descriptive text injection for LLM context.

Also: updating 7 stale `.ai-context/` documents (last updated Apr 16, 6 days behind).

---

## §1 — Session Work Log (2026-04-21 — Multi-Tenant Stabilization + Media Analysis)

| # | What | Commit/Method |
|---|------|---------------|
| 1 | RLS: Superadmin INSERT/UPDATE policies for `messages`, `contacts`, `tenants` | PROD SQL (live) |
| 2 | `/config` page migrated into `(panel)` layout for TenantContext integration | `ca93ddb` |
| 3 | Multi-tenant HMAC webhook verification — per-tenant `meta_app_secret` | `1e0efc4` |
| 4 | Removed dead Google Calendar code + fixed tool description | `88c06d4` |
| 5 | `meta_app_secret` column added to `tenants` table (PROD) | PROD SQL |
| 6 | `bot_active = true` reset for CasaVitaCure silent contact | PROD SQL |
| 7 | Deep analysis: Meta Cloud API media webhook payloads | Research |
| 8 | Media handling implementation plan created (zero-latency fire-and-forget) | Plan artifact |
| 9 | Documentation sync: 7 stale `.ai-context/` files updated | This session |

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
| **Client 1 (PROD)** | CasaVitaCure → tenant `d8376510` |
| **Client 2 (PROD)** | Control Pest → tenant (live, HMAC configured) |
| **Test user** | `instagramelectrimax@gmail.com` → tenant `f12ca5b3` (Jose Mancilla/FumigaMax) |

---

## §3 — Deployment State

| Environment | Frontend | Backend | DB |
|:---|:---|:---|:---|
| PROD | `ca93ddb` (deployed via main push) | `ca93ddb` (auto-deploy Cloud Build) | PROD Supabase |

> Both frontend and backend auto-deploy from `main` branch pushes.

---

## §4 — Migration Parity (DEV vs PROD)

| Migration | DEV | PROD | Status |
|:---|:---|:---|:---|
| All Sprint 1 migrations (Apr 11-16) | ✅ | ✅ | **PROD ✅ VERIFIED** |
| `meta_app_secret` column on tenants | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-21) |
| Superadmin INSERT/UPDATE RLS (messages, contacts, tenants) | ✅ | ✅ | **PROD ✅ VERIFIED** (2026-04-21) |
| `message_type` + `media_metadata` on messages | ❌ | ❌ | **PENDING — media handling plan awaiting approval** |

---

## §5 — Known Remaining Issues

| # | Issue | Status |
|:---|:---|:---|
| Media handling | Images/documents/audio from WhatsApp silently dropped (text_body="") | 🔴 Implementation plan ready, awaiting approval |
| E2E test suite | 14-step plan (7 tools + cross-tenant) not yet executed | ⏳ PENDING — user must run manually |
| wamid extraction | Values null in DB — dedup falls back to atomic lock (working) | 🟡 Low priority |
| Dashboard charts | Mock data in `/reportes/` and `/finops/` | 🟡 Sprint 2 |
