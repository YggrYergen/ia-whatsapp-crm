# 🔴 NOW.md — Full Technical Situation Report

> **Updated:** 2026-04-16 06:45 CLT  
> **Session ID:** cb937bcc-b4a2-4a4f-8333-454c75646e32  
> **Branch:** `desarrollo`  
> **Last commit:** `25f929e` — `feat: resource_count onboarding field - provisions N resources from user input`

---

## §0 — What We Are Doing RIGHT NOW and Why

### Current Focus: Multi-Tenant Hardening + Provisioning Accuracy

**Goal:** After the P0/P1 stabilization sprint, we conducted a forensic multi-tenancy audit and fixed critical schema mismatches that caused provisioning failures (PGRST204 errors). The system is now at **60-75% feature completion** for a professional multi-tenant CRM deployment. PROD remains safe and untouched. DEV is being iteratively tested and hardened.

---

### ✅ DONE — Full Session Log (2026-04-15 → 2026-04-16 morning)

#### Phase A — Design & Planning (Apr 15 daytime)

| # | Item | Commit |
|---|------|--------|
| 1 | Sandbox Tool Integration — 7 tools (5 simulated + 2 real) with Responses API agentic loop | `f6c2260` |
| 2 | Native Calendar Architecture — 3-table schema with `EXCLUDE USING gist`, RLS, approved by user | `670dd9d` |
| 3 | Native Calendar Schema + `NativeSchedulingService` — all 6 operations with 3-channel observability | `670dd9d` |
| 4 | Services/Resources CRUD endpoints + Frontend ConfigView skeleton | `670dd9d` |

#### Phase B — P0 Bug Fix Sprint (Apr 15 evening, commit `cd6240e`)

| Priority | Bug | Root Cause | Fix | Files |
|----------|-----|-----------|-----|-------|
| **P0-4** | Notifications leaking across tenants | `UIContext` + `ChatContext` fetched ALL data with no `tenant_id` filter | Added `useTenant()` hook, filtered all queries + Realtime subs by `currentTenantId`, re-subscribe on tenant change, Sentry on all error paths | `UIContext.tsx`, `ChatContext.tsx` |
| **P0-2** | Onboarding doesn't create services/resources | `_finalize_onboarding()` saved prompt but never provisioned services, resources, or scheduling_config | New `_provision_services_and_resources()` (260 lines): parses `services_offered`, creates `tenant_services` with price/duration extraction, creates contextual default `resource` (24 business-type keywords), creates `scheduling_config` with extracted business hours. All non-fatal with 3-channel observability. | `chat_endpoint.py` |
| **P0-1** | Sandbox calendar tools return fake data | All 5 calendar tools returned hardcoded simulated responses | Replaced with `async` implementations calling real `NativeSchedulingService`: `_real_availability()`, `_real_booking()`, `_real_update()`, `_real_delete()`, `_real_list_appointments()`. Appointments now persist to DB. | `sandbox/tools.py` |
| **P0-3** | Duplicate messages in regular chat | Optimistic temp message (`id: temp-*`) + Realtime INSERT of real DB row → both display | Enhanced Realtime handler to remove `temp-*` prefixed messages matching same `sender_role` when real row arrives | `ChatContext.tsx` |
| **P1-1** | Raw markdown text in all chat views | AI responses with `*bold*`, `_italic_`, `~strike~`, URLs rendered as raw text | Created shared `whatsappFormatter.tsx` utility: WhatsApp markdown → React nodes. Applied to all 3 chat views (ChatArea, TestChatArea, sandbox). Includes CSS safety styles for word-break overflow. | `whatsappFormatter.tsx` (NEW), `ChatArea.tsx`, `TestChatArea.tsx`, `sandbox/page.tsx` |

#### Phase C — Multi-Tenancy Forensic Audit (Apr 15 night)

Deep forensic audit of the entire multi-tenant architecture. Investigated every table, every RLS policy, every helper function.

**C1: RLS Audit Results (13 tables)**

