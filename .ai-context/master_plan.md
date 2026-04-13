# 🗺️ Master Plan v6 — AI WhatsApp CRM SaaS (ALL DECISIONS FINALIZED)

> **Documento vivo** — Última actualización: 2026-04-13 01:50 CLT  
> **Estado:** APPROVED v7 — Sprint 1 Blocks A-L COMPLETE, Blocks M-Q pending. All CC items resolved.  
> **Deep Dives:** [A v3 (Response Quality)](file:///d:/WebDev/IA/.ai-context/deep_dive_a_response_quality.md) | [B v3 (Multi-Channel)](file:///d:/WebDev/IA/.ai-context/deep_dive_b_multi_channel.md) | [C v3 (Dashboard + Observability)](file:///d:/WebDev/IA/.ai-context/deep_dive_c_dashboard_ux.md)

> [!CAUTION]
> **MODEL DECISION FINALIZED (v6):** Production model = **`gpt-5.4-mini`** ($0.75/$4.50/1M). Dev/budget = **`gpt-5.4-nano`** ($0.20/$1.25/1M). Cost cap: `max_completion_tokens=500` → ~$0.00225/response max. Margins: **88-90%** with cap. Codebase must be updated from `gpt-4o-mini` (DEPRECATED).

### 🔴 Critical Research Findings (New in v4)
| # | Finding | Impact | Source |
|:---|:---|:---|:---|
| **1** | WhatsApp service conversations are **FREE** since July 2025 | Cost model drops from ~20K to ~8-12K CLP/tenant | Meta pricing update |
| **2** | **BSUID migration** starting NOW (April 2026) | Must add `bsuid` column to contacts table immediately | Meta Graph API changelog |
| **3** | OpenAI `strict: true` on tools = **guaranteed** schema compliance | Add to ALL tool definitions — eliminates argument hallucination | OpenAI Structured Outputs docs |
| **4** | Prompt caching is **AUTOMATIC** (50% input savings) | System prompt must be first + stable + ≥1024 tokens | OpenAI prompt caching docs |
| **5** | gpt-5.4-mini **400K context window** | Room for much richer conversation history | OpenAI model specs |
| **6** | Portfolio-based messaging limits (Oct 2025) | New numbers **inherit** existing limits — no warm-up | Meta WABA docs |
| **7** | Instagram: 200 msg/hr rate limit, NO templates | Cannot re-engage after 24h (unlike WhatsApp) | Meta Instagram API docs |
| **8** | Graph API at **v25.0**, v19.0 deprecated May 21 | Audit all API version strings in codebase | Meta changelog |
| **9** | `asgi-correlation-id` library | Simplifies correlation ID middleware for Sentry | Python middleware ecosystem |
| **10** | Meta App Review: separate videos per permission | Critical for Sprint 3 Tech Provider enrollment | Meta docs + community |
| **11** | 🔴 **Codebase uses DEPRECATED `gpt-4o-mini`** | Must change model string in 3 files before deploy | Code audit April 11 |
| **12** | `gpt-5.4-nano` ($0.20/$1.25) exists | Budget option for simple tasks — 95% margin possible | OpenAI pricing page |

---

## 0. Business Context & Hard Deadlines

| Milestone | Date | Days Left | Status |
|:---|:---|:---|:---|
| **2nd Client Onboarding** (Fumigation) | Tue 2026-04-15 | **2 días** | 🟡 Template ready, needs client data |
| **7 Paying Clients** | 2026-05-04 | **21 días** | Kill switch |
| **Financial Independence** | 2026-07 | ~82 días | Legal entity + positive cash flow |

### Key Business Decisions Made

| Decision | Choice | Rationale |
|:---|:---|:---|
| **Default LLM** | ✅ **`gpt-5.4-mini`** PROD + `gpt-5.4-nano` DEV/budget | Both API-compatible. Cap: `max_completion_tokens=500`. Margins: 88-90%. |
| **Booking engine** | **Own DB-based** + optional GCal sync | Multi-industry scalability, no GCal dependency |
| **WhatsApp provisioning** | Your WABA short-term → Client-owned WABA before #7 | Meta compliance risk (see §1) |
| **Pricing** | 80K CLP/mo basic | 10K under market leader |
| **Target margin** | 80%+ per tenant | Industry standard, wiggle room for market shifts |

---

## 1. 🔴 Meta Compliance Architecture

> [!CAUTION]
> Running multiple unrelated businesses under ONE WABA is against Meta policy. Each client must eventually own their own WABA.

### Current Reality (Functional But Risky)
- You buy SIM cards, run under YOUR Meta Business account
- One flagged number could take down ALL clients
- For Tuesday: **Option B (your WABA)** — only realistic path

### Migration Path to Compliance (Before Tenant #7)

| Phase | Action | Timeline | Effort |
|:---|:---|:---|:---|
| **Now** | Register new number under your WABA for fumigation client | Today | 1h |
| **Sprint 3** | Submit Meta App for App Review (Tech Provider permissions) | Week 4 | 2h prep |
| **Sprint 4** | Implement Embedded Signup flow in our dashboard | Week 5-6 | 8-12h |
| **Before #7** | Migrate existing clients to their own WABAs | Week 6-7 | 2h/client |

### Tech Provider Enrollment Requirements
1. ✅ Verified Meta Business Portfolio (you have this)
2. ⬜ App Review with `whatsapp_business_management` + `whatsapp_business_messaging`
3. ⬜ Embedded Signup implementation (JS SDK in our frontend)
4. ⬜ Demo video for App Review submission

### What Changes Architecturally
```
CURRENT:
  Your Meta Account → WABA → Phone 1 (CVC) + Phone 2 (Fumig)

COMPLIANT (FUTURE):
  Client Meta Account → Client WABA → Client Phone
  Your Meta App → Tech Provider access via Embedded Signup
  Your Backend → Uses client's WABA ID + Phone ID + Token
```

**DB Change:** The `tenants` table already has `ws_phone_id` and `ws_token` per tenant. For the BSP model, we'll also need:
- `waba_id` — WhatsApp Business Account ID
- `meta_business_id` — Client's Meta Business Portfolio ID
- Both returned from Embedded Signup flow

---

## 2. Financial Model v2

### Revenue

| Item | Value |
|:---|:---|
| Basic plan | **80,000 CLP/mo** (~$80 USD) |
| Setup fee | Variable (survival mode until 7th tenant) |
| Target margin | **80%+** |

### ✅ MODEL DECISION — FINALIZED (2026-04-11)

| Model String | Status | Input $/1M | Output $/1M | Context | Quality |
|:---|:---|:---|:---|:---|:---|
| `gpt-4o-mini` | ⛔ **DEPRECATED** | $0.15 | $0.60 | 128K | Legacy — current code default |
| `gpt-5.4-nano` | ✅ Active | $0.20 | $1.25 | — | Classification, simple tasks |
| **`gpt-5.4-mini`** | ✅ **Active (Recommended)** | **$0.75** | **$4.50** | **400K** | Best tool calling, agentic |  

**Source:** [OpenAI Pricing](https://openai.com/api/pricing/) | [Models](https://platform.openai.com/docs/models)

### Cost Per Tenant — 3 SCENARIOS (CORRECTED v5)

**Scenario A: `gpt-5.4-mini` ($0.75/$4.50) — Maximum Quality**

| Service | Cost/Tenant/Mo | Notes |
|:---|:---|:---|
| **OpenAI API** | ~12,000-18,000 CLP | $0.75 input, $4.50 output. 20-40 convos/day. ~50% input cached. |
| **WhatsApp API** | **~0-500 CLP** 🟢 | [Service FREE](https://developers.facebook.com/docs/whatsapp/pricing). Templates only outside 24h. |
| **Supabase** | $0 → $3.57/tenant Pro | Stay free until tenant #3. |
| **Cloud Run** | ~$0-2 | Free tier covers 7 tenants |
| **Cloudflare / Sentry** | $0 | Free tiers |
| **TOTAL** | **~14,000-20,000 CLP** | |

**Scenario B: `gpt-5.4-nano` ($0.20/$1.25) — Maximum Margin**

| Service | Cost/Tenant/Mo | Notes |
|:---|:---|:---|
| **OpenAI API** | ~3,000-5,000 CLP | Cheapest active model. Quality TBD. |
| **Everything else** | ~500-2,000 CLP | Same as above |
| **TOTAL** | **~4,000-7,000 CLP** | |

### Margin Analysis (CORRECTED v5)

| Tenants | Revenue | Scenario A (5.4-mini) | Margin | Scenario B (5.4-nano) | Margin |
|:---|:---|:---|:---|:---|:---|
| 1 | 80K | ~50K | 38% | ~40K | 50% |
| 3 | 240K | ~80K | 67% | ~48K | 80% |
| 5 | 400K | ~115K | 71% | ~55K | 86% |
| **7** | **560K** | **~150K** | **73%** | **~65K** | **88%** |
| 10 | 800K | ~210K | 74% | ~80K | 90% |
| 15 | 1.2M | ~305K | 75% | ~105K | 91% |

> [!IMPORTANT]
> **v6 update:** With `max_completion_tokens=500`, cost per response capped at ~$0.00225.
> At $4.50/1M output × 500 tokens = $0.00225/response. ≈ $5-8/tenant/mo → **88-90% margins.**
> Decision: `gpt-5.4-mini` for production (quality + nuance), `gpt-5.4-nano` for dev/budget tenants.
> Both API-compatible: same endpoint, same tool format, same `strict: true`. Change = 1 string.
> At 15 tenants with 5.4-mini + cap: ~700K CLP/mo profit (~$700 USD). Comfortable.

### Cost Optimization Levers (Research-Validated)
1. **Prompt caching** (AUTOMATIC) — 50% input savings if system prompt stable + first + ≥1024 tokens. Monitor via `cached_tokens` field.
2. **`strict: true` on tools** — Eliminates retry costs from malformed arguments
3. **Gemini 3.1 Flash-Lite** as alternative — 25% cheaper output ($1.50 vs $2.00)
4. **History summarization** — After 25 messages, summarize older turns (Sprint 2)
5. **Observation masking** — Replace verbose tool outputs with summaries before next LLM call

---

## 3. Credit-Based Billing System

### Hybrid Model (Platform Fee + Credits)

```
Plan Básico:    80K CLP/mo  → 5,000 credits included
Plan Pro:      150K CLP/mo  → 15,000 credits included
Plan Enterprise: Custom     → Unlimited credits
```

### Credit Costs

| Action | Credits | Real Cost |
|:---|:---|:---|
| 1 LLM inference (gpt-5.4-mini, ~1K tokens) | 1 credit | ~3-8 CLP |
| 1 tool execution | 0.5 credits | ~0 CLP |
| 1 outbound WhatsApp template (utility) | 5 credits | ~15-20 CLP |
| 1 outbound WhatsApp template (marketing) | 10 credits | ~30-50 CLP |

### Database Schema → See `usage_logs` table design in Deep Dive A §3

---

## 4. Second Client: Fumigation Business

### Client Profile
- **Business:** Fumigation services, Santiago Metropolitana
- **Scale:** Multiple squads, 15-40 conversations/day
- **Channels:** WhatsApp (now), Instagram (Sprint 2), Messenger (Sprint 3)
- **Owner:** Has personal WhatsApp number, willing to transfer

### Tuesday Deliverable (Realistic MVP)

| Feature | Status | Notes |
|:---|:---|:---|
| ✅ WhatsApp AI assistant | After BUG-6 fix | Must understand fumigation services |
| ✅ Basic appointment booking | Existing system | Single calendar, manual squad assignment initially |
| ✅ Dashboard access | After MVP de-mocking | Blocks 1-2 with real data |
| ✅ Conversation management | Existing | View/respond to chats |
| ⚠️ Squad scheduling | MVP workaround | Book appointments with squad name in notes field |
| ⚠️ Daily briefing | MVP manual | Admin can ask the bot directly "dame el resumen del día" |
| ❌ Instagram | Sprint 2 | Not ready in 4 days |
| ❌ Payments | Sprint 2-3 | Major integration needed |
| ❌ Product catalog | Sprint 2 | Need DB + tools |

> [!IMPORTANT]
> **Tuesday Scope: "WhatsApp MVP that works well."** The fumigation client gets a working AI assistant on WhatsApp that handles conversations, books appointments, and escalates when needed. Advanced features (Instagram, payments, squad logistics, daily briefings) come in Week 2-3. **You need to set this expectation with the client.**

### Multi-Squad Architecture → See Master Plan v2 §4 (Bookings Engine DB schema)

---

## 5. Observability: Correlation ID System

### Architecture

```python
# Every inbound request gets a correlation_id
# Format: "cr_{12_hex_chars}" → compact, grep-friendly
correlation_id = f"cr_{uuid.uuid4().hex[:12]}"

# Propagated to:
# - Every log line: logger.info(f"[{correlation_id}] message")
# - Every Sentry event: sentry_sdk.set_tag("correlation_id", cid)
# - Every Discord alert: included in embed
# - Every usage_log record: metadata.correlation_id
# - Every tool execution context
```

### What Gets Correlation IDs
- Inbound webhook processing (WhatsApp, Instagram, etc.)
- LLM inference calls
- Tool executions
- Outbound messages
- Database operations

### SuperAdmin Lookup
When an error occurs:
1. Discord alert shows `correlation_id`
2. Search Sentry by `correlation_id` tag → see all events from that execution
3. Search `usage_logs` by `correlation_id` → see cost of that interaction
4. Search `messages` for the contact → see conversation context

---

## 6. Architecture Roadmap

### Current State
```
WhatsApp → Cloud Run (FastAPI) → OpenAI → Supabase → Response → WhatsApp
                                           ↕
                                     Google Calendar (hardcoded CVC)
```

### Target State (May 2026)
```
┌─ Channels ─────────┐     ┌── Backend ──────────┐     ┌── LLM ─────────┐
│ WhatsApp            │     │ Channel Router       │     │ gpt-5.4-mini     │
│ Instagram           │ ──► │ CorrelationMiddleware│ ──► │ (future: gemini│
│ Messenger           │     │ ProcessMessage       │     │  anthropic)    │
│ Email               │     │ Agentic Tool Loop    │     └────────────────┘
└─────────────────────┘     │ Usage Tracker        │            ↕
                            │ Booking Engine       │     ┌── Tools ───────┐
┌─ Frontend ─────────┐     └──────────────────────┘     │ check_avail    │
│ Dashboard           │            ↕                     │ book_appointment│
│ Conversations       │     ┌── Database ─────────┐     │ escalate_human │
│ Agenda              │     │ tenants              │     │ update_scoring │
│ Config              │     │ contacts (multi-ch)  │     │ ...per-tenant  │
│ SuperAdmin          │     │ messages (channel)   │     └────────────────┘
│ Reportes            │     │ bookings             │
└─────────────────────┘     │ usage_logs           │
                            │ tenant_plans         │
                            └──────────────────────┘
```

---

## 7. Sprint Breakdown (April 11 → May 4)

### Sprint 1: Emergency Stabilization (Apr 11-15) — REVISED v2

> **See full execution plan:** [task.md §Sprint 1](file:///d:/WebDev/IA/.ai-context/task.md) (Blocks A-Q, 17 blocks, 4 days)
> **Authoritative status:** [task_v2.md](file:///d:/WebDev/IA/.ai-context/task_v2.md)
> **Key change (v2):** Dashboard MVP → Sprint 2. Time → system prompts + resilience layer.

| Day | Tasks | Status |
|:---|:---|:---|
| **Fri Apr 11** | Research DONE ✅ (50+ searches). Deep dives v3 + all docs enriched. Model decided. Sprint 1 restructured. | ✅ Done |
| **Sat Apr 12** | Block A-H: strict tools, agentic loop, resilience, observability, BSUID, deploy. Block I: response quality fix (5 steps). Block J: escalation UX. Block L: dashboard + mobile frontend overhaul. | ✅ Done |
| **Sun Apr 13** | Step 6: Enriched patient context. Merge `desarrollo` → `main` (needs drift check). | ⏳ In progress |
| **Mon Apr 14** | Fumigation tenant setup via provisioning script, full E2E testing, Meta audit. | ⏳ Pending |
| **Tue Apr 15** | Onboarding 🚀, monitoring, post-onboarding (prompt refinement + rescue template). | ⏳ Pending |

### Sprint 2: Product Expansion (Apr 16-25)

| # | Task | Sprint Day | Hours |
|:---|:---|:---|:---|
| S2.1 | Gemini adapter implementation (cost optimization) | Day 1-2 | 4h |
| S2.2 | Multi-channel DB schema + abstraction layer | Day 2-3 | 4h |
| S2.3 | Instagram DM integration | Day 3-5 | 8h |
| S2.4 | Multi-squad booking engine (DB + tools) | Day 5-7 | 8h |
| S2.5 | Credits/billing system (usage_logs + tenant_plans) | Day 7-8 | 6h |
| S2.6 | Dashboard Blocks 3-4 (Opportunities + Performance) | Day 8-9 | 6h |
| S2.7 | Daily briefing generation tool | Day 9 | 4h |
| S2.8 | Staff comments on AI responses | Day 9-10 | 4h |
| S2.9 | SuperAdmin panel v1 | Day 10 | 6h |

### Sprint 3: Scale to 7 (Apr 26 → May 4)

| # | Task | Hours |
|:---|:---|:---|
| S3.1 | Meta App Review submission (Tech Provider) | 2h |
| S3.2 | Facebook Messenger integration | 4h |
| S3.3 | Customer Intelligence v1 (enriched profiles) | 6h |
| S3.4 | FinOps dashboard (cost vs revenue per tenant) | 4h |
| S3.5 | Onboard tenants 3-7 (1h each + outreach) | ~15h |
| S3.6 | Notification system (in-app) | 4h |
| S3.7 | Sandbox testing environment (config preview) | 4h |

---

## 8. Execution Handoff Protocol

When starting a new conversation to execute this plan, the LLM needs:

### Context Files (in priority order)
1. **`.ai-context/deep_dive_a_response_quality.md`** — The BUG-6 fix specification
2. **`.ai-context/deep_dive_b_multi_channel.md`** — Multi-channel architecture
3. **`.ai-context/deep_dive_c_dashboard_ux.md`** — Dashboard design spec
4. **`README.md`** — Full project documentation
5. **`.ai-context/implementation_plan.md`** — Phase history
6. **`.ai-context/task.md`** — Task tracker

### Prompt Template for New Session
```
I need to execute the Master Plan for our AI WhatsApp CRM SaaS.

CONTEXT FILES TO READ FIRST (in this order):
1. .ai-context/deep_dive_a_response_quality.md
2. README.md (§0 for current state, §0.9 for active bugs)
3. .ai-context/task.md (for progress tracking)

CURRENT SPRINT: [Sprint 1/2/3]
TODAY'S DATE: [date]
TODAY'S TASKS: [from task.md daily breakdown]

CRITICAL RULES:
- DOCS FIRST: Always consult official docs before implementing
- POST-IMPLEMENTATION: Document what was done, why, with doc links
- NEVER break existing functionality without explicit approval
- Test with real scenarios before deploying
- Update task.md after each completed item
- If an error occurs that blocks progress, report immediately in Discord
```

---

## 9. Risk Register (UPDATED with Research Findings)

| Risk | Likelihood | Impact | Mitigation | Status |
|:---|:---|:---|:---|:---|
| **BSUID migration breaks contact lookups** | Medium (June 2026) | 🔴 Critical | Phase 1 DONE: `bsuid` column added, extraction active. Phase 2 (lookup swap) before June. | ✅ Phase 1 |
| Meta WABA suspension | Medium | 🔴 Critical | Migrate to client-owned WABAs before #7 | ⏳ |
| gpt-5.4-mini quality insufficient | Low | 🔴 Critical | Deployed + tested. Prompt v2 active. Working well. | ✅ Verified |
| **Graph API v19 deprecated May 21** | Low | 🟡 High | Updated to v25.0 (Block A) | ✅ Fixed |
| Fumigation client disappointed at scope | Medium | 🟡 High | Set expectations BEFORE Tuesday | ⏳ |
| **Instagram 24h window — can't re-engage** | High | 🟡 High | Collect email/phone as backup, prefer WhatsApp | ⏳ Sprint 2 |
| **Strict mode breaks tool schemas** | Low | 🟡 Medium | All 7 schemas validated in Block B | ✅ Fixed |
| Cost explosion from o4-mini usage | Low | 🟡 High | Removed from selectable models, `max_completion_tokens=2048` cap | ✅ Fixed |
| Supabase free tier exhausted | Medium | 🟡 High | Monitor DB size, upgrade to Pro at tenant #3 | ⏳ |
| Single point of failure (you) | High | 🔴 Critical | Document everything, build for automation | ⏳ |
