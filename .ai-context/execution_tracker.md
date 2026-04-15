# AI CRM — Execution Tracker (April 11 → May 4, 2026)

> **Master Plan:** [Master Plan v3](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/master_plan.md)  
> **Deep Dives:** [A](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) | [B](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md) | [C](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md)  
> **Last Updated:** 2026-04-12 23:03 CLT

---

## Sprint 1: Emergency Stabilization (Apr 11-15) — TUESDAY DEADLINE

### Day 1: Friday April 11 — Research & Planning

- [x] Complete deep research: OpenAI function calling best practices
- [x] Complete deep research: Meta WhatsApp compliance & phone provisioning
- [x] Complete deep research: Multi-channel messaging APIs (Instagram, Messenger)
- [x] Complete deep research: LLM model pricing (gpt-5-mini vs Gemini Flash-Lite)
- [x] Complete deep research: SaaS billing models (credits system, EBITDA multiplier)
- [x] Complete deep research: Correlation ID / distributed tracing architecture
- [x] Complete deep research: Meta Tech Provider enrollment process
- [x] Create Deep Dive A: Response Quality Architecture (.ai-context/)
- [x] Create Deep Dive B: Multi-Channel Messaging Architecture (.ai-context/)
- [x] Create Deep Dive C: Dashboard UX Information Architecture (.ai-context/)
- [x] Create Master Plan v3 (artifact)
- [x] Create execution tracker (artifact + .ai-context/)
- [ ] Update README.md with current state, new architecture decisions, backlog
- [ ] Update .ai-context/implementation_plan.md with new phases
- [ ] Update .ai-context/task.md with Sprint 1-3 tasks

### Day 1 (Evening): Saturday April 11 — Block H Completion & PROD Stabilization

> **Session 2** (ea1aa81e) — 22:30-23:15 CLT

#### Block H: Test & Deploy Day 1 ✅ COMPLETE
- [x] H1: 9/9 simulation scenarios passed (zero errors)
- [x] H2: Strict mode validated via H1 scenarios
- [x] H3: Fast-forward merge `desarrollo → main`, deployed to PROD
- [x] H4: Live E2E test — **CRITICAL BUGS FOUND AND FIXED:**

**Bug 1: HMAC Webhook 401 (Critical)**
- Real WhatsApp webhooks → 401 Unauthorized after deploy
- Root cause: Google Secret Manager stores `META_APP_SECRET` with trailing `\r\n` (34 chars vs 32)
- HMAC-SHA256 computed with wrong key → signature mismatch
- Diagnosis: temporary debug logging revealed `secret_len=34`
- Fix: `.strip()` on secret before HMAC computation (`security.py:67`)
- Verified: DEV (200 OK), then PROD (all webhooks 200 OK)

**Bug 2: Cloud Build Trigger Override**
- `ia-calendar-bot@saas-javiera.iam.gserviceaccount.com` has Cloud Build trigger on `main`
- Our manual `gcloud run deploy` was overridden by trigger deploying OLD code from previous push
- Lesson: ALWAYS `git push origin main` FIRST, then Cloud Build auto-deploys

**Optimization: PROD Region Migration**
- Moved `ia-backend-prod` from `europe-west1` → `us-central1`
- Reason: all dependencies (Supabase us-east-2, OpenAI, Meta) are US-based
- Europe added 600-1000ms per request (5-8 cross-Atlantic DB calls per message)
- New PROD URL: `https://ia-backend-prod-645489345350.us-central1.run.app`
- Meta webhook URL updated, UptimeRobot updated

**Optimization: Model Config**
- Tenant was using deprecated `gpt-4o` instead of `gpt-5.4-mini`
- Updated in PROD database → dramatic latency improvement
- Combined with region move = near-instant responses

**Commits:** `fec49c7` → `0d93f94` → `030ef94` (all synced main↔desarrollo)

### Day 2: Saturday April 12 — INCIDENT RESPONSE + System Prompts

#### 🔴 Block 0 (EMERGENCY): Production Incident Fix — April 12 00:47 CLT