| Table | `tenant_select` | `tenant_insert` | `tenant_update` | `superadmin_select` | Status |
|-------|:---:|:---:|:---:|:---:|--------|
| tenants | ✅ | ✅ | ✅ | ✅ | OK |
| contacts | ✅ | ✅ | ✅ | ✅ | OK |
| messages | ✅ | ✅ | — | ✅ | OK |
| alerts | ✅ | ✅ | ✅ | ✅ | OK |
| tenant_users | ✅ | ✅ | — | ✅ | OK |
| test_feedback | ✅ | ✅ | — | ✅ | OK |
| tenant_onboarding | ✅ | ✅ | ✅ | ✅ | OK |
| onboarding_messages | ✅ | ✅ | — | **⚠️ ADDED** | Fixed |
| appointments | ✅ | ✅ | ✅ | **⚠️ ADDED** | Fixed |
| resources | ✅ | ✅ | ✅ | **⚠️ ADDED** | Fixed |
| scheduling_config | ✅ | ✅ | ✅ | **⚠️ ADDED** | Fixed |
| tenant_services | ✅ | ✅ | ✅ | **⚠️ ADDED** | Fixed |
| profiles | — | — | — | — | Auth-owned, no tenant RLS needed |

**C2: Orphan Tenant Cleanup**
- Found 3 "Jose Mancilla" tenant records from failed provisioning attempts
- 2 were orphans (no `tenant_users` linkage) → **DELETED** (`4bda477d`, `af818a7c`)
- Navbar tenant switcher now shows only valid tenants
- CasaVitaCure data verified untouched (18 contacts, 27 msgs, 16 alerts)

**C3: Superadmin RLS Migration** — `add_superadmin_rls_to_new_tables`
- Applied `superadmin_select` policies to 5 tables that were missing them
- Ensures superadmins can see all tenants' data for support/debugging

#### Phase D — Schema Mismatch Fix + Calendar Tenant Isolation (Apr 15 night, commit `3aba37e`)

**D1: PGRST204 Provisioning Errors** ← Root cause of services/resources/config not being created

The provisioning code referenced columns that don't exist in the actual DB schema:

| Table | Code Referenced | Actual Column | Fix |
|-------|----------------|---------------|-----|
| `tenant_services` | `base_price` | `price` | Updated |
| `tenant_services` | `variable_pricing` | `price_is_variable` | Updated |
| `tenant_services` | `estimated_duration_min` | `duration_minutes` | Updated |
| `resources` | `resource_type` (column) | `metadata` (jsonb) | Moved to `metadata.resource_type` |
| `scheduling_config` | `open_time`, `close_time`, `working_days` | `business_hours` (jsonb) | Restructured to jsonb |
| `scheduling_config` | (missing) | `default_duration_minutes`, `slot_interval_minutes`, `buffer_between_minutes`, `timezone` | Added required fields |

**D2: Hardcoded CasaVitaCure tenant_id Removal** — **CRITICAL SECURITY FIX**

Both calendar endpoints had CasaVitaCure's tenant_id as the default:
- `GET /api/calendar/events` — `tenant_id: str = "d8376510-..."` → now required, returns 400 if missing
- `POST /api/calendar/book` — `payload.get("tenant_id", "d8376510-...")` → now required, returns 400 if missing

**D3: Frontend Calendar Tenant Isolation**
- `AgendaView.tsx` — now passes `currentTenantId` from `useTenant()` to both fetch and booking calls
- `calendar/events/route.ts` — proxy now forwards `tenant_id` query param to backend
- `RecursosView.tsx` — reads `resource_type` from `metadata.resource_type` instead of non-existent column

#### Phase E — Resource Count Feature (Apr 16 morning, commit `25f929e`)

**Problem:** Provisioning always created exactly 1 resource, regardless of what the user told the config agent.

**Solution:** Added `resource_count` as the 12th onboarding field:
- **DB migration:** `ALTER TABLE tenant_onboarding ADD COLUMN resource_count integer DEFAULT 1`
- **Agent prompt:** New field #12 with contextual examples ("¿Cuántos equipos/boxes/salas?")
- **`_save_field()`:** Converts LLM string to clamped integer (1-20)
- **Provisioning:** Creates N resources with sequential names and a rotating 10-color palette

#### Phase F — User E2E Testing ✅ PASSED

User completed full onboarding flow after Phase D fixes:
- Config chat: all 11 fields extracted correctly, provisioning triggered ✅
- `tenant_services`: 1 service created (with correct schema) ✅
- `resources`: 2 created (1 auto-provisioned "Equipo 1" + 1 manually added via UI) ✅
- `scheduling_config`: 1 row with business_hours jsonb, timezone, duration ✅
- Sandbox chat: functional, received AI responses ✅
- Frontend: "almost seamless" per user feedback ✅
- Sentry: some non-critical warnings captured (fallback triggers) — addressed

---

### 🔨 DOING NOW

Post-testing iteration. The provisioning pipeline is now functional. Remaining work:

1. **Validate resource_count flow** — Next test should ask for N teams and verify N resources provisioned
2. **Frontend deploy to DEV** — Changes to AgendaView, RecursosView need to be live on dev site

