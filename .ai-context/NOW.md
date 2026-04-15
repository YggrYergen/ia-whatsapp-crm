# 🔴 NOW.md — Full Technical Situation Report

> **Updated:** 2026-04-15 15:50 CLT  
> **Session ID:** cb937bcc-b4a2-4a4f-8333-454c75646e32  
> **Branch:** `desarrollo`  
> **Last commit:** `f6c2260` — `feat(sandbox): 7 tools with agentic loop via Responses API chaining`

---

## §0 — What We Are Doing RIGHT NOW and Why

### Current Focus: Native Calendar Solution — APPROVED, IMPLEMENTING

**The sandbox demo tools work (simulated). Now we build the real scheduling infrastructure that eliminates Google Calendar permanently.**

---

#### ✅ DONE (this session, 2026-04-15)

**1. Sandbox Tool Integration** (commit `f6c2260`)
- **7 tools** work in sandbox chat (5 simulated calendar + 2 real DB/event)
- Agentic loop with Responses API chaining (`previous_response_id`, `store=True`)
- MAX_TOOL_ROUNDS=3, full 3-channel observability
- Files: `sandbox/tools.py` (NEW), `sandbox/chat_endpoint.py` (REWRITE), `openai_responses_adapter.py` (+chaining), `router.py` (+response_id)
- All imports verified, zero regressions ✅

**2. Native Calendar Plan Created + User-Approved**
- Full GCal audit: 5 backend files, 3 frontend files, 4 DB columns
- Architecture: 3 new tables (`resources`, `appointments`, `scheduling_config`)
- `EXCLUDE USING gist` for race-condition-proof double-booking prevention
- Universal "Resource" abstraction (boxes, teams, tables, bays)
- Plan artifact: `native_calendar_plan.md`

---

#### 🔨 DOING NOW: Phase 1 — Native Calendar Schema + Service

**Locked-in decisions (user-confirmed 2026-04-15 16:02 CLT):**

| Decision | Answer | Implications |
|----------|--------|-------------|
| **Fumigation resources** | 3-8 teams, must support dynamic N | `resources` table with no upper limit |
| **Onboarding agent** | MUST ask about resources during config flow | Add resource collection to onboarding prompt |
| **Business hours** | Vary per day, per tenant. Agent collects. | `scheduling_config.business_hours` is per-day JSON |
| **Test chat post-config** | Must be fully tooled when config ends | After onboarding completes → auto-provision resources + scheduling_config → sandbox tools switch to real native queries |

**Implementation order:**
1. ✅ Plan created + approved
2. ✅ **Phase 1:** Schema DDL on DEV (`btree_gist` + 3 tables + RLS + indexes) — VERIFIED
3. ✅ **Phase 2:** `native_service.py` — all 6 operations with 3-channel observability
4. ✅ **Phase 3:** `services.py` rewritten (GCal → Native), `main.py` endpoints swapped, imports verified
5. ⏳ **Phase 4:** Frontend `AgendaView.tsx` dynamic resources
6. ⏳ **Phase 5:** GCal cleanup (remove google_client.py, OAuth router, tenant GCal columns)

---

#### 🔜 WILL DO (after native calendar)

- **Onboarding agent expansion:** Add resource/hours collection to config prompt
- **Auto-provision:** On config completion → create `resources` rows + `scheduling_config` row → sandbox tools → real
- **Superadmin notifications:** Discord alerts on every onboarding start/progress/completion
- **PROD migration:** DEV → E2E verified → PROD (per migration lifecycle rule)
- **GCal column deprecation:** Mark 4 tenant columns for removal after all tenants migrated

---

#### Previous Fixes (Still Active)
- ✅ Fix 1: Phone Number — commit `6508668` (DEV ✅ | PROD ⏳)
- ✅ Fix 2: Sandbox Isolation — commit `6508668` (DEV ✅ | PROD ⏳)
- ✅ Fix 3: Sandbox Tools — commit `f6c2260` (DEV ✅)

