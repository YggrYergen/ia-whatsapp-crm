# 🔴 NOW.md — Full Technical Situation Report

> **Updated:** 2026-04-15 18:13 CLT  
> **Session ID:** cb937bcc-b4a2-4a4f-8333-454c75646e32  
> **Branch:** `desarrollo`  
> **Last commit:** `cd6240e` — `fix(P0+P1): tenant isolation, real sandbox tools, service provisioning, message dedup & formatting`

---

## §0 — What We Are Doing RIGHT NOW and Why

### Current Focus: Stabilization Sprint — Critical Bug Fixes for Demo Readiness

**Goal:** Resolve all P0/P1 bugs discovered during user testing so the platform is demo-ready for the upcoming client onboarding. Every system — onboarding, sandbox, agenda, chat — must work flawlessly end-to-end with zero cross-tenant data leaks, zero duplicate messages, and proper observability at every failure point.

---

#### ✅ DONE (this session, 2026-04-15)

**Phase A — Design & Planning (earlier today)**

| # | Item | Commit |
|---|------|--------|
| 1 | Sandbox Tool Integration — 7 tools (5 simulated + 2 real) with Responses API agentic loop | `f6c2260` |
| 2 | Native Calendar Architecture — 3-table schema with `EXCLUDE USING gist`, RLS, approved by user | `670dd9d` |
| 3 | Native Calendar Schema + `NativeSchedulingService` — all 6 operations with 3-channel observability | `670dd9d` |
| 4 | Services/Resources CRUD endpoints + Frontend ConfigView skeleton | `670dd9d` |

**Phase B — P0 Bug Fix Sprint (this session, commit `cd6240e`)**

| Priority | Bug | Root Cause | Fix | Files |
|----------|-----|-----------|-----|-------|
| **P0-4** | Notifications leaking across tenants | `UIContext` + `ChatContext` fetched ALL data with no `tenant_id` filter | Added `useTenant()` hook, filtered all queries + Realtime subs by `currentTenantId`, re-subscribe on tenant change, Sentry on all error paths | `UIContext.tsx`, `ChatContext.tsx` |
| **P0-2** | Onboarding doesn't create services/resources | `_finalize_onboarding()` saved prompt but never provisioned services, resources, or scheduling_config | New `_provision_services_and_resources()` (260 lines): parses `services_offered`, creates `tenant_services` with price/duration extraction, creates contextual default `resource` (24 business-type keywords), creates `scheduling_config` with extracted business hours. All non-fatal with 3-channel observability. | `chat_endpoint.py` |
| **P0-1** | Sandbox calendar tools return fake data | All 5 calendar tools returned hardcoded simulated responses | Replaced with `async` implementations calling real `NativeSchedulingService`: `_real_availability()`, `_real_booking()`, `_real_update()`, `_real_delete()`, `_real_list_appointments()`. Appointments now persist to DB. | `sandbox/tools.py` |
| **P0-3** | Duplicate messages in regular chat | Optimistic temp message (`id: temp-*`) + Realtime INSERT of real DB row → both display | Enhanced Realtime handler to remove `temp-*` prefixed messages matching same `sender_role` when real row arrives | `ChatContext.tsx` |
| **P1-1** | Raw markdown text in all chat views | AI responses with `*bold*`, `_italic_`, `~strike~`, URLs rendered as raw text | Created shared `whatsappFormatter.tsx` utility: WhatsApp markdown → React nodes. Applied to all 3 chat views (ChatArea, TestChatArea, sandbox). Includes CSS safety styles for word-break overflow. | `whatsappFormatter.tsx` (NEW), `ChatArea.tsx`, `TestChatArea.tsx`, `sandbox/page.tsx` |

---

#### 🔨 DOING NOW: User Testing + Remaining P1 Items

The P0+P1 commit (`cd6240e`) has been pushed to `desarrollo`. Cloud Build will auto-deploy backend to DEV. The user should test:

1. **Onboarding flow end-to-end** — Does it provision services/resources/scheduling_config?
2. **Tenant isolation** — Does switching tenants in navbar show only that tenant's data?
3. **Sandbox chat** — Do calendar tool calls create real appointments?
4. **Message dedup** — Does sending a message show exactly 1 bubble (not 2)?
5. **Message formatting** — Do `*bold*` and `_italic_` render correctly?

**Remaining P1 items (not yet implemented):**

| ID | Issue | Status | Description |
|----|-------|--------|-------------|
| **P1-3** | Agenda business hours from real data | ⏳ PENDING | `AgendaView` should read `scheduling_config` for business hours instead of hardcoded 8-20 |
| **P1-4** | Agenda appointment progress bars | ⏳ PENDING | Show real appointment count per resource as progress bars |
| **P1-5** | Permanent sandbox link in chats list | ⏳ PENDING | Old "Chat de Pruebas" should always appear in contacts list sidebar as shortcut to `/chats/sandbox` |

---

#### 🔜 WILL DO (after stabilization sprint)

1. **P1-3/P1-4:** Agenda real data integration
2. **P1-5:** Permanent sandbox chat link
3. **Services/Products Page (P2):** Full CRUD frontend for `tenant_services` — user-approved, architecture designed but blocked on stabilization
4. **PROD migration:** DEV → E2E verified → schema sync → PROD (per migration lifecycle rule)
5. **GCal cleanup (Phase 5):** Remove google_client.py, OAuth router, tenant GCal columns — ONLY after native calendar verified in PROD

---

#### Previous Fixes (Still Active, All on `desarrollo`)

| Fix | Commit | DEV | PROD |
|-----|--------|-----|------|
| Phone Number (11th field) | `6508668` | ✅ | ⏳ PENDING |
| Sandbox Isolation (Responses API) | `6508668` | ✅ | ⏳ PENDING |
| Sandbox Tools (7 tools + agentic loop) | `f6c2260` | ✅ | ⏳ PENDING |
| Native Calendar Schema | `670dd9d` | ✅ | ⏳ PENDING |
| P0+P1 Bug Fixes | `cd6240e` | ✅ | ⏳ PENDING |

### Current Deployment State

| Component | Status | Notes |
|:---|:---|:---|
| **Backend** (Cloud Run DEV) | ✅ Running | Commit `cd6240e` — auto-deployed |
| **Frontend** (Cloudflare Workers DEV) | ⚠️ NEEDS MANUAL DEPLOY | `npm run deploy` required on `desarrollo` |
| **Supabase DEV** | ✅ | 13 tables, all RLS enabled |
| **PROD** | ⏳ UNTOUCHED | No changes merged to main since Apr 12 |

---

## §1 — Complete Session Work Log (2026-04-15)

### 12. P0+P1 Stabilization Sprint ✅ (commit `cd6240e`)
- **Context:** User-tested the system, found 5 critical bugs
- **All fixed in single commit:** tenant isolation × 2 contexts, onboarding provisioning, real sandbox tools, message dedup, WhatsApp formatter
- **846 insertions, 237 deletions, 8 files changed**
- **New file:** `Frontend/lib/whatsappFormatter.tsx`

### 11. Native Calendar + Services CRUD (commit `670dd9d`)
- **3 new DB tables:** `resources`, `appointments`, `scheduling_config` with RLS + `btree_gist`
- **NativeSchedulingService:** 6 operations (availability, book, cancel, update, list, events) with 3-channel observability
- **Services CRUD:** `services.py` endpoints, `tenant_services` table
- **Frontend skeleton:** ConfigView for services management

### 10. Sandbox Tool Integration ✅ (commit `f6c2260`)
- **7 tools** in sandbox chat (5 simulated calendar + 2 real DB/event)
- Agentic loop with Responses API chaining (`previous_response_id`, `store=True`)
- MAX_TOOL_ROUNDS=3, full 3-channel observability