---

### 🔜 WILL DO (Priority Order)

| Priority | Item | Status | Description |
|----------|------|--------|-------------|
| **P1-3** | Agenda real business hours | ⏳ PENDING | `AgendaView` reads `scheduling_config` for hours instead of hardcoded 8-20 |
| **P1-4** | Agenda appointment progress bars | ⏳ PENDING | Show real appointment count per resource in agenda |
| **P1-5** | Permanent sandbox link in contacts | ⏳ PENDING | "Chat de Pruebas" always visible in sidebar |
| **P2** | Services/Products CRUD frontend | ⏳ Designed | Full UI for editing `tenant_services` |
| **P2** | Resources CRUD polish | ⏳ Partial | RecursosView exists but needs polish |
| **P3** | PROD migration sync | ⏳ BLOCKED | Requires full E2E pass on DEV |
| **P4** | GCal cleanup | ⏳ BLOCKED | Remove google_client.py, OAuth — only after native verified in PROD |

---

### Previous Fixes (Still Active, All on `desarrollo`)

| Fix | Commit | DEV | PROD |
|-----|--------|-----|------|
| Phone Number (11th field) | `6508668` | ✅ | ⏳ PENDING |
| Sandbox Isolation (Responses API) | `6508668` | ✅ | ⏳ PENDING |
| Sandbox Tools (7 tools + agentic loop) | `f6c2260` | ✅ | ⏳ PENDING |
| Native Calendar Schema | `670dd9d` | ✅ | ⏳ PENDING |
| P0+P1 Bug Fixes | `cd6240e` | ✅ | ⏳ PENDING |
| Schema Mismatch + Calendar Isolation | `3aba37e` | ✅ | ⏳ PENDING |
| Resource Count Feature | `25f929e` | ✅ | ⏳ PENDING |

### Current Deployment State

| Component | Status | Notes |
|:---|:---|:---|
| **Backend** (Cloud Run DEV) | ✅ Running | Commit `25f929e` — auto-deployed from `desarrollo` |
| **Frontend** (CF Workers DEV) | ⚠️ NEEDS DEPLOY | AgendaView + RecursosView changes need `npm run deploy` or auto-build |
| **Supabase DEV** | ✅ | 13 tables, all RLS enabled, superadmin policies on all |
| **PROD** | 🔒 BLOCKED & SAFE | No changes since Apr 12. 10 migrations pending approval. |

---

## §1 — Complete Session Work Log (2026-04-15 → 2026-04-16)

### 15. Resource Count Feature ✅ (commit `25f929e` — Apr 16 06:37 CLT)
- Added `resource_count` as 12th onboarding field
- DB migration, agent prompt, `_save_field()` handler, N-resource provisioning loop
- Rotating 10-color palette for visual distinction in Agenda

### 14. Schema Mismatch + Calendar Isolation ✅ (commit `3aba37e` — Apr 15 ~22:41 CLT)
- Fixed 6 column mismatches causing PGRST204 in provisioning
- Removed hardcoded CasaVitaCure `tenant_id` from both calendar endpoints
- Frontend calendar now passes `currentTenantId`
- RecursosView reads `resource_type` from `metadata` jsonb

### 13. Multi-Tenancy Forensic Audit (Apr 15 ~21:00-22:30 CLT)
- Audited all 13 tables' RLS policies
- Deleted 2 orphan tenants, reset test user
- Applied superadmin RLS to 5 tables
- Verified CasaVitaCure data integrity

### 12. P0+P1 Stabilization Sprint ✅ (commit `cd6240e`)
- **Context:** User-tested the system, found 5 critical bugs
- **All fixed in single commit:** tenant isolation × 2 contexts, onboarding provisioning, real sandbox tools, message dedup, WhatsApp formatter
- **846 insertions, 237 deletions, 8 files changed**
- **New file:** `Frontend/lib/whatsappFormatter.tsx`

### 11. Native Calendar + Services CRUD (commit `670dd9d`)
- **3 new DB tables:** `resources`, `appointments`, `scheduling_config` with RLS + `btree_gist`
- **NativeSchedulingService:** 6 operations with 3-channel observability
- **Services CRUD:** `services.py` endpoints, `tenant_services` table

### 10. Sandbox Tool Integration ✅ (commit `f6c2260`)
- **7 tools** in sandbox chat (5 simulated calendar + 2 real DB/event)
- Agentic loop with Responses API chaining

### Previous items (1-9): see §1 in earlier session logs

---

## §2 — What's Pending