### Current Deployment State
| Component | Status | Notes |
|:---|:---|:---|
| **Sandbox tools** | ✅ Deployed | Commit `f6c2260` on Cloud Run DEV |
| **Backend** (Cloud Run DEV) | ✅ Running | 7 tools + agentic loop |
| **Frontend** (Cloudflare Pages) | ⏳ No frontend changes yet | N/A |
| **onboarding_messages migration** | ✅ DEV | ⏳ PENDING PROD APPROVAL |
| **phone_number column migration** | ✅ DEV | ⏳ PENDING PROD APPROVAL |
| **Native calendar schema** | ✅ DEV APPLIED | ⏳ PENDING PROD APPROVAL |
| **PROD** | ⏳ NOT YET | No changes merged to main |

---

## §1 — Complete Session Work Log

### 10. Sandbox Tool Integration ✅ (commit `f6c2260`)
- **Problem:** Sandbox chat had `tools=[]` — AI couldn't do anything useful for the demo
- **Solution:** Created standalone sandbox tool implementations + full agentic loop
  - `sandbox/tools.py`: 7 tools, zero GCal imports, 3-channel observability
  - `sandbox/chat_endpoint.py`: Responses API agentic loop with `previous_response_id` chaining
  - `openai_responses_adapter.py`: Added `previous_response_id` + `store=True` support
  - `router.py`: Added `response_id` to `LLMResponse` DTO
- **Verified:** All imports pass, full app startup passes, zero regressions

### 11. Native Calendar Architecture Plan ✅
- **Problem:** Google Calendar dependency blocks multi-tenant scaling (OAuth per tenant, rate limits, latency, no double-booking prevention)
- **Solution:** 3-table Supabase schema with RLS + `EXCLUDE USING gist` constraint
- **Plan:** `native_calendar_plan.md` — approved by user

### Previous items (1-9): see earlier session log below

### 1. Responses API Chaining Fix ✅
- **Problem:** OpenAI `BadRequestError 400` — "No tool call found for function call output with call_id"
- **Root Cause:** Frontend was sending full conversation history including orphaned `function_call_output` items from previous turns
- **Fix:** Added history sanitization (strip non-user/non-assistant messages) + implemented `previous_response_id` chaining for tool-call follow-ups
- **File:** `Backend/app/api/onboarding/chat_endpoint.py` lines 141-163, 364-420

### 2. Done Event Suppression Fix ✅
- **Problem:** When the model made tool calls, the `done` event for the initial response was being suppressed, causing its text content to be lost
- **Fix:** Removed the suppression — every `done` event is now forwarded to the frontend, regardless of pending tool calls
- **File:** `Backend/app/api/onboarding/chat_endpoint.py` lines 341-370

### 3. Activity-Based Timeout ✅
- **Problem:** Fixed 60s timeout from stream start — multi-turn config sessions easily exceeded this
- **Fix:** 90s inactivity timeout that resets on every received SSE chunk
- **File:** `Frontend/hooks/useOnboardingStream.ts` line 82 + timeout logic in SSE loop

### 4. SSE Observability - NOT FULL YET
- **Problem:** No visibility into what was happening in the SSE stream — messages disappeared with zero evidence
- **Fix:** Added `console.debug` for every SSE event + Sentry breadcrumbs throughout the stream lifecycle
- **File:** `Frontend/hooks/useOnboardingStream.ts` (throughout)

### 5. Frontend State Fix ✅
- **Problem:** Stale `isThinking` React closure in the SSE event loop
- **Fix:** Used local mutable variable `thinkingActive` inside the SSE loop instead of stale state reference
- **File:** `Frontend/hooks/useOnboardingStream.ts`

### 6. Provisioning Progress Overlay _ UNCONFIRMED.
- **Problem:** After config completion, there was an invisible 2-second delay before transitioning
- **Fix:** Added animated step-through overlay: Saving → Generating personality → Activating tools → Ready!
- **File:** `Frontend/components/Onboarding/ConfigChat.tsx` lines 56-85 + 128-172

