# 🚀 AI WhatsApp CRM — Session Prompt

> **Usage:** Copy this prompt into each new Antigravity session. Update ONLY the `[MODIFIABLE]` sections.  
> **IMMUTABLE sections** (`🔒`) must NEVER be altered — they contain operational rules that prevent catastrophic errors.  
> **MODIFIABLE sections** (`✏️`) must be updated before every session to reflect current state.  
> **Last structural update:** 2026-04-11

---

## ✏️ [MODIFIABLE] §0 — Session Identity

```
SESSION DATE:    2026-04-11
CURRENT SPRINT:  Sprint 1
CURRENT DAY:     Day 1 of Sprint (Saturday — most critical day)
SESSION GOAL:    Blocks A+B+C+D+E+F DONE ✅ — Full observability + resilience — Block G next
SESSION BLOCKS:  A (✅), B (✅), C (✅), D (✅), E (✅), F (✅), G (← NOW), H
LAST COMMIT:     5f7e5e1 (desarrollo) — Block F correlation IDs + Sentry tags
```

---

## ✏️ [MODIFIABLE] §1 — Big Picture: Where We Are

> Update this section before every session. It is the agent's primary situational awareness.

### What This Project Is
AI WhatsApp CRM SaaS — a multi-tenant platform where businesses get an AI assistant on WhatsApp that handles customer conversations, books appointments, escalates to humans, and tracks customer intelligence. Currently live with 1 client (CasaVitaCure, wellness center), onboarding 2nd client (fumigation business) on Tuesday April 15. Goal: 7 paying clients by May 4.

### What Has Been Done (Completed)
- ✅ Full backend (FastAPI) + frontend (Next.js 15) deployed to Cloud Run + Cloudflare Pages
- ✅ WhatsApp Cloud API integration working (send/receive messages, webhooks)
- ✅ OpenAI LLM integration with 7 tools (scheduling, scoring, escalation)
- ✅ Supabase multi-tenant database (tenants, contacts, messages, bookings)
- ✅ Google Calendar integration (hardcoded to CasaVitaCure — needs multi-tenant refactor, deferred)
- ✅ Sentry + Discord observability (basic — needs correlation IDs)
- ✅ Dev/prod environment separation (independent Cloud Run + Supabase instances)
- ✅ Phase 5D live testing with first client — identified BUG-5 (95% false positive alerts) and BUG-6 (unacceptable response quality)
- ✅ Deep research session (50+ web searches): model pricing corrected, BSUID migration identified, Graph API deprecation found, 12 critical corrections documented (CC-1 to CC-12)
- ✅ Sprint 1 v2 plan approved: Dashboard MVP deferred to Sprint 2, replaced with resilience layer + system prompt engineering
- ✅ Model decision finalized: `gpt-5.4-mini` for PROD, `gpt-5.4-nano` for DEV/budget, `max_completion_tokens=500` cost cap
- ✅ **Block A executed & deployed** (2026-04-11):
  - A1: Model `gpt-4o-mini` → `gpt-5.4-mini` in 3 backend files + frontend dropdown + tests
  - A2: Removed `.lower()` on text_body — casing preserved (verified: "Te llamas Tomás" in logs)
  - A3: Disabled BUG-5 (TOOL_ACTION_PATTERNS) — 0 false alerts in DEV logs
  - A4: History limit 20 → 30 messages
  - A5: Graph API v19.0 → v25.0 (v19 dies May 21, 2026)
  - A6: `max_completion_tokens=500` cost cap added
- ✅ **Observability Hardening** (2026-04-11):
  - All 7 tools in `tools.py` wrapped with try/except + Sentry + Discord + diagnostic context
  - Infrastructure: supabase_client, proactive_worker, google_oauth_router, discord_notifier self-instrumented
  - §6 Observability-First Rule added as IMMUTABLE to SESSION_PROMPT
  - 10 blind spots eliminated (5/7 tools had ZERO error handling previously)
- ✅ **Block B executed & deployed** (2026-04-11):
  - B1: All 7 tool schemas migrated to `strict: true` + `additionalProperties: false`
  - 4 optional params converted to nullable: `duration_minutes`, `phone`, `patient_phone`, `clinical_notes`
  - `parallel_tool_calls=False` added to OpenAI adapter (required for strict mode per docs)
  - ⚠️ Hotfix: `parallel_tool_calls` must be OMITTED (not null) when no tools — SDK sends null as JSON null
  - Verified: escalation tool works ✅, booking tool hits expected GCal 403 on DEV (by design — no calendar in dev)