### Completion Assessment: ~60-75%

| Area | Completion | What's Missing |
|------|:---:|--------------|
| **Self-Onboarding** | 90% | Edge case handling, resource_count validation |
| **Sandbox Chat** | 85% | Polish, real tool responses working |
| **Tenant Isolation** | 95% | Calendar was the last leak — fixed |
| **Chat (Regular)** | 80% | Message dedup fixed, formatting improved |
| **Agenda/Calendar** | 50% | Hardcoded hours, no progress bars, no real resource view |
| **Services CRUD** | 30% | Backend exists, frontend skeleton only |
| **Resources CRUD** | 60% | UI works but reads from wrong schema (now fixed) |
| **Dashboard** | 40% | Live alerts work, charts/KPIs are mock |
| **PROD Parity** | 0% | 10 migrations pending, all work on DEV only |

### AFTER Testing — Remaining Implementation

| Priority | Item | Status | Blocker? |
|----------|------|--------|----------|
| P1-3 | Agenda real business hours from `scheduling_config` | ⏳ | No |
| P1-4 | Agenda real appointment progress bars | ⏳ | No |
| P1-5 | Permanent sandbox link in contacts sidebar | ⏳ | No |
| P2 | Services/Products CRUD frontend page | ⏳ Designed | P1 completion |
| P3 | PROD migration sync (10 migrations) | ⏳ | Full E2E pass on DEV |
| P4 | GCal cleanup (remove google_client.py, OAuth) | ⏳ | P3 completion |

### Migration Parity (DEV vs PROD)

> ⚠️ **CRITICAL GAP:** PROD has 6 tables. DEV has 13 tables. Seven tables + 3 column additions exist only on DEV.

| Migration | DEV | PROD |
|:---|:---|:---|
| `onboarding_messages` table + index + RLS | ✅ Applied | ⏳ PENDING APPROVAL |
| `phone_number` column on `tenant_onboarding` | ✅ Applied | ⏳ PENDING APPROVAL |
| `tenant_onboarding` table | ✅ Applied | ⏳ PENDING APPROVAL |
| `profiles` table | ✅ Applied | ⏳ (may already exist) |
| `resources` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `appointments` table + gist constraint + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `scheduling_config` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `tenant_services` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `superadmin_select` RLS on 5 new tables | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `resource_count` column on `tenant_onboarding` | ✅ Applied (2026-04-16) | ⏳ PENDING APPROVAL |

**PROD SQL is ready to apply. Blocked on: user approving promotion after full E2E verification on DEV.**

### Technical Debt
- [ ] Remove `google-api-python-client`, `google-auth-oauthlib` from requirements (after GCal cleanup)
- [ ] Config agent prompt improvements — Remove redundant confirmations (REGLA 2), improve natural flow
- [ ] Frontend manual deploy to Cloudflare Workers DEV (after testing)
- [ ] Onboarding edge cases: what if user says "no tenemos horario" or "24/7"?
- [ ] Provisioning: services_offered extraction should create granular per-service rows, not one blob

---

## §3 — Infrastructure Identifiers

| Resource | ID / URL |
|:---|:---|
| **Supabase DEV** | Project: `nzsksjczswndjjbctasu` (13 tables) |
| **Supabase PROD** | Project: `nemrjlimrnrusodivtoa` (6 tables) |
| **Cloud Run DEV** | `ia-backend-dev` in `saas-javiera` / `us-central1` |
| **Cloud Run PROD** | `ia-backend-prod` in `saas-javiera` / `us-central1` |
| **Frontend DEV** | `https://dev-ia-whatsapp-crm.tomasgemes.workers.dev` / `ohno.tuasistentevirtual.cl` |
| **Frontend PROD** | `https://ia-whatsapp-crm.tomasgemes.workers.dev` / `dash.tuasistentevirtual.cl` |
| **Test user email** | `instagramelectrimax@gmail.com` |
| **Test user current tenant** | `f12ca5b3-cbeb-4488-ac68-de3a78e55e63` (Jose Mancilla — FumigaMax) |
| **CasaVitaCure tenant** | `d8376510-911e-42ef-9f3b-e018d9f10915` |
| **GitHub repo** | `YggrYergen/ia-whatsapp-crm` |
| **Branch** | `desarrollo` (all work) → merge to `main` for PROD |

---

## §4 — Key Files Modified (This Session — Apr 15-16)