### Previous items (1-9): see §1 in earlier session logs
*(Responses API fix, done event fix, activity timeout, SSE observability, frontend state fix, provisioning overlay, celebration screen, persistent history, tool detection feature spec)*

---

## §2 — What's Pending

### NOW — User Testing of commit `cd6240e`

Priority order for testing:
1. Self-onboarding flow → verify provisioning
2. Sandbox chat → verify real tool calls
3. Tenant switching → verify isolation
4. Message send → verify no duplicates
5. AI response formatting → verify markdown rendering

### AFTER Testing — Remaining Implementation

| Priority | Item | Status | Blocker? |
|----------|------|--------|----------|
| P1-3 | Agenda real business hours from `scheduling_config` | ⏳ | No |
| P1-4 | Agenda real appointment progress bars | ⏳ | No |
| P1-5 | Permanent sandbox link in contacts sidebar | ⏳ | No |
| P2 | Services/Products CRUD frontend page | ⏳ Designed | P0/P1 completion |
| P3 | PROD migration sync | ⏳ | Full E2E pass on DEV |
| P4 | GCal cleanup (remove google_client.py, OAuth) | ⏳ | P3 completion |

### Migration Parity (DEV vs PROD)

> ⚠️ **CRITICAL GAP:** PROD has 6 tables. DEV has 13 tables. Seven tables exist only on DEV and are NOT yet approved for PROD migration.

| Migration | DEV | PROD |
|:---|:---|:---|
| `onboarding_messages` table + index + RLS | ✅ Applied | ⏳ PENDING APPROVAL |
| `phone_number` column on `tenant_onboarding` | ✅ Applied | ⏳ PENDING APPROVAL |
| `tenant_onboarding` table | ✅ Applied | ⏳ PENDING APPROVAL |
| `profiles` table | ✅ Applied | ⏳ (may already exist) |
| `resources` table + RLS | ✅ Applied | ⏳ PENDING APPROVAL |
| `appointments` table + gist constraint + RLS | ✅ Applied | ⏳ PENDING APPROVAL |
| `scheduling_config` table + RLS | ✅ Applied | ⏳ PENDING APPROVAL |
| `tenant_services` table + RLS | ✅ Applied | ⏳ PENDING APPROVAL |

**PROD SQL is ready to apply. Blocked on: user testing on DEV passing with zero errors.**

### Technical Debt
- [ ] Remove `google-api-python-client`, `google-auth-oauthlib` from requirements (after GCal cleanup)
- [ ] Config agent prompt improvements — Remove redundant confirmations (REGLA 2), improve natural flow
- [ ] RLS verification — Confirm `onboarding_messages` RLS policy correctly restricts access
- [ ] Sandbox tools integration — connect to real scheduling via NativeSchedulingService ✅ DONE
- [ ] Frontend manual deploy to Cloudflare Workers DEV (after testing)

---

## §3 — Infrastructure Identifiers

| Resource | ID / URL |
|:---|:---|
| **Supabase DEV** | Project: `nzsksjczswndjjbctasu` (13 tables) |
| **Supabase PROD** | Project: `nemrjlimrnrusodivtoa` (6 tables) |
| **Cloud Run DEV** | `ia-backend-dev` in `saas-javiera` / `us-central1` |
| **Cloud Run PROD** | `ia-backend-prod` in `saas-javiera` / `us-central1` |
| **Frontend DEV** | `https://dev-ia-whatsapp-crm.tomasgemes.workers.dev` |
| **Frontend PROD** | `https://ia-whatsapp-crm.tomasgemes.workers.dev` |
| **Test tenant ID** | `4bda477d-33d6-458a-b256-e28ea1337324` (instagramelectrimax) |
| **GitHub repo** | `YggrYergen/ia-whatsapp-crm` |
| **Branch** | `desarrollo` (all work) → merge to `main` for PROD |

