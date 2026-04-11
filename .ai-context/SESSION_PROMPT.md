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
SESSION GOAL:    Deploy Block A quick wins IMMEDIATELY for instant prod improvement, then execute Blocks B-H
SESSION BLOCKS:  A, B, C, D, E, F, G, H
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

### What Is Being Done RIGHT NOW (This Session)
**Block A — Quick Wins (30 min) → DEPLOY IMMEDIATELY:**
- A1: Change `gpt-4o-mini` → `gpt-5.4-mini` in 3 files
- A2: Remove `.lower()` in `use_cases.py:L64`
- A3: Disable BUG-5 (comment `TOOL_ACTION_PATTERNS` L219-L242)
- A4: Increase history limit 20→30
- A5: Graph API v19.0→v25.0
- A6: Add `max_completion_tokens=500`
- A7: DEPLOY to production
- A8: Live test via WhatsApp

**Block B — `strict: true` tool schemas (1 hr)**
**Block C — OpenAI adapter enhancement (30 min)**
**Block D — Agentic loop rewrite (3-5 hrs) ⭐ MOST CRITICAL**
**Block E — Resilience layer: webhook sig, rate limit, lock TTL, shadow-forward, health, cache (90 min)**
**Block F — Observability: correlation IDs + Sentry tags (30 min)**
**Block G — DB: `bsuid` column + index (15 min)**
**Block H — Test & deploy Day 1 (30 min)**

### What Comes Next (After This Session)
- Day 2 (Sun): Blocks I (system prompt engineering 3-4h), J (escalation UX), K (provisioning script), L (status page)
- Day 3 (Mon): Blocks M (fumigation tenant setup), N (E2E testing), O (Meta audit)
- Day 4 (Tue): Blocks P (go-live 🚀), Q (post-onboarding)
- Sprint 2: Dashboard MVP, Instagram DM, multi-squad booking, gpt-5.4-nano testing

### Known Blockers & Risks
- ⚠️ `META_APP_SECRET` env var needed for Block E1 (webhook signature verification) — must be retrieved from Meta App Dashboard → Settings → Basic
- ⚠️ Block D (agentic loop) is the highest-risk block — 3-5 hours estimated, involves rewriting the core message processing flow
- ⚠️ CasaVitaCure client is experiencing poor AI responses RIGHT NOW — Block A deployment provides immediate relief
- ⚠️ Graph API v19.0 deprecation deadline: May 21, 2026 (40 days)

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

### Active Bugs & Critical Corrections
| ID | Issue | Status | Fix Location |
|:---|:---|:---|:---|
| BUG-5 | Silent Failure Detector 95%+ false positives | 🟡 → Disable | Block A3: comment L219-L242 `use_cases.py` |
| BUG-6 | Response quality unacceptable in production | 🔴 7 Root Causes | Blocks A-D: model, tools, adapter, agentic loop |
| CC-1 | Codebase uses deprecated `gpt-4o-mini` | 🔴 | Block A1: 3 files |
| CC-3 | BSUID migration needed for contact lookups | 🔴 | Block G1: add column + index |
| CC-4 | Graph API v19.0 deprecated May 21, 2026 | 🔴 | Block A5: `meta_graph_api.py:L8` |
| CC-5 | Tool schemas missing `strict: true` | 🔴 | Block B1: all 7 tools |
| CC-7 | No webhook signature verification | 🔴 SECURITY | Block E1: HMAC-SHA256 |
| CC-8 | No LLM rate limit per contact | 🔴 COST | Block E2: 20/hour max |
| CC-9 | `is_processing_llm` lock has no TTL | 🔴 SILENCES | Block E3: 90s TTL |
| CC-10 | No health monitoring | 🟡 | Block E5: UptimeRobot |
| CC-11 | No conversation shadow-forward | 🟡 | Block E4: to admin phone |
| CC-12 | Tenant config fetched every request | 🟡 | Block E6: 3-min cache |

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

## 🔒 [IMMUTABLE] §6 — The No-Assumptions Testing Rule

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

## 🔒 [IMMUTABLE] §7 — Progress & Documentation Preservation Rules

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
> **Pushes to branches trigger AUTOMATIC deployments.** Understand this before pushing ANYTHING.

```
desarrollo (dev branch)  ──push──►  Cloud Run: DEV backend    +  Cloudflare: DEV frontend
main       (prod branch) ──push──►  Cloud Run: PROD backend   +  Cloudflare: PROD frontend
```

| Branch | Backend Deploy Target | Frontend Deploy Target | Database |
|:---|:---|:---|:---|
| `desarrollo` | `ia-backend-dev` (Cloud Run, `saas-javiera`) | Dev Cloudflare Pages | Supabase DEV |
| `main` | `ia-backend` (Cloud Run, `casavitacure-crm`) | Prod Cloudflare Pages | Supabase PROD |

**THE WORKFLOW:**
1. **ALL new work happens on `desarrollo`** — never commit Sprint work directly to `main`
2. Test and verify on DEV environment
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