| File | What Changed |
|:---|:---|
| `Backend/app/api/onboarding/chat_endpoint.py` | **P0-2 + D1 + E:** Provisioning function: schema fix (6 columns), N-resource loop, resource_count handling, `_save_field` resource_count parser |
| `Backend/app/api/onboarding/agent_prompt.py` | **E:** Added `resource_count` as 12th field in ONBOARDING_FIELDS + prompt instructions |
| `Backend/app/api/sandbox/tools.py` | **P0-1:** Replaced 5 simulated functions with real NativeSchedulingService calls |
| `Backend/app/main.py` | **D2:** Removed hardcoded tenant_id from `/api/calendar/events` and `/api/calendar/book`, now required |
| `Frontend/contexts/UIContext.tsx` | **P0-4:** Tenant-filtered alerts + Realtime re-subscription |
| `Frontend/contexts/ChatContext.tsx` | **P0-4b + P0-3:** Tenant-filtered contacts/messages + dedup fix |
| `Frontend/components/CRM/AgendaView.tsx` | **D3:** Passes `currentTenantId` to calendar API calls |
| `Frontend/components/CRM/RecursosView.tsx` | **D3:** Reads `resource_type` from `metadata` jsonb + helper function |
| `Frontend/app/api/calendar/events/route.ts` | **D3:** Forwards `tenant_id` query param to backend |
| `Frontend/lib/whatsappFormatter.tsx` | **P1-1 NEW:** WhatsApp markdown → React nodes formatter |
| `Frontend/components/Conversations/ChatArea.tsx` | **P1-1:** Applied shared formatter |
| `Frontend/components/Conversations/TestChatArea.tsx` | **P1-1:** Applied shared formatter |
| `Frontend/app/(panel)/chats/sandbox/page.tsx` | **P1-1:** Applied shared formatter |

---

## §5 — Git Commits This Session (on `desarrollo`)

```
25f929e feat: resource_count onboarding field - provisions N resources from user input
3aba37e fix: schema mismatch in provisioning (PGRST204) + remove hardcoded tenant_id from calendar
916137b docs: update NOW.md + execution_tracker.md with P0+P1 sprint results
cd6240e fix(P0+P1): tenant isolation, real sandbox tools, service provisioning, message dedup & formatting
f7eb010 fix: tool format conversion + response_dto unbound in sandbox
670dd9d feat: native scheduling + services/resources CRUD + config modernization
f6c2260 feat(sandbox): 7 tools with agentic loop via Responses API chaining
6508668 fix(sandbox+phone): isolated sandbox via Responses API, phone_number field fix
74f1748 fix: typo resisted->persisted in history loading
8dbea72 feat(onboarding): persistent conversation history + session resumability
4d0e5c1 fix(completion): move keyframe animations to globals.css (fixes build)
df5a634 feat(onboarding): activity timeout + provisioning progress + celebration UI
09aa68b fix(onboarding): stop suppressing first done event + add SSE observability
```

---

---

# 🔒 OPERATIONAL RULES (from SESSION_PROMPT.md — verbatim)

> These are ALL the immutable rules from `.ai-context/SESSION_PROMPT.md`. They MUST be followed in every session without exception.

---

## 🔒 §4 — The Documentation-First Rule

> **THIS IS THE SINGLE MOST IMPORTANT RULE IN THIS ENTIRE PROMPT.**

### The Rule
**Before implementing ANY change, the agent MUST:**
1. **Identify** all official documentation URLs linked in the relevant `task.md` block (📚 markers).
2. **Open and read** each URL. Not skim. READ. Pay attention to version-specific behaviors, edge cases, deprecation notices, and "Important" callouts.
3. **Cross-reference** with the corresponding Deep Dive file for additional context and implementation notes.
4. **If the existing docs are insufficient** — the agent MUST perform web searches to find the latest official documentation. This is not optional. Guessing is NEVER acceptable when official docs exist.

### Why This Rule Exists
- The codebase uses **multiple external APIs** (OpenAI, Meta Graph API, WhatsApp Cloud API, Supabase, Google Calendar) that each have version-specific behaviors.
- APIs change. What was true for v19.0 is NOT true for v25.0. What worked with `gpt-4o-mini` does NOT work identically with `gpt-5.4-mini`.
- A "works on my machine" implementation that violates the official spec WILL break in production.
- **The cost of reading docs: 5 minutes. The cost of NOT reading docs: hours of debugging + potential production incident affecting real clients.**

### Mandatory Web Search Triggers
The agent MUST perform fresh web searches when:
- The task involves an API version change or migration
- The existing 📚 link returns a 404 or redirects to a different page
- The task involves security-sensitive operations (webhook verification, auth, tokens)
- The agent encounters unexpected API behavior that contradicts the docs
- More than 30 days have passed since the Deep Dive was last updated