> **Full incident report:** [`.ai-context/incident_report_apr12.md`](file:///d:/WebDev/IA/.ai-context/incident_report_apr12.md)
> **Forensic artifact:** [BSUID forensic (Antigravity brain)](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/incident_report_apr12.md)

**Summary:** Cloud Run instance network death at 00:47 CLT caused a cascade of ConnectTimeout + StreamReset errors. The processing lock on contact `83dc2480` (phone 56931374341, "Rapida Media Co.") was never released because `_unset_processing()` also failed. Contact is STILL permanently locked — all real WhatsApp messages are silently dropped. Sandbox works because it bypasses the lock check (`is_simulation=True`).

**Root cause of permanence:** Block E3's `updated_at` column migration was applied to DEV but NOT PROD. The 90-second TTL safety net has **never worked in production.** The code reads `contact_data.get("updated_at")` → always `None` → treats every lock as "fresh" → silently drops every subsequent message.

**5 issues discovered:**

| ID | Issue | Severity | Fix |
|:---|:---|:---|:---|
| **INC-1** | Contact 83dc2480 permanently locked (`is_processing_llm=true`) | 🔴 CRITICAL | `UPDATE contacts SET is_processing_llm = false WHERE id = '83dc2480-...'` |
| **INC-2** | `updated_at` column + trigger missing from PROD contacts | 🔴 CRITICAL | Run E3 migration on PROD: `ALTER TABLE contacts ADD COLUMN updated_at...` + trigger |
| **INC-3** | No recovery mechanism for network-death cascade | 🟡 ARCH | Lock release needs retry + finally pattern |
| **INC-4** | `last_message_at` not being updated by orchestrator | 🟡 BUG | Should update on every processed message |
| **INC-5** | Lock release (`_unset_processing`) has no retry | 🟡 RESILIENCE | Add 1 retry with backoff |

**Checklist:**
- [x] Fix INC-1: Unlock contact via MCP SQL on PROD — `is_processing_llm` set to false (verified)
- [x] Fix INC-2: Apply `updated_at` migration to PROD via MCP — column + trigger verified on PROD
- [x] Fix INC-3: Lock release moved to `finally` block — always runs even on crash
- [x] Fix INC-4: `last_message_at` now updated on every inbound message
- [x] Fix INC-5: Lock release has 1 retry + 2s backoff + Sentry/Discord alerts
- [ ] Verify: Send real WhatsApp message, confirm response received ← **WAITING FOR PROD DEPLOY (~3min)**
- [x] Add SESSION_PROMPT rule: Migration Parity Rule already in §8 (added in previous session)
- [x] Commit `3c9d9ed` → pushed to `desarrollo` + merged to `main` (fast-forward)

**Migration Parity Status:**
| Migration | DEV | PROD |
|:---|:---|:---|
| `updated_at` column on contacts | ✅ | ✅ VERIFIED |  
| `contacts_updated_at_trigger` | ✅ | ✅ VERIFIED |
| Schema drift check (13 columns) | ✅ | ✅ PASS |

#### Block I: Assistant Response Quality — DIAGNOSTIC FIRST, THEN FIX

> ⚠️ **DO NOT IMPLEMENT ANY FIXES UNTIL THE FULL DIAGNOSIS IN PHASE 1 IS COMPLETE.**
> We know WHAT is broken (7 bugs). We do NOT know WHY. Premature fixes risk masking the real root cause.
> 
> **Conversation diagnostic:** [`.ai-context/conversation_diagnostic_apr12.md`](file:///d:/WebDev/IA/.ai-context/conversation_diagnostic_apr12.md)
> **Deep Dive A (prior analysis):** [`.ai-context/deep_dive_a_response_quality.md`](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md)

**7 bugs identified from PROD conversation analysis:**

| Bug | Summary | Severity |
|:---|:---|:---|
| **BUG-A** | Broken record loop — bot gives identical response 6+ times ignoring conversation | 🔴 CRITICAL |
| **BUG-B** | Phase 1 skip — triaje questions bypassed, jumps straight to scheduling | 🔴 CRITICAL |
| **BUG-C** | Context hallucination — bot references "piernas" user never mentioned | 🔴 HIGH |
| **BUG-D** | "Confirmed" without tool call — says booking is done but may not have called `book_round_robin` | 🔴 HIGH |
| **BUG-E** | Human agent message triggers bot response (should be ignored by bot) | 🟡 MEDIUM |
| **BUG-F** | Double response — bot responds twice to same message ~37s apart | 🟡 MEDIUM |
| **BUG-G** | Owner conversation skips phases with fabricated context | 🔴 HIGH |

##### Phase 1: Root Cause Investigation ✅ COMPLETE

**All 5 tracks investigated. 7 root causes identified and documented.**

| Bug | Root Cause | Classification | Fix |
|:---|:---|:---|:---|
| BUG-A | `max_completion_tokens=500` truncates responses; "obligatoria" template parroting | API + Prompt | ✅ Step 1: 500→2048 + penalties |
| BUG-B | No phase enforcement in prompt; LLM freely skips Phase 1 | Prompt design | ⏳ Step 3: prompt rewrite |
| BUG-C | Template contains "piernas" → hallucinated patient context | Prompt design | ⏳ Step 3: prompt rewrite |
| BUG-D | Template responses bypass tool calling + truncation corrupts tool JSON | API + Prompt | ✅ Step 1: finish_reason + circuit breaker |
| BUG-E | `human_agent` mapped to `role:"assistant"` — LLM confused own identity | Code bug | ✅ Step 2: role:"user" + name:"agente_humano" |
| BUG-F | No webhook dedup (wamid not stored) + atomic lock race condition | Code gap | ⏳ Step 4: wamid + RPC lock |
| BUG-G | Same root as BUG-B + BUG-C combined | Prompt design | ⏳ Step 3: prompt rewrite |

**Critical blind spots caught by second-agent review:**
1. 🔴 human_agent Option A (skip) would BREAK escalation — fixed with Option C (role:"user")
2. 🔴 max_completion_tokens truncates tool_calls JSON too — raised to 2048 + circuit breaker
3. 🔴 wamid column migration MUST happen before code deployment

##### Phase 2: Fix Implementation

**Step 1: openai_adapter.py ✅ DEPLOYED TO PROD** (commit `8808a28`)
- [x] max_completion_tokens: 500 → 2048
- [x] frequency_penalty: 0.3, presence_penalty: 0.3
- [x] finish_reason checked → was_truncated flag in LLMResponse DTO
- [x] Sentry + Discord instrumentation on truncation events

**Step 2: use_cases.py ✅ DEPLOYED TO PROD** (commit `8808a28`)
- [x] human_agent → role:"user" + name:"agente_humano" (NOT skip)
- [x] Removed [(Log): timestamp] prefix from user messages
- [x] Truncation circuit breaker: if was_truncated + has_tool_calls → discard + fallback

**Step 3: System prompt rewrite ✅ V2 APPLIED TO PROD**
- [x] Draft new prompt v2 delivered → reviewed, 3 fixes incorporated
- [x] Applied to PROD tenant `CasaVitaCure` in Supabase `system_prompt` column
- [x] Fixes: phase gate ⛔, anti-parroting, generic triaje, admin/staff bypass, anti-repetition
- [ ] Fine-tune pacing: model dumps all questions at once → needs `reasoning_effort` (Step 5)

**Step 4: Webhook dedup + atomic lock ✅ DEPLOYED TO PROD** (commit `614d1c1`)
- [x] `acquire_processing_lock` RPC (DEV ✅ | PROD ✅ VERIFIED)
- [x] `wamid TEXT` column + `idx_messages_wamid_unique` partial index (DEV ✅ | PROD ✅ VERIFIED)
- [x] Code: extract wamid from payload, store in insert, catch UNIQUE violation → skip
- [x] Code: `_set_processing()` → `_acquire_lock_atomic()` via RPC
- [x] Code: Stale lock force-release before atomic acquire
- [x] Sentry + Discord instrumentation on all failure paths
- [x] Pre-merge drift check: PASS (messages.note DEV-only, pre-existing, unused)

**Step 5: reasoning_effort experiment ✅ REMOVED → Sprint 2**
- [x] Diagnosed: OpenAI hard-rejects `reasoning_effort` + `tools` on `/v1/chat/completions` for gpt-5.4-mini
- [x] Error: "Function tools with reasoning_effort are not supported. Please use /v1/responses instead."
- [x] Impact: every request was doubling (fail→retry) + spamming Discord (7+ alerts per test)
- [x] Fix: removed entire experiment (commit `627c93e`). Zero quality impact — param never worked with tools
- [x] Sprint 2: ~~Migrate adapter to Responses API~~ → **PULLED FORWARD to Block R2.1 (2026-04-14)**: New `openai_responses_adapter.py` built side-by-side for onboarding agent. Existing adapter untouched.
- [ ] Full diagnostic: [reasoning_effort_diagnostic.md](file:///d:/WebDev/IA/.ai-context/deep_dives_&_misc/reasoning_effort_diagnostic.md)

**Step 5b: Rapid-fire message batching ✅ MERGED TO PROD** (commit `1f7b250` → merged `73789ef`)
- [x] Diagnosed: messages 2+ in rapid-fire sequences were persisted to DB but silently dropped from LLM context
- [x] Fix: re-fetch history AFTER 3s sleep to capture accumulated messages
- [x] Full observability: Sentry context + Discord alert on failure
- [x] Graceful degradation: falls back to pre-sleep history on re-fetch failure
- [x] Merged to main + auto-deployed to PROD (2026-04-12 19:00 CLT)

**Step 6: Infrastructure fixes ✅ COMPLETED** (2026-04-12 ~18:50 CLT)
- [x] Fixed `messages.note` schema drift — added column to PROD (`apply_migration`)
- [x] Fixed trigger name drift — renamed PROD `contacts_updated_at_trigger` → `trg_contacts_updated_at`
- [x] Fixed Cloud Build PROD trigger — was deploying to deleted europe-west1 service, now targets us-central1
- [x] Pre-merge drift check: PASS (all columns, indexes, triggers match)
- [x] Merged `desarrollo` → `main` (commit `73789ef`, 7 files, 365 insertions)
- [x] Cloud Build auto-deploy: ✅ SUCCESS (build `98de7410`, revision `ia-backend-prod-00003-z77`)
- [x] Cloudflare Workers auto-deploy: ✅ triggered
- [x] PROD health check: 200 OK
- [x] User confirmed: assistant answers much better, webhook working

**Schema Drift: ZERO ✅**
| Item | DEV | PROD | Status |
|:---|:---|:---|:---|
| messages.note | ✅ | ✅ | ✅ FIXED |
| trigger name | `trg_contacts_updated_at` | `trg_contacts_updated_at` | ✅ FIXED |
| All contacts cols (13) | ✅ | ✅ | ✅ MATCH |
| All messages cols (7) | ✅ | ✅ | ✅ MATCH |

#### Day 2 Unsolved Issues — Carried Forward (2026-04-12 ~18:30 CLT)

> **Last updated:** 2026-04-12 22:10 CLT  
> Most issues resolved during Apr 12 frontend session. See `task_v2.md` for authoritative status.

**🔴 RESOLVED**

| # | Issue | Resolution | Status |
|:---|:---|:---|:---|
| U-1 | **Mobile frontend BROKEN** | Multiple fix passes: pb-sidebar, responsive grids, dark glassmorphic design, compact navbar (68→60px), header clearance, double padding fix. | ✅ |
| U-2 | **Escalation UX missing** | Full Block J: badge, resolve button, filter tabs, sorting, pulse, sidebar badge, NotificationFeed | ✅ |
| U-3 | **PROD calendar UNVERIFIED** | Confirmed working — multiple successful bookings over 5+ hours | ✅ |
| U-4 | **Dashboard fake data** | Full Block L: live alerts, INTERVENCIÓN MANUAL, alert history, time range filter, glassmorphic design | ✅ |
| U-6 | **Rapid-fire fix NOT on PROD** | Merged `73789ef` to main. Cloud Build auto-deployed. | ✅ |
| U-15 | **Hardcoded europe URL × 5** | 5 frontend files fixed. Hotfix on main `c5d7b06`. | ✅ |
| U-16 | **contacts.notes column missing** | Added column to DEV + PROD via migration. | ✅ |

**⏳ STILL OPEN**

| # | Issue | Status |
|:---|:---|:---|
| U-5 | **Fumigation prompt** | Template drafted. Blocked on client data. | ⏳ |
| U-7 | **wamid extraction null** | Low priority. Fallback (atomic lock) works. | 🟡 |
| U-8 | **Prompt Phase 1 skip** | Prompt v2 deployed, testing ongoing. | ⏳ |
| U-14 | **Booking flow repetition loop** | Fix deployed, testing ongoing. | ⏳ |

### Day 2 (Evening) / Day 3 (Early Morning): Apr 12-13 — Frontend Overhaul + Mobile Stabilization

> **Session** (2ae8123c) — Multiple passes, Apr 12 evening CLT

#### Block J: Escalation UX ✅ COMPLETE
- [x] **J1.** Visual badge on ContactList for `bot_active=false` contacts
- [x] **J2.** "Resolver y reactivar bot" button in ChatArea + ProfilePanel
- [x] **J3.** Filter/tab: "Todos/Pendientes/Activos" with count badges
- [x] **J4.** Sorted: escalated first, then by last_message_at
- [x] **J5.** Gentle 3s pulse animation (not stroboscopic)
- [x] **J6.** Sidebar escalation count badge
- [x] **J7.** NotificationFeed: type-specific icons, navigate-to-chat

#### Block L: Dashboard + Frontend Overhaul ✅ COMPLETE
- [x] **L1.** Live alerts from Supabase with realtime subscription
- [x] **L2.** INTERVENCIÓN MANUAL section (live escalations)
- [x] **L3.** Alert history with filter tabs (Pendientes/Todas/Resueltas)
- [x] **L4.** Navigate-to-chat from dashboard alerts
- [x] **L5.** Resolve / Dismiss buttons per alert
- [x] **L6.** Type badges: escalation, cita, cancelación, reagendada
- [x] **L7.** Dark glassmorphic design language across Dashboard, Agenda, CRM
- [x] **L8.** Compact responsive stats grid with time range filter (1h/6h/today/week/month/year)
- [x] **L9.** PacientesView with patient profile sheet, lead scoring, editable notes, call button

#### Mobile Frontend Stabilization ✅ COMPLETE (Multiple Passes)

**Pass 1: Layout + Spacing**
- [x] Fix chat layout for mobile viewport (`pb-sidebar`, input clearing)
- [x] Fix dashboard layout for mobile (responsive grids, `pb-24`)
- [x] Slide-in animation for profile panel on mobile

**Pass 2: Critical UX Bugs**
- [x] NotificationFeed not closable — root cause: rendered inside `pointer-events-none` container. Moved to sibling.
- [x] CRM status label truncation — simplified to single-word labels (Nuevo/Activo/Reciente/Inactivo)
- [x] GlobalFeedbackButton overlapping chat controls — hidden on mobile (`hidden md:flex`)

**Pass 3: Chat Sandbox + Spacing**
- [x] TestChatArea redesigned: compact layout, DESCARTAR/ENVIAR/CAMBIAR ROL/CONFIG. buttons
- [x] Role switcher added (Client ↔ Staff ↔ Admin) with DB integration
- [x] Header height reduced (72→52px TestChat, 72→56px ChatArea) to clear mobile browser chrome
- [x] Double bottom padding eliminated (layout `pb-sidebar` was doubling with component padding)
- [x] Navbar reduced 68→60px

**Bug Fixes (discovered during frontend work):**
- [x] **U-15:** 5 hardcoded europe-west1 URLs → us-central1. Hotfix on main `c5d7b06`.
- [x] **U-16:** `contacts.notes` column missing in DEV + PROD. Migration applied both envs.

**Commits:** Multiple on `desarrollo` branch. Build verified (0 errors).

#### Session 3 Close-Out (Apr 12 ~23:00 CLT)

- [x] README.md rewrite — 1581→508 lines (Project README + Operational Runbook + Roadmap)
- [x] All `.ai-context/` docs synchronized (master_plan, implementation_plan, execution_tracker)
- [x] `reasoning_effort_diagnostic.md` persisted to `deep_dives_&_misc/`
- [x] Pre-merge drift check: 6 tables compared, **✅ PASS** (tenant_users +role/+created_at on DEV only — safe)
- [x] Merge `desarrollo` → `main` — commit `6ee6cd8`, pushed. Auto-deploy triggered.
- [ ] Test on actual phone browser (PROD now deployed)
- [ ] **U-69:** Read OpenAI docs on tool execution patterns for gpt-5.4-mini

#### Deferred to Monday
- [ ] **Step 6:** Enriched Patient Context — deferred for proper design (interconnected: LLM context ↔ PacientesView ↔ staff actions)

### Day 4: Monday April 14 — Newcomer Onboarding System + Fumigation Tenant Setup

#### Block R: Newcomer Onboarding System 🔧 IN STABILIZATION

> **Session:** 13d7385c (2026-04-15)  
> **Commit:** `2c5d2a5` — SSE parser root cause fix  
> **Last updated:** 2026-04-15 11:30 CLT

##### R1–R3: Core Implementation ✅ COMPLETE

All backend, DB, and frontend components built:
- [x] `onboarding_messages` Supabase table (DEV ✅ | PROD ⏳ PENDING APPROVAL)
- [x] `openai_responses_adapter.py` — new Responses API adapter (reasoning + tools + streaming)
- [x] `chat_endpoint.py` — full config-agent SSE endpoint (10-field wizard, follow-up loop, finalization)
- [x] `useOnboardingStream.ts` — SSE consumer hook with persistence, history load, progress tracking
- [x] `ConfigChat.tsx` — streaming chat UI with dedup rendering
- [x] `CompletionStep.tsx` — confetti/fireworks celebration (CSS keyframes in globals.css)
- [x] `OnboardingWizard.tsx` — multi-step wizard (Welcome → Chat → Completion)

##### Block R: Bugs Fixed (April 15 session)

| Fix | Commit | Description |
|:---|:---|:---|
| Build: CSS scoping | `f7d705a` | Moved keyframes from styled-jsx to globals.css; flattened multiline classNames |
| Rendering: DEDUP arch | `f7d705a` | Eliminated flushSync; streaming bubble hides when content matches last message |
| Multi-turn: isStreaming | `f7d705a` | Moved setIsStreaming(false) to outer finally — no longer kills follow-up bubbles |
| **SSE Parser: ROOT CAUSE** | `2c5d2a5` | `currentEventType/Data` declared inside while loop → reset on every read() call → events split across TCP chunks were silently dropped. Moved before loop. |

##### Block R: Remaining Known Issues (Post-Fix)

| ID | Issue | Priority | Status |
|:---|:---|:---|:---|
| **R-1** | WelcomeStep (Step 1) not seen — user goes straight to ConfigChat | High | ⏳ To investigate |
| **R-2** | Confetti/fireworks at completion not firing | Medium | ⏳ CompletionStep CSS paths to verify |
| **R-3** | After completion, user sent to `/chats` (empty for newcomers) | High | ⏳ Needs sandbox route |
| **R-4** | Sandbox "Chat de Pruebas" requires DB contact row to display | Critical | ⏳ Architecture change needed |
| **R-5** | `onboarding_messages` migration not applied to PROD | Critical | PENDING APPROVAL |
| **R-6** | Phone number not collected during onboarding (11th field) | Medium | Backlog |

##### Block R: Architecture Decision — Sandbox Route (APPROVED DIRECTION)

> Option A chosen: dedicated `/chats/sandbox` standalone route, no contacts table dependency.
> Self-contained, always available for newcomers, powered by tenant's `system_prompt`.
> CompletionStep CTA → `router.push('/chats/sandbox')` instead of `/chats`.

#### Step 11: WhatsApp Number Setup (1 hour)
- [ ] Buy SIM card (if not done)
- [ ] Register number in Meta Business Manager → your WABA
- [ ] Configure display name: "[Fumigation Business Name]"
- [ ] Verify number receives webhook
- [ ] Note the `phone_number_id` for tenant config

#### Step 12: Supabase Tenant Setup (1 hour)
- [ ] Insert new tenant in `tenants` table
  ```sql
  INSERT INTO tenants (name, ws_phone_id, ws_token, llm_provider, llm_model, system_prompt, is_active)
  VALUES ('FumigacionXYZ', 'PHONE_ID_HERE', 'SYSTEM_USER_TOKEN', 'openai', 'gpt-5-mini', '[SYSTEM_PROMPT]', true);
  ```
- [ ] Create admin user in Supabase Auth
- [ ] Insert user-tenant mapping
- [ ] Test login with new credentials on `dash.tuasistentevirtual.cl`

#### Step 13: System Prompt for Fumigation (2 hours)
- [ ] Get from owner: services list, pricing, service areas, squad names, FAQ
- [ ] Write comprehensive system prompt covering:
  - Business identity and tone
  - Services catalog with descriptions
  - Common questions and answers
  - Booking flow instructions
  - Escalation triggers
  - Working hours and coverage areas
- [ ] Test prompt with simulation mode
- [ ] Iterate based on owner feedback

#### Step 14: Usage Tracking Foundation (2 hours)
- [ ] Create `usage_logs` table migration:
  ```sql
  CREATE TABLE usage_logs (
      id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id uuid REFERENCES tenants(id),
      correlation_id text,
      action_type text NOT NULL,
      model text,
      prompt_tokens integer,
      completion_tokens integer,
      credits_consumed numeric(10,2),
      cost_usd numeric(10,6),
      metadata jsonb DEFAULT '{}',
      created_at timestamptz DEFAULT now()
  );
  CREATE INDEX idx_usage_logs_tenant ON usage_logs(tenant_id);
  CREATE INDEX idx_usage_logs_created ON usage_logs(created_at);
  ```
- [ ] Add usage logging to `use_cases.py` after each LLM call
- [ ] Add `correlation_id` generation at pipeline start

#### Step 15: Full E2E Test (2 hours)
- [ ] Send test messages to fumigation WhatsApp number
- [ ] Verify responses are natural and accurate
- [ ] Test appointment booking
- [ ] Test escalation flow
- [ ] Verify dashboard shows new tenant data
- [ ] Fix any bugs found

#### Step 16: Deploy Final for Tuesday (30 min)
- [ ] Final commit + push
- [ ] Verify both backend + frontend deployed
- [ ] Smoke test both tenants (CVC + fumigation)
- [ ] Prepare onboarding notes for tomorrow

### Day 5: Tuesday April 15 — Client Onboarding

- [ ] **Morning:** Walk fumigation owner through dashboard
- [ ] **Morning:** Show conversation management, how to read chats
- [ ] **Morning:** Explain escalation (when human needs to intervene)
- [ ] **Morning:** Test with owner — have them message the WhatsApp number
- [ ] **All day:** Monitor Sentry + Discord for any errors
- [ ] **As needed:** Hotfix any issues discovered during onboarding
- [ ] **End of day:** Check CasaVitaCure is still working properly (regression test)

---

## Sprint 2: Product Expansion (Apr 16-25)

### Week 1 (Apr 16-20)

- [ ] **S2.1:** Gemini 3.1 Flash-Lite adapter (primary model candidate)
  - File: `Backend/app/infrastructure/llm_providers/gemini_adapter.py`
  - Use `google-genai` SDK with function calling + Pydantic schema support
  - Map Gemini's tool format to our LLMResponse DTO
  - Model: `gemini-3.1-flash-lite` — $0.25/M in, $1.50/M out (3x cheaper than gpt-5.4-mini)
  - 1M token context window, 2.5x faster TTFT than predecessor
  - Native thinking capabilities (`thinking_config` param)
  - Our architecture already supports dual providers (`llm_provider` column)
  - Test plan: A/B test one tenant on Gemini, one on OpenAI
  - Prerequisite: Set up Google AI Studio API key + billing

- [ ] **S2.1b:** Config UI enhancements for tenant management
  - Prompt versioning: save/swap/compare multiple prompts per tenant
  - Cache invalidation endpoint: `POST /api/admin/invalidate-cache` → instant prompt apply
  - Wire config UI to call invalidation after saving changes
  - Model selection dropdown: allow switching models from config tab
  - Ref: `dependencies.py:31` — `invalidate_tenant_cache()` already exists, just needs an endpoint

- [ ] **S2.2:** Multi-channel DB schema migration
  - Add `channel` column to `messages` table (default 'whatsapp')
  - Add `primary_channel` to `contacts` table
  - Create `contact_channel_ids` table
  - Create `tenant_channels` table
  - Ref: [Deep Dive B §3.2](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md)

- [ ] **S2.3:** Instagram DM integration
  - Configure Instagram webhook in Meta App Dashboard
  - Create NormalizedMessage dataclass
  - Create InstagramAdapter (webhook → NormalizedMessage)
  - Create InstagramSendAPI
  - Update ProcessMessageUseCase for channel-awareness
  - Update ContactList UI with channel icons
  - Test with fumigation client's Instagram Business account
  - Ref: [Deep Dive B §4](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md)

### Week 2 (Apr 21-25)

- [ ] **S2.4:** Multi-squad booking engine
  - Create `tenant_resources` table (squads/practitioners/rooms)
  - Create `resource_schedules` table (availability windows)
  - Create `bookings` table
  - Update/create booking tools: `check_availability`, `book_appointment`
  - Update Agenda view to show bookings from DB (not just Google Calendar)
  - Optional: Google Calendar sync (push bookings to GCal for visibility)

- [ ] **S2.5:** Credits/billing system
  - Create `tenant_plans` table
  - Create `consume_credits()` Postgres function
  - Wire usage_logs → credit consumption in use_cases.py
  - Add credit display to dashboard (Block 4)
  - Add overage alerts (Discord + dashboard)

- [ ] **S2.6:** Dashboard Blocks 3-4
  - Block 3: Opportunities (inactive clients 30+ days, hot leads)
  - Block 4: Performance (credits, model info, response metrics)
  - Ref: [Deep Dive C §4](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md)

- [ ] **S2.7:** Daily briefing generation
  - New LLM tool: `generate_daily_briefing`
  - Queries: today's appointments, conversations summary, pending items
  - Triggers: admin sends "resumen del día" or scheduled via cron

- [ ] **S2.8:** Staff comments on AI responses
  - Add `staff_comment` column to `messages` table
  - Add comment button next to each AI message in ChatArea
  - Staff comments visible only to admin/staff (not sent to client)
  - Flag system: "incorrect response" → triggers review workflow

- [ ] **S2.9:** SuperAdmin panel v1
  - New route: `/superadmin` (gated by hardcoded user list)
  - All-tenants overview table
  - Per-tenant cost tracking (from usage_logs)
  - System health overview
  - Correlation ID search

---

## Sprint 3: Scale to 7 (Apr 26 → May 4)

- [ ] **S3.1:** Meta App Review submission
  - Create demo video showing WhatsApp integration
  - Submit for `whatsapp_business_management` + `whatsapp_business_messaging`
  - Register as Tech Provider

- [ ] **S3.2:** Facebook Messenger integration
  - Reuse Instagram adapter (90% shared code)
  - Test with fumigation client's Facebook Page

- [ ] **S3.3:** Customer Intelligence v1
  - Enriched contact profiles: visits, purchases, interests
  - "30 days no contact" detection + alert
  - Contact detail panel improvements

- [ ] **S3.4:** FinOps dashboard in SuperAdmin
  - Revenue per tenant (manual input for now)
  - Cost per tenant (from usage_logs)
  - Margin calculation
  - Trend charts

- [ ] **S3.5:** Client acquisition + onboarding (tenants 3-7)
  - Outreach per go-to-market strategy
  - Onboard each client (~1h per client)
  - Monitor system stability

- [ ] **S3.6:** Notification system
  - In-app bell icon for admins
  - Notification types: escalation, error, daily summary ready
  - Real-time via Supabase Realtime

- [ ] **S3.7:** Sandbox environment for tenants
  - Simulation mode accessible from dashboard
  - Changes to system prompt don't affect live until "publish"
  - A/B testing foundation

---

## Critical References

| Resource | URL | Why |
|:---|:---|:---|
| **OpenAI Function Calling** | https://platform.openai.com/docs/guides/function-calling | Correct tool message format |
| **Meta WhatsApp Cloud API** | https://developers.facebook.com/docs/whatsapp/cloud-api/ | Webhook + messaging |
| **Meta Business Verification** | https://www.facebook.com/business/help/2058515294227817 | Required for Tech Provider |
| **Instagram Messaging API** | https://developers.facebook.com/docs/instagram-messaging/ | Instagram DM integration |
| **Supabase Pricing** | https://supabase.com/pricing | Plan limits monitoring |
| **Cloud Run Pricing** | https://cloud.google.com/run/pricing | Cost tracking |
| **Sentry FastAPI** | https://docs.sentry.io/platforms/python/integrations/fastapi/ | Error monitoring |
