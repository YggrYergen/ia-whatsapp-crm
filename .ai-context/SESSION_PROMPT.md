# 🚀 AI WhatsApp CRM — Session Prompt

> **Usage:** Copy this prompt into each new Antigravity session. Update ONLY the `[MODIFIABLE]` sections.  
> **IMMUTABLE sections** (`🔒`) must NEVER be altered — they contain operational rules that prevent catastrophic errors.  
> **MODIFIABLE sections** (`✏️`) must be updated before every session to reflect current state.  
> **Last structural update:** 2026-04-11

---

## ✏️ [MODIFIABLE] §0 — Session Identity

```
SESSION DATE:    2026-04-21
CURRENT SPRINT:  Sprint 2 (Product Expansion)
CURRENT DAY:     Day 10 — Media Handling + Documentation Sync
SESSION GOAL:    Implement WhatsApp media pipeline (image/document/audio) + sync 7 stale .ai-context/ files
SESSION BLOCKS:  Media Handling (DB + Storage + Backend + Frontend) + Doc Sync
LAST COMMIT:     ca93ddb (main) — fix: move /config into (panel) layout for superadmin tenant switching
```

---

## ✏️ [MODIFIABLE] §1 — Big Picture: Where We Are

> Update this section before every session. It is the agent's primary situational awareness.

### What This Project Is
AI WhatsApp CRM SaaS — a multi-tenant platform where businesses get an AI assistant on WhatsApp that handles customer conversations, books appointments, escalates to humans, and tracks customer intelligence. Currently live with **2 clients**: CasaVitaCure (wellness center) and Control Pest (fumigation). Goal: 7 paying clients by May 4.

### What Has Been Done (Completed)
- ✅ Full backend (FastAPI) + frontend (Next.js 15) deployed to Cloud Run + Cloudflare Workers
- ✅ WhatsApp Cloud API integration (send/receive, webhooks, per-tenant HMAC verification)
- ✅ OpenAI LLM integration: **Responses API** (migrated from Chat Completions Apr 18) with 7 tools
- ✅ Adaptive reasoning: no reasoning for greetings, low effort for conversation
- ✅ Pre-tool-call ACK messages ("Dejame revisar...")
- ✅ Staff WhatsApp send from CRM with 24h window handling
- ✅ Supabase multi-tenant database (tenants, contacts, messages, bookings)
- ✅ Native calendar engine: resources, appointments, scheduling_config, round-robin booking
- ✅ Service-aware booking with service selector + 30-min slot agenda grid
- ✅ Self-service onboarding: 3-step wizard (Welcome → ConfigChat → Completion)
- ✅ Sandbox chat: dedicated `/api/sandbox/chat` endpoint, Responses API
- ✅ Cinematic login: Vortex particles + CLI text + glassmorphic card
- ✅ Sentry + Discord observability (correlation IDs, structured logging)
- ✅ Dev/prod environment separation (independent Cloud Run + Supabase instances)
- ✅ Security: per-tenant HMAC, superadmin RLS INSERT/UPDATE policies, service_role bypass
- ✅ Mobile UX: bottom bar, viewport, logout, dead button wiring (6 commits Apr 19)
- ✅ Control Pest fully provisioned: prompt, services, resources, scheduling_config, HMAC
- ✅ Dead Google Calendar code removed (commit `88c06d4`)
- ✅ `/config` page migrated into `(panel)` layout for TenantContext superadmin switching

### What Is Being Done RIGHT NOW (This Session)

**WhatsApp Media Handling Pipeline (Apr 21)**

Control Pest clients will send payment receipts (images, documents). The current pipeline drops all non-text messages silently. Implementation plan created:

1. **Zero-latency media detection** — extract `message.type` synchronously from webhook
2. **Metadata persistence** — `message_type` + `media_metadata` JSONB columns on `messages`
3. **LLM context injection** — descriptive text ("[El usuario envio una imagen]") instead of binary
4. **Fire-and-forget background** — download from Meta + upload to Supabase Storage async
5. **Frontend MediaBubble** — render images, documents, audio in ChatArea

**Also:** Syncing 7 stale `.ai-context/` files (last updated Apr 16, 6 days behind).

### What Comes Next (After Media Handling)
- 14-step E2E test execution (7 tools + cross-tenant isolation)
- Instagram DM integration (SELLING POINT)
- Dashboard MVP with real charts/KPIs
- Multi-squad booking engine

### Known Blockers & Risks
- ⚠️ Media handling plan awaiting user approval on 3 open questions
- ⚠️ E2E test suite not yet executed
- 🟢 WhatsApp webhook pipeline stable for text messages
- 🟢 Both tenants (CasaVitaCure + Control Pest) operational
- 🟡 wamid extraction null — dedup falls back to atomic lock (working)

---

## ✏️ [MODIFIABLE] §2 — Key Decisions & Context

> Record ALL significant decisions that have been made. An agent that doesn't know about a decision WILL contradict it.

