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

### Day 2: Saturday April 12 — BUG-6 Core Fix (Response Quality)

> **Primary reference:** [Deep Dive A](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md)

#### Step 1: Quick Wins (30 min)
- [ ] **RC-4 Fix:** `openai_adapter.py` — Always capture `message.content`, not just when no tool_calls
  - File: `Backend/app/infrastructure/llm_providers/openai_adapter.py:58-66`
  - Change: `dto.content = message.content or ""` BEFORE the if/else
- [ ] **RC-3 Fix:** `use_cases.py:64` — Remove `.lower()`, store original text
  - Change: `raw_text_body = message.get("text", {}).get("body", "")`
  - Only lowercase for keyword detection on L106-107
- [ ] **RC-7 Fix:** `use_cases.py:219-242` — Comment out BUG-5 silent failure detector
  - Add comment: `# DISABLED: 95%+ false positive rate. See BUG-5 in README.`

#### Step 2: LLMResponse DTO Update (15 min)
- [ ] `router.py:8-12` — Add `prompt_tokens`, `completion_tokens`, `total_tokens`, `model` fields
- [ ] `openai_adapter.py` — Capture `response.usage` and `response.model` into DTO

#### Step 3: Agentic Loop Rewrite — THE BIG ONE (3-5 hours)
- [ ] `use_cases.py` — Replace L245-L325 with proper agentic loop
  - Implement `MAX_TOOL_ROUNDS = 5` loop
  - Append `role: "assistant"` message with `tool_calls` array to history
  - For each tool result, append `role: "tool"` with `tool_call_id`
  - Pass `tools=tools_schema` on EVERY iteration (not `tools=None`)
  - Track `tool_choice_override` only on first round
  - Add safety: if max rounds exceeded, generate fallback message
  - Remove old error injection logic (L286-L323)

#### Step 4: Test with Simulation Suite (1-2 hours)
- [ ] Run simulation scenarios from `Backend/scripts/simulation/`
- [ ] Test multi-step conversation: "check availability" → "book the 3pm slot"
- [ ] Test name preservation: "Soy María García" → verify NOT lowercased in DB
- [ ] Verify tool results display naturally in responses
- [ ] Check Sentry for errors during testing

#### Step 5: Deploy to Production (30 min)
- [ ] `git commit` with descriptive message
- [ ] Push to `main` → auto-deploy via Cloud Build
- [ ] Verify revision is active: `gcloud run services describe ia-backend-prod`
- [ ] Test with real WhatsApp message to CasaVitaCure number
- [ ] Monitor Sentry for 15 minutes

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