---

## 🔒 §5 — The Logs-First Debugging Rule

> **NEVER assume why something failed. NEVER.** Assumptions are the #1 cause of cascading failures in this project.

### The Rule
When encountering ANY error, unexpected behavior, or test failure:

1. **CAPTURE THE FULL ERROR** — Get the complete traceback, HTTP status codes, response bodies, and log output. Not a summary. The FULL output.
2. **IDENTIFY THE EXACT FAILURE POINT** — Which file, which line, which function, which API call. Be specific.
3. **READ THE RELEVANT LOGS** — Check Sentry, Cloud Run logs, Discord alerts, and terminal output. Multiple sources, not just one.
4. **UNDERSTAND THE CAUSAL CHAIN** — Trace the error back to its root. What triggered the function? What input did it receive? What was the expected vs actual output?
5. **ONLY THEN diagnose** — After steps 1-4, form a hypothesis. Then verify it with evidence before implementing a fix.
6. **AFTER fixing** — Verify the fix actually works. Run the test again. Check the logs again. Confirm the error is gone.

### Explicitly Forbidden
- ❌ "This probably failed because..." → **SHOW ME THE ERROR.**
- ❌ "Let me try changing this and see if it works" → **DIAGNOSE FIRST, THEN CHANGE.**
- ❌ "It works now" (without evidence) → **SHOW ME THE PASSING TEST/LOG.**
- ❌ Changing code that wasn't related to the error → **FIX WHAT'S BROKEN, NOTHING ELSE.**

---

## 🔒 §6 — The Observability-First Rule

> **EVERY code change MUST include Sentry + Discord instrumentation.** If an error can happen, we MUST know about it instantly. Silent failures are production killers.

### The Rule
When writing or modifying ANY code that could fail (API calls, DB operations, tool execution, external services, data parsing):

1. **Wrap in try/except** — Every call to an external service or potentially-failing operation MUST be wrapped.
2. **Log to `logger`** — Include the function/tool name, tenant_id (if available), and relevant input parameters for fast diagnosis.
3. **Capture in `sentry_sdk`** — Use `sentry_sdk.capture_exception(e)` for errors, `sentry_sdk.capture_message()` for warnings. Use `sentry_sdk.set_context()` to attach diagnostic data.
4. **Alert via `send_discord_alert()`** — Every error-level exception must also fire a Discord alert with a descriptive title, description, `error=e`, and appropriate `severity`.
5. **Even gracefully handled errors must report** — If you catch an error and return a fallback, STILL report to Sentry + Discord.

### The Pattern (Copy This)
```python
try:
    result = await some_operation(param1, param2)
    return result
except Exception as e:
    tenant_id = tenant.id if tenant else "unknown"
    logger.error(f"[ComponentName] Operation failed for tenant={tenant_id}: {e}")
    sentry_sdk.set_context("component_context", {"component": "name", "tenant_id": tenant_id, "param1": param1})
    sentry_sdk.capture_exception(e)
    await send_discord_alert(
        title=f"❌ ComponentName Failed | Tenant {tenant_id}",
        description=f"param1={param1}\nError: {str(e)[:300]}",
        severity="error", error=e
    )
    return fallback_value
```

### Explicitly Forbidden
- ❌ `except Exception: pass` → **NEVER swallow errors silently**
- ❌ `except Exception as e: logger.error(e)` alone → **MUST also Sentry + Discord**
- ❌ Bare function calls without try/except on external services → **ALWAYS wrap**
- ❌ Early returns without reporting → **MUST log + Sentry**

### Required Imports (in every file that handles errors)
```python
import sentry_sdk
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger
```

---

## 🔒 §7 — The No-Assumptions Testing Rule

> **Changes are NOT complete until they are TESTED and VERIFIED.** Code that compiles is not code that works.

### The Rule
After implementing any change:

1. **Unit verification** — Does the specific function/module work in isolation?
2. **Integration verification** — Does it work with the rest of the system?
3. **Live verification** (when applicable) — Does it work in the actual environment?
4. **Regression check** — Did the change break anything that was working before?

### What "Verified" Means
- ✅ A passing test with visible output
- ✅ A successful API response with the expected body
- ✅ A log entry showing the correct behavior
- ✅ A screenshot/recording of the working UI
- ❌ "I believe this should work" — NOT VERIFIED
- ❌ "The code looks correct" — NOT VERIFIED
- ❌ "Similar code works elsewhere" — NOT VERIFIED

---