| Decision | Choice | Date | Rationale |
|:---|:---|:---|:---|
| Production LLM model | `gpt-5.4-mini` ($0.75/$4.50/1M) | 2026-04-11 | Best tool calling + agentic performance |
| Dev/budget LLM model | `gpt-5.4-nano` ($0.20/$1.25/1M) | 2026-04-11 | For simple tenants or dev testing |
| Cost cap | `max_completion_tokens=2048` per response | 2026-04-12 | Raised from 500 (truncation caused doom loops) |
| PROD region | `us-central1` (was `europe-west1`) | 2026-04-11 | All dependencies in US. Europe added 600-1000ms |
| WhatsApp pipeline | **Responses API** (`openai_responses_adapter.py`) | **2026-04-18** | **Migrated from Chat Completions. Enables reasoning.effort + tools.** |
| Adaptive reasoning | No reasoning for greetings, low for conversation | 2026-04-18 | Sub-2s greeting responses |
| Staff WhatsApp | CRM staff can send messages via WhatsApp | 2026-04-18 | 24h window handling for Meta compliance |
| Per-tenant HMAC | `meta_app_secret` column on tenants | 2026-04-21 | Dynamic HMAC lookup per webhook, replaces single shared secret |
| Config page location | Inside `(panel)` layout | 2026-04-21 | Required for TenantContext superadmin switching |
| GCal removal | Dead code removed entirely | 2026-04-21 | All tenants use native calendar, GCal SA credentials unnecessary |
| Media handling | Zero-latency fire-and-forget pipeline | 2026-04-21 | Sync type detection, async download/upload, descriptive text for LLM |
| Shadow-forwarding | BOTH user + bot messages forwarded to admin | 2026-04-11 | Full interaction visibility |
| BSUID implementation | Dormant capture (Phase 1) | 2026-04-11 | Phase 2 (lookup swap) before June 2026 |
| Sandbox isolation | Dedicated `/api/sandbox/chat` via Responses API | 2026-04-15 | Zero shared state with WhatsApp webhook |
| Rapid-fire batching | Re-fetch history after 3s sleep | 2026-04-12 | 80/20 fix |

### Active Bugs & Critical Corrections
| ID | Issue | Status | Fix Location |
|:---|:---|:---|:---|
| MEDIA-1 | WhatsApp media messages silently dropped | Plan ready | `ProcessMessageUseCase` line 96 |
| U-7 | wamid extraction null | Low priority | Dedup fallback working |
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

| Branch | Backend Service | Region | Frontend | Database |
|:---|:---|:---|:---|:---|
| `desarrollo` | `ia-backend-dev` | `us-central1` | Dev Cloudflare Pages | Supabase DEV |
| `main` | `ia-backend-prod` | `us-central1` | Prod Cloudflare Pages | Supabase PROD |

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

### 🔴 Migration Parity Rule — NON-NEGOTIABLE

> [!CAUTION]
> **On April 12, 2026, a migration applied ONLY to DEV caused a production outage.** The `updated_at` column was never applied to PROD. The 90-second lock TTL safety mechanism was completely dead in production — contacts were permanently silenced with zero recovery. Full incident report: [`.ai-context/incident_report_apr12.md`](file:///d:/WebDev/IA/.ai-context/incident_report_apr12.md)

**The Rule:** Every database migration, schema change, or DDL operation (columns, indexes, triggers, functions, RLS policies, ALTER TABLE) follows a **gated lifecycle**. No migration is ever "complete" until PROD is verified.

**The Gated Lifecycle:**

```
 1. Write the migration SQL
 2. Apply to DEV (project: nzsksjczswndjjbctasu) — iterate freely here
 3. Test on DEV (simulation, manual test, sandbox)
 4. Mark in execution_tracker.md:
    └─ "DEV ✅ | PROD ⏳ PENDING APPROVAL"
 5. ── GATE: User explicitly approves promotion to PROD ──
 6. Apply IDENTICAL SQL to PROD (project: nemrjlimrnrusodivtoa)
 7. Verify on PROD (run schema verification query — see below)
 8. Mark in execution_tracker.md:
    └─ "DEV ✅ | PROD ✅ VERIFIED"
```

**If the migration is experimental or potentially harmful:**
- Stay at step 4
- Mark: `"PROD ❌ NOT YET — REASON: [explain why it's unsafe for prod, e.g., 'destructive ALTER on live data', 'depends on code not yet deployed', 'testing edge cases first']"`
- Only promote after user explicitly says "send it to PROD"
- NEVER mark the task as complete while PROD is pending

**Verification Query (run after EVERY migration on target env):**
```sql
-- Verify column exists
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = '<TABLE>' AND column_name = '<COLUMN>';

-- Verify index exists
SELECT indexname, indexdef FROM pg_indexes
WHERE tablename = '<TABLE>' AND indexname LIKE '%<INDEX_NAME>%';
```

**Report BOTH verification results (DEV + PROD) in your response.**

**Pre-Merge Drift Check (before every `desarrollo → main` merge):**
- Query `information_schema.columns` on BOTH DEV and PROD for all tables touched in the sprint
- If ANY column/index/trigger exists on DEV but not PROD → the merge is BLOCKED until the migration is applied or explicitly deferred with reason

**Sprint 2 (planned):** Automate this with a GitHub Action that runs `supabase db dump --schema-only` on both projects and diffs them on every PR to `main`.

**Sprint 3 (planned):** Add a proper staging environment (3rd Supabase project) that mirrors PROD exactly, so migrations can be tested against production-like data before promotion.

### 🔴 Post-Migration Health Check

**After every migration applied to PROD:**
1. Run the verification query above — confirm the change exists
2. Check Sentry for new errors in the next 5 minutes
3. Check Discord alerts channel for any new alerts
4. If the migration added a column used by existing code (e.g., `updated_at` for lock TTL), send ONE real test message through WhatsApp to confirm the code path executes without error
5. If any check fails → immediately document in execution_tracker and alert the user

**This is NOT optional.** The April 12 incident was invisible for 12+ hours because no health check was performed after the blocks were deployed.

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
| **Frontend Host** | Cloudflare Workers (OpenNext) | [Cloudflare](https://developers.cloudflare.com/workers/) |
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
1. Check Cloud Run logs FIRST: `gcloud run services logs read ia-backend-prod --region=us-central1 --project=saas-javiera`
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
