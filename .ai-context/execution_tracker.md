# AI CRM — Execution Tracker (April 11 → May 4, 2026)

> **Master Plan:** [Master Plan v3](file:///C:/Users/tomas/.gemini/antigravity/brain/2ae8123c-0df3-4743-86ba-b85da6306f81/master_plan.md)  
> **Deep Dives:** [A](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) | [B](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md) | [C](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md)  
> **Last Updated:** 2026-04-11 14:30 CLT

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
- [ ] Fix INC-1: Unlock contact via MCP SQL on PROD
- [ ] Fix INC-2: Apply `updated_at` migration to PROD via MCP
- [ ] Fix INC-3: Add retry/finally to `_unset_processing()` in `use_cases.py`
- [ ] Fix INC-4: Update `last_message_at` in orchestrator pipeline
- [ ] Fix INC-5: Add retry to lock release
- [ ] Verify: Send real WhatsApp message, confirm response received
- [ ] Add new SESSION_PROMPT rule: Migration Parity Rule (DEV+PROD always)
- [ ] Commit + deploy to `desarrollo`, test, then merge to `main`

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

##### Phase 1: Root Cause Investigation (DO THIS FIRST — no code changes)

**Track 1: History Loading** — Is the LLM receiving the full conversation history?
- [ ] Read `use_cases.py` — trace EXACTLY what gets passed in the `messages` array to OpenAI
- [ ] Check: How many messages are loaded? Is there a `.limit()` truncation?
- [ ] Check: Are `human_agent` role messages included in history? (relates to BUG-E)
- [ ] Check: Is history ordered correctly (chronological)?
- [ ] Check: Does the system prompt get prepended correctly?
- [ ] Add temporary logging to echo the EXACT messages array sent to OpenAI (for one test message)

**Track 2: OpenAI API Contract** — Are we calling the API correctly for gpt-5.4-mini?
- [ ] Search OpenAI docs for `gpt-5.4-mini` — message format, system prompt format, tool_calls protocol
- [ ] Search OpenAI docs for `max_completion_tokens` behavior — does 500 tokens cause the broken record?
- [ ] Compare our `openai_adapter.py` against the official Chat Completions API reference
- [ ] Check: Are we sending `role: "system"` or embedding it differently?
- [ ] Check: `temperature`, `top_p`, or other params that could cause repetitive output
- [ ] Check: Is `parallel_tool_calls=False` causing issues with this model?

**Track 3: Tool Execution** — Did `book_round_robin` and `get_merged_availability` actually fire?
- [ ] Pull Cloud Run logs for contact 83dc2480 between 00:41-00:47 CLT April 12
- [ ] Search for `[TOOL]` or tool execution log lines during that window
- [ ] If tools DID fire: check return values — did the bot receive confirmation?
- [ ] If tools DID NOT fire: this confirms BUG-1/BUG-D — the bot is claiming actions without executing tools

**Track 4: System Prompt Analysis** — Does the prompt structure cause LLM misbehavior?
- [ ] Read the full system prompt (PROD) + `INTERNAL_TOOL_RULES` concatenation
- [ ] Check: Is the prompt so prescriptive that the LLM memorizes template outputs instead of conversing?
- [ ] Check: Does "Ejemplo de estructura obligatoria" in Phase 2 cause verbatim parroting?
- [ ] Cross-reference with OpenAI best practices for system prompts (web search required)
- [ ] Evaluate: The "broken record" response IS the Phase 2 template — "nombre y apellido y día y hora"

**Track 5: Message Dedup & Lock Behavior** — Why double responses?
- [ ] Check: Is there a webhook deduplication mechanism? (Meta sometimes sends same webhook twice)
- [ ] Check: `message_id` from Meta — are we storing it? Using it for dedup?
- [ ] Check: Can two pipeline runs overlap if the lock isn't set fast enough?
- [ ] Check: Do `human_agent` messages from the dashboard come through the webhook path?

**Synthesis:**
- [ ] After all 5 tracks are investigated, write a root cause summary for each of the 7 bugs
- [ ] Classify each root cause: prompt issue / code issue / API issue / infrastructure issue
- [ ] Propose specific fixes with evidence from the investigation
- [ ] Present to user for approval before implementing

##### Phase 2: Implement Fixes (ONLY after Phase 1 is complete and approved)

- [ ] Fix each confirmed root cause (specific steps TBD from diagnosis)
- [ ] Test on DEV via sandbox simulation
- [ ] Verify each fix against the specific BUG it addresses
- [ ] Deploy to PROD following Migration Parity Rule
- [ ] Run Post-Migration Health Check
- [ ] Send real WhatsApp test message to verify behavior



### Day 3: Sunday April 13 — Context + Dashboard + Escalation

#### Step 6: Enriched Patient Context (30 min)
- [ ] `use_cases.py:185` — Build richer context block
  - Include: contact name, phone, role, created_at, notes, tags
  - Later: appointments, purchase history (Sprint 2)
  
#### Step 7: Increase History Limit (5 min)
- [ ] `use_cases.py:148` — Change `.limit(20)` to `.limit(30)`

#### Step 8: Dashboard MVP — Blocks 1-2 (3-4 hours)
> **Reference:** [Deep Dive C](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md)

- [ ] Create `GET /api/dashboard/status` endpoint in `main.py`
  - Query: messages today count, pending escalations count, system status
- [ ] Create `GET /api/dashboard/activity` endpoint in `main.py`
  - Query: today's messages with contact names, reverse chronological
- [ ] Rewrite `DashboardView.tsx` — Replace ALL mock data
  - Block 1: StatusBlock (green/red status, counts)
  - Block 2: ActivityFeed (today's timeline)
  - Remove: fake charts, fake KPIs, placeholder data
- [ ] Test dashboard with real CasaVitaCure data

#### Step 9: Escalation UX Minimum (2 hours)
- [ ] In `ContactList.tsx`: Add visual indicator for contacts where `bot_active=false`
  - Red dot or "⚠️ Escalado" badge next to contact name
- [ ] In `ChatArea.tsx`: Add "Resolver y reactivar bot" button
  - On click: `UPDATE contacts SET bot_active = true WHERE id = X`
  - Show confirmation toast
- [ ] Filter/tab: "Pendientes" to show only escalated contacts

#### Step 10: Deploy Day 3 (30 min)
- [ ] Commit + push both backend + frontend
- [ ] Verify both deploys succeed
- [ ] Test escalation flow end-to-end

### Day 4: Monday April 14 — Fumigation Tenant Setup

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

- [ ] **S2.1:** Implement real Gemini adapter (cost optimization / fallback)
  - File: `Backend/app/infrastructure/llm_providers/gemini_adapter.py`
  - Use `google-genai` SDK with function calling support
  - Map Gemini's tool format to our LLMResponse DTO
  - Prerequisite: Set up Gemini API billing + key

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