## 🔒 §8 — Progress & Documentation Preservation Rules

### Rule 1: Never Remove Key Information
- **DO NOT** delete or overwrite content from `task.md`, `implementation_plan.md`, `README.md`, or deep dives without explicit user approval.
- **DO NOT** replace detailed content with summaries.
- **ALWAYS** append, annotate, or update-in-place.

### Rule 2: Update Progress Immediately
After completing any block or sub-task:
1. Mark it `[x]` in `task.md`
2. Add a completion note with date and any learnings
3. Update `execution_tracker.md`
4. If a decision was made, add it to `README.md`

### Rule 3: Preserve Documentation Links
- **NEVER** remove 📚 URLs from `task.md` or `implementation_plan.md`

### Rule 4: Record Deviations
If implementation deviates from the plan:
1. Document WHAT was different and WHY
2. Update `task.md` with the actual approach
3. Flag downstream impacts

### Rule 5: Session Handoff
At the END of every session:
1. All completed tasks marked in `task.md`
2. `execution_tracker.md` updated
3. New decisions recorded
4. `[MODIFIABLE]` sections of SESSION_PROMPT updated
5. A `git commit` captures the stable state

---

## 🔒 §8b — Operational Guardrails

### Code Safety
- **NEVER** deploy directly to production without EXPLICIT APROVAL AND CONSENT FROM USER
- **NEVER** modify environment variables or secrets without user EXPLICIT CONFIRMATION
- **NEVER** delete data from Supabase production tables
- **ALWAYS** test locally or in dev environment
- **ALWAYS** create a git commit before AND after significant changes

### Git Branch & Deployment Architecture

```
┌──── git push origin desarrollo ────┐     ┌──── git push origin main ────────┐
│                                     │     │                                   │
│  Cloud Build (saas-javiera)         │     │  Cloud Build (saas-javiera)       │
│  ├─ Build: Backend/Dockerfile       │     │  ├─ Build: Backend/Dockerfile     │
│  ├─ Push: → Artifact Registry       │     │  ├─ Push: → Artifact Registry     │
│  └─ Deploy: → ia-backend-dev        │     │  └─ Deploy: → ia-backend-prod     │
│                                     │     │                                   │
│  Cloudflare Workers Builds          │     │  Cloudflare Workers Builds        │
│  └─ Deploy: → dev-ia-whatsapp-crm   │     │  └─ Deploy: → ia-whatsapp-crm    │
└─────────────────────────────────────┘     └───────────────────────────────────┘
```

| Branch | Backend Service | Frontend | Database |
|:---|:---|:---|:---|
| `desarrollo` | `ia-backend-dev` (auto-deploy) | CF Worker auto-deploy via Workers Builds | Supabase DEV |
| `main` | `ia-backend-prod` (auto-deploy) | Auto-deploy via Workers Builds | Supabase PROD |

### THE WORKFLOW
1. ALL new work on `desarrollo` — never commit directly to `main`
2. Push triggers auto-deploy backend to DEV — test there
3. When stable → merge `desarrollo → main` to deploy to PROD
4. **NEVER push untested code to `main`**

### Scope Discipline
- **ONLY** work on the blocks listed in §1 "What Is Being Done RIGHT NOW"
- Out-of-scope problems: **LOG IT**, do NOT fix it
- If it BLOCKS current task: fix minimum needed, document everything

### Git Hygiene
- Commit messages: `type(scope): description`
- One logical change per commit
- Never force-push to `main`

---

## 🔒 Migration Parity Rule — NON-NEGOTIABLE

> On April 12, 2026, a migration applied ONLY to DEV caused a production outage. The `updated_at` column was never applied to PROD. The 90-second lock TTL safety mechanism was completely dead in production.

**The Gated Lifecycle:**
```
 1. Write the migration SQL
 2. Apply to DEV (project: nzsksjczswndjjbctasu) — iterate freely
 3. Test on DEV (simulation, manual test, sandbox)
 4. Mark: "DEV ✅ | PROD ⏳ PENDING APPROVAL"
 5. ── GATE: User explicitly approves promotion to PROD ──
 6. Apply IDENTICAL SQL to PROD (project: nemrjlimrnrusodivtoa)
 7. Verify on PROD (information_schema query)
 8. Mark: "DEV ✅ | PROD ✅ VERIFIED"
```

**If experimental/unsafe:** Stay at step 4, mark: `"PROD ❌ NOT YET — REASON: [reason]"`