- ✅ **Block C executed & deployed** (2026-04-11):
  - C1: Content now ALWAYS preserved from LLM response (was silently discarded with tool_calls)
  - C2: Usage tracking (prompt/completion/cached/reasoning tokens + model) added to LLMResponse DTO
  - 3 observability gaps fixed: SDK missing alert, usage parsing isolation, constructor warning
- ✅ **Supabase DEV DB fixes** (2026-04-11):
  - Added `messages_delete_own` RLS policy (ENVIAR PRUEBA button was silently failing to delete)
  - Added `contacts` to `supabase_realtime` publication (bot_active changes weren't reaching frontend)
  - Both verified via SQL queries against dev DB
- ✅ **Block D executed & deployed** (2026-04-11):
  - D1: Rewrote agentic loop in `use_cases.py` — multi-round with `MAX_TOOL_ROUNDS = 3`
  - Proper `role: "tool"` + `tool_call_id` protocol (was `role: "user"` — WRONG)
  - Assistant `tool_calls` messages appended to history between rounds
  - Usage tracking accumulation across all rounds
  - All 22 failure points instrumented with Sentry + Discord (16 except blocks, 19 Sentry, 20 Discord)
  - Tested via sandbox: simple greeting ✅, tool calls ✅, escalation ✅, multi-round ✅, regression ✅
- ✅ **Block E executed & deployed** (2026-04-11):
  - E1: HMAC-SHA256 webhook signature verification (`security.py` + ASGI middleware in `main.py`)
    - `META_APP_SECRET` stored in Google Secret Manager (both DEV + PROD)
    - Soft mode: if secret missing, logs warning and skips (safe rollout)
  - E2: LLM rate limit per contact — 20/hr max (`rate_limiter.py` NEW)
    - In-memory sliding window, auto-prune, polite throttle message
  - E3: Processing lock TTL — 90s stale lock force-release
    - DB migration: added `updated_at` column + auto-update trigger to `contacts` table
  - E4: Shadow-forwarding — full conversation forwarded to admin WhatsApp
    - Uses tenant's own `ws_phone_id` + `ws_token` (dynamic per tenant, no hardcoded numbers)
    - `SHADOW_FORWARD_PHONE=56931374341` set on both DEV + PROD
  - E5: UptimeRobot health monitoring — manual setup (endpoint: `/api/debug-ping`)
  - E6: Tenant config cache — `TTLCache(maxsize=50, ttl=180)` in `dependencies.py`
    - Added `cachetools>=5.3.0` to `pyproject.toml`
  - Telemetry totals: security.py 7 Sentry/6 Discord, rate_limiter.py 3/2, dependencies.py 6/4, use_cases.py 31/23
- ✅ **Block F executed & deployed** (2026-04-11):
  - F1: `asgi-correlation-id` middleware added (outermost) — generates unique request ID per request
  - F2: `SentryTagsMiddleware` sets `correlation_id` + `request_path` on every Sentry event
    - Pipeline also sets `tenant_id` + `correlation_id` for deep tracing
  - F3: Logger updated — `%(correlation_id)s` in both dev (human-readable) and prod (JSON) formats
  - Middleware order: CorrelationId → SentryTags → WebhookSignature → CORS
  - Dependencies: `asgi-correlation-id>=4.3.0` added to `pyproject.toml`

### What Is Being Done RIGHT NOW (This Session)
**Blocks A, B, C, D, E, F — ✅ ALL DEPLOYED to DEV**
**Observability + DB fixes — ✅ APPLIED**

**Block G — BSUID Dormant Capture: DB + Backend (20 min) ← NOW** (Phase 1: store data, zero behavior change)
**Block H — Test & deploy Day 1 (30 min)**

### What Comes Next (After This Session)
- Day 2 (Sun): Blocks I (system prompt engineering 3-4h), J (escalation UX), K (provisioning script), L (status page)
- Day 3 (Mon): Blocks M (fumigation tenant setup), N (E2E testing), O (Meta audit)
- Day 4 (Tue): Blocks P (go-live 🚀), Q (post-onboarding)
- Sprint 2: Dashboard MVP, Instagram DM, multi-squad booking, gpt-5.4-nano testing

### Known Blockers & Risks
- ~~⚠️ `META_APP_SECRET` env var needed for Block E1~~ → **Stored in Google Secret Manager, set on both DEV + PROD**
- ~~⚠️ Block D (agentic loop) is the highest-risk block~~ → **DONE ✅ — tested via sandbox, all 5 tests passed**
- ~~⚠️ CasaVitaCure client is experiencing poor AI responses RIGHT NOW — Block A deployment provides immediate relief~~ → **Deployed to DEV**
- ~~⚠️ Graph API v19.0 deprecation deadline: May 21, 2026 (40 days)~~ → **Fixed: now v25.0**
- ⚠️ OpenAI platform docs (platform.openai.com) return 403 when accessed programmatically — use `search_web` to verify API details instead
- ⚠️ Google Calendar tools return 403 on DEV — **BY DESIGN** (no GCal credentials in dev, production client data isolation). Booking engine in Sprint 2 will replace GCal dependency.
- ⚠️ `parallel_tool_calls` param must be OMITTED (not set to None/null) when no tools — OpenAI SDK serializes None as JSON null which the API rejects
- ⚠️ Shadow-forwarding (E4) uses tenant's WABA phone → admin number. Requires active 24h conversation window on admin's WhatsApp. If window expired, forward silently fails (non-blocking).

---

## ✏️ [MODIFIABLE] §2 — Key Decisions & Context

> Record ALL significant decisions that have been made. An agent that doesn't know about a decision WILL contradict it.

| Decision | Choice | Date | Rationale |
|:---|:---|:---|:---|
| Production LLM model | `gpt-5.4-mini` ($0.75/$4.50/1M) | 2026-04-11 | Best tool calling + agentic performance. Both mini and nano share exact same API. |
| Dev/budget LLM model | `gpt-5.4-nano` ($0.20/$1.25/1M) | 2026-04-11 | For simple tenants or dev testing. API-compatible with mini. |
| Cost cap | `max_completion_tokens=500` per response | 2026-04-11 | Caps output cost at ~$0.00225/response. Maintains 88-90% margins. |
| Dashboard MVP | Deferred to Sprint 2 | 2026-04-11 | Time invested in system prompts + resilience instead. Bot quality > dashboard. |
| Sprint 1 strategy | Deploy Block A first, then iterate | 2026-04-11 | Client experiencing bad responses NOW. Every hour without fix = reputation damage. |
| Instagram/booking | Sprint 2 priority (SELLING POINTS) | 2026-04-11 | Not needed for Tuesday, but critical for sales outreach. |
| Fumigation prompt | DRAFT in Sprint 1, refine WITH client | 2026-04-11 | Can't perfect a prompt without the business owner's input. |
| Shadow-forwarding | Include BOTH user messages AND bot responses | 2026-04-11 | Full interaction visibility for quality monitoring. |
| Rate limit behavior | Auto-resume when limit refreshes + notify us | 2026-04-11 | Don't permanently block contacts, just throttle + alert. |
| Config cache | 3-min TTL, ~250KB for 50 tenants | 2026-04-11 | Negligible memory vs 512MB Cloud Run limit. |
| WhatsApp provisioning | Our WABA short-term → client-owned WABA before tenant #7 | 2026-04-11 | Meta compliance risk. Embedded Signup in Sprint 3-4. |
| BSUID implementation | Dormant capture (Phase 1) — store now, activate before June | 2026-04-11 | Full forensic (40+ touch points) confirmed zero behavioral risk. 4 lines backend + 1 migration. Phase 2 (lookup swap, nullable phone, tool updates) is separate task. |
| BSUID Phase 2 deadline | Must be deployed before June 2026 | 2026-04-11 | Meta enables username hiding in June — `from` field may contain BSUID. Without Phase 2, contact lookup breaks silently. |

### Active Bugs & Critical Corrections
| ID | Issue | Status | Fix Location |
|:---|:---|:---|:---|
| BUG-5 | Silent Failure Detector 95%+ false positives | ✅ Disabled (DEV) | Block A3: commented L219-L242 `use_cases.py` |
| BUG-6 | Response quality unacceptable in production | 🟡 Partial (A done) | Blocks B-D remaining: tools, adapter, agentic loop |
| CC-1 | Codebase uses deprecated `gpt-4o-mini` | ✅ Fixed (DEV) | Block A1: 3 backend + frontend + tests |
| CC-3 | BSUID dormant capture (Phase 1 of 2) | 🟡 Phase 1 | Block G1-G4: column + index + extract + store + backfill. Phase 2 (lookup swap) before June 2026. |
| CC-4 | Graph API v19.0 deprecated May 21, 2026 | ✅ Fixed (DEV) | Block A5: now v25.0 |
| CC-5 | Tool schemas missing `strict: true` | ✅ Fixed (DEV) | Block B1: all 7 tools + `parallel_tool_calls=False` |
| CC-7 | No webhook signature verification | ✅ Fixed (DEV+PROD) | Block E1: HMAC-SHA256 middleware + Secret Manager |
| CC-8 | No LLM rate limit per contact | ✅ Fixed (DEV) | Block E2: 20/hour max in `rate_limiter.py` |
| CC-9 | `is_processing_llm` lock has no TTL | ✅ Fixed (DEV) | Block E3: 90s TTL + `updated_at` column |
| CC-10 | No health monitoring | 🟡 In progress | Block E5: UptimeRobot — manual setup by user |
| CC-11 | No conversation shadow-forward | ✅ Fixed (DEV+PROD) | Block E4: tenant-dynamic forwarding to admin phone |
| CC-12 | Tenant config fetched every request | ✅ Fixed (DEV) | Block E6: TTLCache(50, 180s) in `dependencies.py` |
---

## 🔒 [IMMUTABLE] §3 — Context Files: Where to Find What

> [!CAUTION]
> **READ THESE FILES BEFORE WRITING ANY CODE.** The agent MUST read the relevant files BEFORE starting work. Not after. Not "as needed." BEFORE.

### Mandatory Pre-Session Reading (in this order)
1. **`.ai-context/task.md`** — Task tracker with per-step documentation links (📚). This is the execution playbook.
2. **`.ai-context/master_plan.md`** — Business context, financial model, architecture roadmap, risk register.
3. **`README.md`** §0 (System Architecture) + §0.9 (Active Bugs/CCs) — Current state of the system.
4. **`.ai-context/implementation_plan.md`** — Full phase history + Sprint execution blocks with doc URLs.

### Deep Dives (Load on demand per block)
5. **`.ai-context/deep_dive_a_response_quality.md`** — BUG-6 fix specification, LLM tool calling, agentic loop design.
6. **`.ai-context/deep_dive_b_multi_channel.md`** — WhatsApp/Instagram/BSUID, Meta compliance, webhook architecture.
7. **`.ai-context/deep_dive_c_dashboard_ux.md`** — Dashboard design, observability, correlation IDs, Sentry integration.

### Execution Tracker
8. **`.ai-context/execution_tracker.md`** — Day-by-day progress log. Update after every completed block.

> [!IMPORTANT]
> Every block in `task.md` has 📚-linked documentation URLs. Those URLs are NOT decorative. They contain version-specific implementation details, edge cases, and required behaviors that CANNOT be guessed. OPEN AND READ THEM.

### ⚠️ Context Loading Strategy — CRITICAL FOR SESSION PERFORMANCE

> [!WARNING]
> **DO NOT load all `.ai-context/` files at once.** The deep dives alone are 40+ URLs each. Loading everything upfront causes context window pressure, degraded reasoning, and "lost in the middle" failures. Use phased loading instead.

#### Phase 1: Session Start (ALWAYS load these)
```
1. SESSION_PROMPT.md          ← You're reading this. Contains all rules.
2. task.md §Sprint 1          ← The execution playbook. Lines ~646-865.
3. README.md §0 + §0.9       ← Architecture + active bugs. Lines 1-110.
4. master_plan.md §0 + §2    ← Business context + financial model. Skim rest.
```

#### Phase 2: Per-Block Loading (load ONLY when starting that block)
| Block(s) | Load This Deep Dive | Why |
|:---|:---|:---|
| **A** (quick wins) | Nothing extra — task.md has everything | Simple config changes |
| **B** (strict tools) | `deep_dive_a` §3 Phase 3 | Tool-by-tool migration checklist |
| **C** (adapter) | `deep_dive_a` §3 Phase 2 | Response object shape details |
| **D** (agentic loop) ⭐ | `deep_dive_a` §3 Phase 4 — **READ FULLY** | Complete rewrite specification |
| **E** (resilience) | `deep_dive_b` §1 (webhooks) | Webhook signature + BSUID format |
| **F** (observability) | `deep_dive_c` §3 | Correlation ID setup code example |
| **G** (DB migration) | `deep_dive_b` §1 (BSUID) | BSUID webhook payload example |
| **H** (test & deploy) | Nothing extra | Integration testing |
| **I** (system prompts) | Nothing extra | Creative work, not API-dependent |
| **J-Q** | Relevant deep dive sections as needed | Day 2-4 blocks |

#### Phase 3: Documentation URLs (load per-step)
When you reach a step with a 📚 link in `task.md`:
1. Open the URL via `read_url_content` or `search_web`
2. Extract the relevant section (don't load the entire page into context)
3. Implement based on what you read
4. Move to the next step

#### If the session gets "confused" or quality degrades:
1. **STOP.** Do not push through.
2. Ask the user to start a new session with a fresh context
3. Capture current state in `execution_tracker.md` BEFORE ending
4. The new session starts from Phase 1 with updated §0-§2

---

## 🔒 [IMMUTABLE] §4 — The Documentation-First Rule

> [!CAUTION]
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
- A "works on my machine" implementation that violates the official spec WILL break in production. There is no "probably fine."
- **The cost of reading docs: 5 minutes. The cost of NOT reading docs: hours of debugging + potential production incident affecting real clients.**

### The Documentation Chain
```
task.md 📚 links → Official docs (OpenAI, Meta, etc.) → Deep Dives (project-specific notes)
                                    ↓
                    If insufficient: web search for latest official docs
                                    ↓
                    If STILL insufficient: flag to user before proceeding
```

### Mandatory Web Search Triggers
The agent MUST perform fresh web searches when:
- The task involves an API version change or migration
- The existing 📚 link returns a 404 or redirects to a different page
- The task involves security-sensitive operations (webhook verification, auth, tokens)
- The agent encounters unexpected API behavior that contradicts the docs
- More than 30 days have passed since the Deep Dive was last updated

---

## 🔒 [IMMUTABLE] §5 — The Logs-First Debugging Rule

> [!CAUTION]
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

### Error Escalation
If after genuine diagnosis the root cause cannot be identified:
1. Document exactly what was tried and what evidence was gathered
2. Flag to the user immediately with all diagnostic output attached
3. Do NOT attempt speculative fixes — they create more problems than they solve

---

## 🔒 [IMMUTABLE] §6 — The Observability-First Rule

> [!CAUTION]
> **EVERY code change MUST include Sentry + Discord instrumentation.** If an error can happen, we MUST know about it instantly. Silent failures are production killers.

### The Rule
When writing or modifying ANY code that could fail (API calls, DB operations, tool execution, external services, data parsing):

1. **Wrap in try/except** — Every call to an external service or potentially-failing operation MUST be wrapped.
2. **Log to `logger`** — Include the function/tool name, tenant_id (if available), and relevant input parameters for fast diagnosis.
3. **Capture in `sentry_sdk`** — Use `sentry_sdk.capture_exception(e)` for errors, `sentry_sdk.capture_message()` for warnings. Use `sentry_sdk.set_context()` to attach diagnostic data (tool name, tenant_id, kwargs).
4. **Alert via `send_discord_alert()`** — Every error-level exception must also fire a Discord alert with:
   - A descriptive title including the component name and tenant_id
   - A description with the relevant parameters + first 300 chars of the error
   - The `error=e` kwarg for automatic traceback attachment
   - Appropriate `severity` ("error", "warning", "info")
5. **Even gracefully handled errors must report** — If you catch an error and return a fallback value, STILL report to Sentry + Discord. The fact that the user didn't see a crash doesn't mean we shouldn't know about it.

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
    return fallback_value  # Graceful degradation
```

### Explicitly Forbidden
- ❌ `except Exception: pass` → **NEVER swallow errors silently**
- ❌ `except Exception as e: logger.error(e)` alone → **MUST also Sentry + Discord**
- ❌ Bare function calls without try/except on external services → **ALWAYS wrap**
- ❌ Early returns without reporting (e.g., `if not tenant: return error`) → **MUST log + Sentry**

### Required Imports (in every file that handles errors)
```python
import sentry_sdk
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger
```

---

## 🔒 [IMMUTABLE] §7 — The No-Assumptions Testing Rule

> [!IMPORTANT]
> **Changes are NOT complete until they are TESTED and VERIFIED.** Code that compiles is not code that works.

### The Rule
After implementing any change:

1. **Unit verification** — Does the specific function/module work in isolation?
2. **Integration verification** — Does it work with the rest of the system? (API calls, database, external services)
3. **Live verification** (when applicable) — Does it work in the actual production/staging environment?
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

## 🔒 [IMMUTABLE] §8 — Progress & Documentation Preservation Rules

> [!CAUTION]
> **Information loss is IRREVERSIBLE.** Once a decision, finding, or implementation detail is lost from the docs, it is gone forever. The next session will not know it existed.

### Rule 1: Never Remove Key Information
- **DO NOT** delete or overwrite content from `task.md`, `implementation_plan.md`, `README.md`, or deep dives without explicit user approval.
- **DO NOT** replace detailed content with summaries. Summaries lose nuance. Nuance prevents bugs.
- **ALWAYS** append, annotate, or update-in-place. Mark completed items with `[x]`, add status notes, update dates — but NEVER delete the item or its documentation links.

### Rule 2: Update Progress Immediately
After completing any block or sub-task:
1. Mark it `[x]` in `task.md`
2. Add a completion note with date and any learnings
3. Update `execution_tracker.md` with what was done, what was found, any deviations from plan
4. If a decision was made during implementation, add it to `README.md` and the relevant Deep Dive

### Rule 3: Preserve Documentation Links
- **NEVER** remove 📚 URLs from `task.md` or `implementation_plan.md`, even after a task is completed
- These links are the audit trail for WHY something was implemented a certain way
- Future refactors WILL need to reference the original documentation

### Rule 4: Record Deviations
If the implementation deviates from the plan (different approach, unexpected constraint, partial implementation):
1. Document WHAT was different and WHY
2. Update `task.md` with the actual approach taken
3. Flag any downstream impacts on future blocks

### Rule 5: Session Handoff
At the END of every session, ensure:
1. All completed tasks are marked in `task.md`
2. `execution_tracker.md` is updated with session summary
3. Any new decisions or findings are recorded in the appropriate files
4. The `[MODIFIABLE]` sections of this prompt are updated for the next session
5. A `git commit` captures the stable state

---

## 🔒 [IMMUTABLE] §8 — Operational Guardrails

### Code Safety
- **NEVER** deploy directly to production without user approval
- **NEVER** modify environment variables or secrets without user confirmation
- **NEVER** delete data from Supabase production tables
- **ALWAYS** test locally or in dev environment before staging for production
- **ALWAYS** create a git commit before AND after significant changes (safety net)

### 🔴 Git Branch & Deployment Architecture

> [!CAUTION]
> **Pushes to branches trigger AUTOMATIC deployments.** There is NO manual step. The moment you `git push`, builds start.

#### How the Auto-Deploy Triggers Work

**Backend (Google Cloud Run via Cloud Build):**
- A **Cloud Build trigger** watches the GitHub repo for pushes
- Push to `main` → triggers Cloud Build → 3-step pipeline: **Build** (Dockerfile) → **Push** (to Artifact Registry) → **Deploy** (to Cloud Run service)
- Push to `desarrollo` → same pipeline but targets the DEV Cloud Run service
- Build context: `Backend/` directory only (changes to `.ai-context/`, `Frontend/`, docs do NOT trigger backend rebuilds, but the trigger still fires — it just builds the same image)
- Build time: ~2-5 minutes from push to live
- Service account: `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com`

**Frontend (Cloudflare Pages via Workers Builds):**
- Cloudflare Pages is connected to the GitHub repo
- Push to `main` → auto-builds and deploys production frontend
- Push to `desarrollo` → auto-builds and deploys dev/preview frontend
- Build uses OpenNext to compile Next.js 15 for Cloudflare Workers runtime

```
┌──── git push origin desarrollo ────┐     ┌──── git push origin main ────────┐
│                                     │     │                                   │
│  Cloud Build (saas-javiera)         │     │  Cloud Build (casavitacure-crm)   │
│  ├─ Build: Backend/Dockerfile       │     │  ├─ Build: Backend/Dockerfile     │
│  ├─ Push: → Artifact Registry       │     │  ├─ Push: → Artifact Registry     │
│  └─ Deploy: → ia-backend-dev        │     │  └─ Deploy: → ia-backend-prod     │
│                                     │     │                                   │
│  Cloudflare Workers Builds          │     │  Cloudflare Workers Builds        │
│  └─ Deploy: → DEV Pages            │     │  └─ Deploy: → PROD Pages          │
│                                     │     │                                   │
│  Database: Supabase DEV             │     │  Database: Supabase PROD          │
└─────────────────────────────────────┘     └───────────────────────────────────┘
```

| Branch | Backend Service | GCP Project | Frontend | Database |
|:---|:---|:---|:---|:---|
| `desarrollo` | `ia-backend-dev` | `saas-javiera` | Dev Cloudflare Pages | Supabase DEV |
| `main` | `ia-backend-prod` | `casavitacure-crm` | Prod Cloudflare Pages | Supabase PROD |

**THE WORKFLOW:**
1. **ALL new work happens on `desarrollo`** — never commit Sprint work directly to `main`
2. Push triggers auto-deploy to DEV — test and verify there
3. When a block is tested and stable → merge `desarrollo → main` to deploy to production
4. **NEVER push untested code to `main`** — it goes LIVE immediately to real clients

**Before pushing to `desarrollo`:**
- ✅ Code compiles / no syntax errors
- ✅ No hardcoded prod credentials in dev code

**Before merging `desarrollo → main`:**
- ✅ All block tasks marked `[x]` in `task.md`
- ✅ Tested on DEV environment (real WhatsApp messages or simulation)
- ✅ No regressions on existing features
- ✅ User has explicitly approved the merge

### Scope Discipline
- **ONLY** work on the blocks listed in §1 "What Is Being Done RIGHT NOW"
- If you discover a problem outside the current scope: **LOG IT** in the relevant tracking file, do NOT fix it now
- If a "quick fix" tempts you: it's scope creep. Log it. Move on.
- The ONLY exception: if the out-of-scope problem BLOCKS the current task, then fix the minimum needed to unblock and document everything

### Communication
- **DO** explain what you're about to do before doing it
- **DO** show evidence of verification after each change
- **DO** flag uncertainties, risks, or deviations immediately
- **DO NOT** proceed silently through multiple complex steps — check in frequently
- **DO NOT** give "all good" status without evidence

### Git Hygiene
- Commit messages must describe WHAT changed and WHY
- Format: `type(scope): description` (e.g., `fix(llm): migrate to gpt-5.4-mini for deprecated model`)
- One logical change per commit — not a giant "fixed everything" commit
- Never force-push to `main`

---

## 🔒 [IMMUTABLE] §9 — Technology Stack Reference

> Quick reference for the agent. For details, see README.md.

| Layer | Technology | Key Doc |
|:---|:---|:---|
| **Backend** | Python 3.12 + FastAPI | [FastAPI](https://fastapi.tiangolo.com/) |
| **Frontend** | Next.js 15 + React 19 | [Next.js](https://nextjs.org/docs) |
| **Database** | Supabase (PostgreSQL) | [Supabase](https://supabase.com/docs) |
| **LLM (PROD)** | OpenAI `gpt-5.4-mini` | [OpenAI API](https://platform.openai.com/docs/api-reference) |
| **LLM (DEV)** | OpenAI `gpt-5.4-nano` | [OpenAI Models](https://platform.openai.com/docs/models) |
| **Messaging** | WhatsApp Cloud API | [WhatsApp Docs](https://developers.facebook.com/docs/whatsapp/cloud-api) |
| **Hosting** | Google Cloud Run | [Cloud Run](https://cloud.google.com/run/docs) |
| **Frontend Host** | Cloudflare Pages | [Cloudflare](https://developers.cloudflare.com/pages/) |
| **Observability** | Sentry + Discord webhooks | [Sentry Python](https://docs.sentry.io/platforms/python/) |
| **Auth** | Supabase Auth | [Supabase Auth](https://supabase.com/docs/guides/auth) |

### Runtime Environment
| Aspect | Value |
|:---|:---|
| **OS** | Windows |
| **Shell** | **PowerShell** — NOT bash. `&&` does NOT work. Use `;` to chain commands. |
| **Path separator** | `\` (backslash) |
| **No `grep`/`wc`/`sed`** | Use `Select-String`, `Measure-Object`, PowerShell equivalents |
| **Python** | `python` (not `python3`) |
| **Package manager** | `pip` / `npm` |


---

## 🔒 [IMMUTABLE] §9.1 — MCP Tools Available in Environment

> [!IMPORTANT]
> The Antigravity environment has **Model Context Protocol (MCP) servers** connected that provide direct access to infrastructure. These are POWERFUL — use them for diagnostics, queries, and deployments, but NEVER run destructive operations without user approval.

### Available MCP Servers

#### 1. `cloudrun` — Google Cloud Run Management
Access to deploy, inspect, and manage Cloud Run services.

| Tool | Use For |
|:---|:---|
| `list_projects` | See all GCP projects |
| `list_services` | See all Cloud Run services in a project |
| `get_service` | Inspect a specific service (URL, status, config) |
| `get_service_log` | **CRITICAL FOR DEBUGGING** — get logs and errors from a service |
| `deploy_local_folder` | Deploy code to Cloud Run |
| `deploy_container_image` | Deploy a container image |

#### 2. `supabase-mcp-server` — Supabase Database Management
Direct SQL access to BOTH production and development databases.

| Tool | Use For |
|:---|:---|
| `list_projects` | See all Supabase projects (PROD + DEV) |
| `list_tables` | Inspect schema (use `verbose: true` for columns/FKs) |
| `execute_sql` | Run SELECT queries for diagnostics |
| `apply_migration` | Run DDL changes (CREATE TABLE, ALTER, etc.) |
| `get_logs` | Get service logs (api, postgres, auth, edge-function, etc.) |
| `get_advisors` | Check for security/performance issues |
| `list_migrations` | See migration history |

### ⚠️ CRITICAL: Production vs Development

> [!CAUTION]
> There are TWO Supabase projects. **ALWAYS confirm which one you're targeting before running ANY query.**

| Environment | Purpose | Safety Level |
|:---|:---|:---|
| **PRODUCTION** | Live client data (CasaVitaCure + future tenants) | 🔴 **READ-ONLY unless explicitly approved** |
| **DEVELOPMENT** | Testing, experimentation, safe to modify | 🟢 Free to query and modify |

### MCP Safety Rules
1. **NEVER** run `DELETE`, `DROP`, `TRUNCATE`, or `UPDATE` on production without explicit user approval
2. **ALWAYS** use `list_projects` first to identify the correct project ID — do NOT guess
3. **ALWAYS** use `list_tables` with `verbose: true` before writing migrations — verify the current schema
4. **Prefer `execute_sql`** for diagnostics (SELECT queries) — it's safe and fast
5. **Use `apply_migration`** (not `execute_sql`) for DDL operations — it creates a proper migration record
6. **Use `get_service_log`** as the FIRST debugging step when Cloud Run issues are suspected
7. **Run `get_advisors`** after any DDL changes to catch missing RLS policies or security issues

---

## 🔒 [IMMUTABLE] §10 — Emergency Procedures


### If Production Is Down
1. Check Cloud Run logs FIRST: `gcloud run services logs read ia-backend --region=us-central1`
2. Check Sentry for the latest error
3. Check Discord for automated alerts
4. If the issue is in the latest deploy: **ROLLBACK** using the previous Cloud Run revision
5. Notify user IMMEDIATELY

### If LLM Returns Garbage
1. Check which model is actually being called (log the model string)
2. Check the system prompt being sent (log the first 200 chars)
3. Check the message history format (role: user/assistant/tool, correct tool_call_ids)
4. Check for `strict: true` schema violations in tool calls
5. Check `max_completion_tokens` cap — is the response being truncated?

### If WhatsApp Stops Receiving Messages
1. Check Meta webhook subscription is active
2. Check webhook verification token matches
3. Check the Cloud Run service is responding to health checks
4. Check Meta App status (not in Development Mode when it should be Live)
5. Check rate limits on the Meta side

---

> **END OF SESSION PROMPT**  
> **To use:** Copy this file. Fill in `✏️ [MODIFIABLE]` sections. Paste into new Antigravity session.  
> **To update rules:** Only modify `🔒 [IMMUTABLE]` sections with full team consensus and version the change.