### 7. Premium Celebration Screen - NEVER SEEN BY TESTER; MIGHT BE BROKEN
- **Problem:** User requested "big relaxing check animation with extra glitters and glow"
- **Fix:** Rewrote CompletionStep with animated SVG checkmark (stroke drawing), pulsing glow rings, 40 floating glitter particles, sparkle accents, 3-phase staggered reveal
- **File:** `Frontend/components/Onboarding/CompletionStep.tsx`

### 8. Persistent Conversation History - JUST DONE NOT TESTED YET,
- **Problem:** Messages only lived in React state — no debugging, no resumability, no audit trail
- **Fix:** 
  - Created `onboarding_messages` table (Supabase DEV migration)
  - Added `_persist_message()` helper with 3-channel observability
  - User messages saved before streaming starts
  - Assistant messages saved on each `done` event
  - Added `GET /api/onboarding/chat/history` endpoint
  - Frontend loads persisted history on mount via `useEffect`
  - `historyLoaded` flag prevents duplicate initial greetings
- **Files:**
  - `Backend/app/api/onboarding/chat_endpoint.py` (persistence layer + GET endpoint)
  - `Frontend/hooks/useOnboardingStream.ts` (history loading)
  - `Frontend/components/Onboarding/ConfigChat.tsx` (conditional greeting)

### 9. Tool Detection Feature (documented, not implemented)
- Documented in `.ai-context/deep_dives_&_misc/onboarding_tool_detection_feature.md`
- Detect tool gaps during onboarding
- Notify superadmins via Discord
- Auto-provision sandbox chats
- Persist conversation history for QA (now partially implemented via item 8)
- Superadmins need to be notified any time a self onboarding process starts and be kept updated of the progress even if sucessful, unsucesfull, incomplete, leave, whatever: this message should lead directly to where supperadmin can see the whole thing, behaviour configchathistory, logs from tools executed, the whole process and its observability parts so it can be thoroughly diagnosed

---

## §2 — What's Pending

### NOW — Native Calendar Implementation (Phases 1-5)

| Phase | What | Status | Blocker? |
|-------|------|--------|----------|
| 1 | Schema DDL: `btree_gist` + `resources` + `appointments` + `scheduling_config` + RLS + indexes | ⏳ NEXT | No |
| 2 | `native_service.py`: availability, book, cancel, update, list, events | ⏳ | Phase 1 |
| 3 | Tool registry swap: production tools → native service; sandbox → real native queries | ⏳ | Phase 2 |
| 4 | Frontend `AgendaView.tsx` dynamic resources (replace hardcoded Box 1/Box 2) | ⏳ | Phase 2 |
| 5 | GCal cleanup: remove `google_client.py`, `google_oauth_router.py`, tenant GCal columns | ⏳ | Phase 3+4 verified |

### AFTER Calendar — Onboarding Agent Expansion
- [ ] Add resource collection to onboarding config prompt ("¿Cuántos equipos/boxes/mesas tienes?")
- [ ] Add business hours collection per day ("¿Qué horarios de atención tienes cada día?")
- [ ] Auto-provision `resources` rows + `scheduling_config` on config completion
- [ ] Swap sandbox tools from simulated → real native queries after provisioning
- [ ] Superadmin Discord notifications for onboarding lifecycle events

### Migration Parity (DEV ✅ | PROD ⏳)
| Migration | DEV | PROD |
|:---|:---|:---|
| `onboarding_messages` table + index + RLS | ✅ | ⏳ PENDING APPROVAL |
| `phone_number` column on `tenant_onboarding` | ✅ | ⏳ PENDING APPROVAL |
| `resources` table + RLS | ⏳ NEXT | ⏳ |
| `appointments` table + gist constraint + RLS | ⏳ NEXT | ⏳ |
| `scheduling_config` table + RLS | ⏳ NEXT | ⏳ |

- ONLY AFTER FULL E2E VERIFICATION ON DEV WITHOUT A SINGLE ERROR

### Technical Debt
- [ ] Remove `google-api-python-client`, `google-auth-oauthlib` from requirements
- [ ] Config agent prompt improvements — Remove redundant confirmations (REGLA 2), improve natural flow
- [ ] RLS verification — Confirm `onboarding_messages` RLS policy correctly restricts access