**Verification Query (run after EVERY migration):**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<TABLE>' AND column_name = '<COLUMN>';
```

**Report BOTH verification results (DEV + PROD) in response.**

**Pre-Merge Drift Check:** Before every `desarrollo → main` merge, query schemas on BOTH envs. Any discrepancy → merge BLOCKED.

---

## 🔒 §9 — Technology Stack

| Layer | Technology |
|:---|:---|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 15 + React 19 |
| Database | Supabase (PostgreSQL) |
| LLM (PROD) | OpenAI `gpt-5.4-mini` |
| LLM (DEV) | OpenAI `gpt-5.4` (config agent) / `gpt-5.4-nano` (general) |
| Messaging | WhatsApp Cloud API |
| Hosting | Google Cloud Run |
| Frontend Host | Cloudflare Pages (Workers) |
| Observability | Sentry + Discord webhooks |
| Auth | Supabase Auth |

### Runtime Environment
| Aspect | Value |
|:---|:---|
| OS | Windows |
| Shell | **PowerShell** — NOT bash. `&&` does NOT work. Use `;` to chain. |
| Python | `python` (not `python3`) |

---

## 🔒 §9.1 — MCP Tools Available

### `cloudrun` — Google Cloud Run Management
| Tool | Use For |
|:---|:---|
| `list_projects` | See all GCP projects |
| `list_services` | See Cloud Run services |
| `get_service` | Inspect specific service |
| `get_service_log` | **CRITICAL FOR DEBUGGING** |
| `deploy_local_folder` | Deploy code |

### `supabase-mcp-server` — Supabase Database
| Tool | Use For |
|:---|:---|
| `list_projects` | See PROD + DEV projects |
| `list_tables` | Inspect schema (`verbose: true` for columns) |
| `execute_sql` | Run SELECT queries for diagnostics |
| `apply_migration` | Run DDL changes |
| `get_logs` | Service logs |
| `get_advisors` | Security/performance checks |

### ⚠️ Production vs Development
| Environment | Project ID | Safety |
|:---|:---|:---|
| **PRODUCTION** | `nemrjlimrnrusodivtoa` | 🔴 READ-ONLY unless approved |
| **DEVELOPMENT** | `nzsksjczswndjjbctasu` | 🟢 Free to modify |

### MCP Safety Rules
1. NEVER run DELETE/DROP/TRUNCATE/UPDATE on production without approval
2. ALWAYS use `list_projects` first to identify correct project
3. ALWAYS use `list_tables` with `verbose: true` before migrations
4. Prefer `execute_sql` for diagnostics
5. Use `apply_migration` for DDL (creates migration record)
6. Use `get_service_log` as FIRST debugging step for Cloud Run issues
7. Run `get_advisors` after DDL changes

---

## 🔒 §10 — Emergency Procedures

### If Production Is Down
1. Check Cloud Run logs FIRST
2. Check Sentry for latest error
3. Check Discord for automated alerts
4. If issue is in latest deploy: **ROLLBACK** using previous Cloud Run revision
5. Notify user IMMEDIATELY

### If LLM Returns Garbage
1. Check which model is actually being called
2. Check the system prompt being sent
3. Check message history format
4. Check `strict: true` schema violations
5. Check `max_completion_tokens` cap

### If WhatsApp Stops Receiving Messages
1. Check Meta webhook subscription
2. Check verification token
3. Check Cloud Run health
4. Check Meta App status
5. Check rate limits

---

## §6 — Current Migration Status

| Migration | DEV | PROD |
|:---|:---|:---|
| `onboarding_messages` table + index + RLS | ✅ Applied & verified | ⏳ PENDING APPROVAL |
| `phone_number` column on `tenant_onboarding` | ✅ Applied & verified (2026-04-15) | ⏳ PENDING APPROVAL |
| `tenant_onboarding` table | ✅ Applied | ⏳ PENDING APPROVAL |
| `profiles` table | ✅ Applied | ⏳ PENDING APPROVAL |
| `resources` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `appointments` table + gist + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `scheduling_config` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `tenant_services` table + RLS | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| Superadmin RLS on 5 new tables | ✅ Applied (2026-04-15) | ⏳ PENDING APPROVAL |
| `resource_count` column on `tenant_onboarding` | ✅ Applied (2026-04-16) | ⏳ PENDING APPROVAL |

**Schema Gap: DEV has 13 tables, PROD has 6 tables. 10 migrations pending PROD approval.**

**PROD SQL ready to apply — blocked on full E2E verification on DEV + user approval.**

---

> **END OF NOW.md**  
> This file is the single source of truth for the current session state.  
> Update it before starting new work or ending the session.