---

## §4 — Key Files Modified This Session (commit `cd6240e`)

| File | What Changed |
|:---|:---|
| `Frontend/contexts/UIContext.tsx` | **P0-4:** Tenant isolation — alerts filtered by `currentTenantId`, dynamic Realtime re-subscription, Sentry on all error paths |
| `Frontend/contexts/ChatContext.tsx` | **P0-4b + P0-3:** Tenant isolation on contacts/messages queries + Realtime subs. Fixed duplicate messages (remove `temp-*` on Realtime INSERT). `useRef` for stale closure prevention. |
| `Backend/app/api/onboarding/chat_endpoint.py` | **P0-2:** Added `_provision_services_and_resources()` — auto-creates `tenant_services`, `resources`, `scheduling_config` from onboarding data (260 lines) |
| `Backend/app/api/sandbox/tools.py` | **P0-1:** Replaced 5 simulated calendar functions with real `NativeSchedulingService` async implementations. Updated header, executor routing. |
| `Frontend/lib/whatsappFormatter.tsx` | **P1-1 NEW:** Shared WhatsApp markdown formatter — `*bold*`, `_italic_`, `~strike~`, `` `code` ``, ```` ```blocks``` ````, URLs, line breaks, CSS safety styles |
| `Frontend/components/Conversations/ChatArea.tsx` | **P1-1:** Replaced 38-line inline `formatWhatsAppText` with shared `formatWhatsAppMessage` |
| `Frontend/components/Conversations/TestChatArea.tsx` | **P1-1:** Same replacement as ChatArea |
| `Frontend/app/(panel)/chats/sandbox/page.tsx` | **P1-1:** Applied `formatWhatsAppMessage` + `messageBubbleStyles` |

---

## §5 — Git Commits This Session (on `desarrollo`)

```
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
│  Cloud Build (saas-javiera)         │     │  Cloud Build (casavitacure-crm)   │
│  ├─ Build: Backend/Dockerfile       │     │  ├─ Build: Backend/Dockerfile     │
│  ├─ Push: → Artifact Registry       │     │  ├─ Push: → Artifact Registry     │
│  └─ Deploy: → ia-backend-dev        │     │  └─ Deploy: → ia-backend-prod     │
│                                     │     │                                   │
│  Cloudflare Workers Builds          │     │  Cloudflare Workers Builds        │
│  └─ Deploy: → dev-ia-whatsapp-crm.tomasgemes.workers.dev            │     │  └─ Deploy: → ia-whatsapp-crm.tomasgemes.workers.dev          │
└─────────────────────────────────────┘     └───────────────────────────────────┘
```

⚠️ **CRITICAL FINDING THIS SESSION:** Cloudflare Workers auto-build is connected to `main` only. Frontend changes on `desarrollo` require **manual** `npm run deploy` from the local machine. This gap caused ALL previous frontend fixes to be invisible on the dev site.

| Branch | Backend Service | Frontend | Database |
|:---|:---|:---|:---|
| `desarrollo` | `ia-backend-dev` (auto-deploy) | Manual `npm run deploy` | Supabase DEV |
| `main` | `ia-backend-prod` (auto-deploy) | Auto-deploy via Workers Builds | Supabase PROD |

### THE WORKFLOW
1. ALL new work on `desarrollo` — never commit directly to `main`
2. Push triggers auto-deploy backend to DEV — test there
3. Frontend on `desarrollo` requires manual deploy
4. When stable → merge `desarrollo → main` to deploy to PROD
5. **NEVER push untested code to `main`**

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

**Schema Gap: DEV has 13 tables, PROD has 6 tables. 7 tables pending PROD approval.**

**PROD SQL ready to apply — blocked on full E2E verification on DEV.**

---

> **END OF NOW.md**  
> This file is the single source of truth for the current session state.  
> Update it before starting new work or ending the session.