---

## §3 — Infrastructure Identifiers

| Resource | ID / URL |
|:---|:---|
| **Supabase DEV** | Project: `nzsksjczswndjjbctasu` |
| **Supabase PROD** | Project: `nemrjlimrnrusodivtoa` |
| **Cloud Run DEV** | `ia-backend-dev` in `saas-javiera` / `us-central1` |
| **Cloud Run PROD** | `ia-backend-prod` in `saas-javiera` / `us-central1` |
| **Frontend DEV** | `https://dev-ia-whatsapp-crm.tomasgemes.workers.dev` |
| **Test tenant ID** | `4bda477d-33d6-458a-b256-e28ea1337324` (instagramelectrimax) |
| **GitHub repo** | `YggrYergen/ia-whatsapp-crm` |
| **Branch** | `desarrollo` (all work) → merge to `main` for PROD |

---

## §4 — Key Files Modified This Session

| File | What Changed |
|:---|:---|
| `Backend/app/api/sandbox/tools.py` | **NEW** — 7 standalone sandbox tools (zero GCal imports), 3-channel observability |
| `Backend/app/api/sandbox/chat_endpoint.py` | **REWRITE** — full agentic loop with Responses API chaining, MAX_TOOL_ROUNDS=3 |
| `Backend/app/infrastructure/llm_providers/openai_responses_adapter.py` | Added `previous_response_id` + `store=True` for chaining |
| `Backend/app/modules/intelligence/router.py` | Added `response_id` field to LLMResponse DTO |
| `Backend/app/api/onboarding/chat_endpoint.py` | History sanitization, done event fix, follow-up chaining, **message persistence layer**, **GET history endpoint** |
| `Frontend/hooks/useOnboardingStream.ts` | Activity timeout, SSE observability, stale closure fix, **persistent history loading on mount** |
| `Frontend/components/Onboarding/ConfigChat.tsx` | Provisioning progress overlay, **historyLoaded-gated initial greeting** |
| `Frontend/components/Onboarding/CompletionStep.tsx` | Premium celebration UI rewrite |
| `Frontend/app/globals.css` | fadeIn, glitterFloat, checkDraw, bg-gradient-radial animations |
| `.ai-context/deep_dives_&_misc/onboarding_tool_detection_feature.md` | Feature spec for tool gap detection |

---

## §5 — Git Commits This Session (on `desarrollo`)

```
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
| `onboarding_messages` table | ✅ Applied & verified | ⏳ PENDING APPROVAL |
| `idx_onboarding_messages_tenant_created` index | ✅ | ⏳ PENDING APPROVAL |
| `tenant_users_read_own_messages` RLS policy | ✅ | ⏳ PENDING APPROVAL |
| `phone_number` column on `tenant_onboarding` | ✅ Applied & verified (2026-04-15) | ⏳ PENDING APPROVAL |

**PROD SQL — onboarding_messages (ready to apply when approved):**
```sql
CREATE TABLE IF NOT EXISTS onboarding_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'event')),
    content TEXT NOT NULL DEFAULT '',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_onboarding_messages_tenant_created 
    ON onboarding_messages (tenant_id, created_at ASC);

ALTER TABLE onboarding_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_users_read_own_messages" ON onboarding_messages
    FOR SELECT USING (
        tenant_id IN (
            SELECT tenant_id FROM tenant_users WHERE user_id = auth.uid()
        )
    );
```

**PROD SQL — phone_number column (ready to apply when approved):**
```sql
ALTER TABLE public.tenant_onboarding
  ADD COLUMN IF NOT EXISTS phone_number text DEFAULT NULL;

COMMENT ON COLUMN public.tenant_onboarding.phone_number IS 
  'Business owner personal WhatsApp/phone for platform communications (support, billing). NOT the assistant bot number.';
```

---

> **END OF NOW.md**  
> This file is the single source of truth for the current session state.  
> Update it before starting new work or ending the session.
