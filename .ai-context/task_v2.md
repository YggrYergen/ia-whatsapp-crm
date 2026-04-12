# AI CRM — Task Tracker v2 (2026-04-12)

> **Replaces:** `task.md` (v1 had 1000+ lines of completed Phase 0-5 history, many stale checkboxes)  
> **Source of truth for daily status:** `execution_tracker.md`  
> **Operational rules:** `SESSION_PROMPT.md`  
> **Historical record of Phases 0-5:** `task.md` (archived, do not edit)

---

## ✅ COMPLETED — Summary (Phases 0-5, Blocks A-H)

All completed. Full details in `task.md` (archived). Key milestones:

| Phase | What | When |
|:---|:---|:---|
| Phase 0-1 | Infrastructure, security, auth, Cloud Build | Pre Apr-11 |
| Phase 2 | Sentry backend+frontend, Discord alerts, OpenNext migration, RLS policies | Pre Apr-11 |
| Phase 3 | E2E validation, BUG-1/2/3 fixes, observability hardening | Pre Apr-11 |
| Phase 4 | DEV/PROD environment isolation | Apr 10 |
| Phase 5A-C | Meta webhook sim suite, WhatsApp live, permanent token | Apr 10 |
| Block A | gpt-5.4-mini, strict tools, max_completion_tokens, Graph API v25 | Apr 11 |
| Block B | `strict: true` on all 7 tool schemas | Apr 11 |
| Block C | Adapter enhancement (content preservation, usage tracking) | Apr 11 |
| Block D | Agentic loop rewrite (multi-round, `role: "tool"`, error recovery) | Apr 11 |
| Block E | Resilience: HMAC, rate limit, lock TTL, shadow-forward, health, cache | Apr 11 |
| Block F | Observability: correlation ID, Sentry tags, structured logging | Apr 11 |
| Block G | BSUID dormant capture (Phase 1 — extract + store, no lookup change) | Apr 11 |
| Block H | Deploy + live test, HMAC fix, region migration to us-central1, model fix | Apr 11 night |
| Block 0 | Incident fix: permanent lock, `updated_at` migration parity, retry logic | Apr 12 early |
| Block I Steps 1-4 | openai_adapter fixes, human_agent role fix, prompt v2, dedup + atomic lock | Apr 12 |
| Step 5 | reasoning_effort removed (incompatible with tools on chat/completions) | Apr 12 |
| Step 5b | Rapid-fire message batching (DEV only — needs PROD merge) | Apr 12 |

---

## 🔴 UNSOLVED BUGS — MUST FIX BEFORE TUESDAY

| ID | Bug | Detail | Root Cause | Status |
|:---|:---|:---|:---|:---|
| **U-1** | Mobile frontend BROKEN | Dashboard + chat UI unusable on mobile. Layout overflows, buttons unreachable, chat doesn't scroll. Client would rage. | CSS/layout not mobile-first | ❌ Not started |
| **U-2** | Escalation UX missing | No visual badge for `bot_active=false`, no "Resolver" button, no filter. Staff blind to escalations. | Block J not started | ❌ Not started |
| **U-3** | PROD calendar UNVERIFIED | No `book_round_robin` tool on PROD in 24+ hrs. Can't confirm CasaVitaCure booking works. | Unknown — need test | ❌ Need test |
| **U-4** | Dashboard fake data | Mock/placeholder numbers displayed. | Block L not started | ❌ Not started |
| **U-5** | Fumigation prompt not drafted | Need business data from client: services, prices, hours, zones. | Client data not collected | ❌ Need onboarding checklist |
| **U-6** | Rapid-fire fix NOT on PROD | `1f7b250` on `desarrollo` only. PROD silently drops rapid-fire msgs 2+. | Not merged | ❌ Needs approval |
| **U-7** | wamid extraction null | `wamid` column exists, all values `null`. Dedup partially broken. | Payload path may differ | ❌ Not diagnosed |
| **U-8** | Prompt Phase 1 skip | Bot asks "nombre y hora" immediately, skips 3-question triaje. | Prompt v2.1 may not fully fix | ❌ Need E2E test |
| **U-14** | Booking flow repetition loop | Bot re-asks info already provided (name, zone, time) + demands multiple confirmations. Extremely bothersome. | Unknown: prompt? model tool execution? history? agentic loop? | ❌ Need diagnosis + OpenAI docs |

---

## 📋 REMAINING SPRINT 1 WORK (Apr 12-15)

### Tonight (Sat Apr 12, ~7 hrs remaining)

#### Block J: Escalation UX Minimum (U-2) — 2 hrs
- [ ] **J1.** Visual badge on ContactList for `bot_active=false` contacts
- [ ] **J2.** "Resolver y reactivar bot" button in ChatArea
- [ ] **J3.** Filter/tab: "Pendientes" to show escalated contacts first

#### Block L: Minimal Dashboard (U-4) — 30 min
- [ ] **L1.** Replace mock data with real Supabase query: "Mensajes hoy: X, Escalaciones: Y, Último mensaje: hace Z min"

#### Mobile Frontend Fix (U-1) — 3-4 hrs
- [ ] Fix chat layout for mobile viewport (scroll, buttons, contact list)
- [ ] Fix dashboard layout for mobile
- [ ] Test on actual phone browser

#### Diagnosis Work
- [ ] **U-14:** Read OpenAI docs on tool execution patterns (sequential vs concurrent) for gpt-5.4-mini
- [ ] **U-14:** Test booking flow on PROD, identify which stage causes repetition
- [ ] **U-3:** Trigger a test booking on PROD to verify calendar works

---

### Sunday Apr 13

#### Step 6: Enriched Patient Context (30 min)
- [ ] `use_cases.py` — Build richer context block (name, phone, role, created_at, notes, tags)

#### U-14 Fix Implementation
- [ ] Fix root cause of booking repetition loop (prompt? code? model config?)
- [ ] Test on DEV, then approve for PROD

#### U-6: Merge Rapid-Fire Fix to PROD
- [ ] Merge `desarrollo` → `main` (needs pre-merge drift check per §8)
- [ ] Verify on PROD

---

### Monday Apr 14

#### Block M: Fumigation Tenant Setup — 2 hrs
- [ ] **M1.** Buy SIM + register WhatsApp Business number
- [ ] **M2.** Register number in WABA
  - 📚 [Phone Number Management](https://developers.facebook.com/docs/whatsapp/business-management-api/manage-phone-numbers)
- [ ] **M3.** Run tenant setup (provisioning via SQL or script)
- [ ] **M4.** Subscribe webhook to new phone's `messages` field
  - 📚 [WhatsApp Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
- [ ] **M5.** Refine system prompt with tenant input

#### Block N: Full E2E Testing — 3 hrs
- [ ] **N1.** CasaVitaCure E2E: greeting → triaje → availability → booking → confirmation
- [ ] **N2.** Fumigation E2E: service inquiry → quote → appointment request
- [ ] **N3.** Cross-tenant isolation: messages from A don't appear in B
- [ ] **N4.** Error paths: tool failures, LLM timeout, rate limit

#### Block O: Meta Audit — 30 min
- [ ] **O1.** Verify App permissions: `whatsapp_business_messaging` active
- [ ] **O2.** Verify webhook fields subscribed: `messages`, `message_template_status_update`
- [ ] **O3.** Verify System User token: never-expiring, correct permissions

---

### Tuesday Apr 15 — Onboarding Day 🚀

#### Block P: Go-Live
- [ ] **P1.** Publish Meta App to Live Mode (if not done)
- [ ] **P2.** Client walkthrough: show dashboard, explain escalation UX
- [ ] **P3.** Monitor Sentry + Discord + shadow-forwards for 2 hrs post-launch
- [ ] **P4.** Verify both tenants working

#### Block Q: Post-Onboarding
- [ ] **Q1.** Refine fumigation prompt based on first real conversations
- [ ] **Q2.** Prepare WhatsApp template for conversation rescue (submit for Meta approval)
- [ ] **Q3.** Update all documentation with lessons learned

---

## 📋 DEFERRED TO SPRINT 2 (Apr 16-25)

| Item | Why Deferred | Priority |
|:---|:---|:---|
| Dashboard MVP (Charts, KPIs) | Bot quality > dashboard for Tuesday | 🔴 First Sprint 2 |
| Responses API migration | Enables `reasoning.effort` + tools. Major adapter rewrite | 🔴 |
| Instagram DM integration | SELLING POINT but not needed Tuesday | 🔴 |
| Multi-squad booking engine | SELLING POINT for scaling | 🔴 |
| Gemini adapter (+ SDK migration) | `google.generativeai` deprecated → `google.genai` | 🟡 |
| Ideal rapid-fire (abort in-flight LLM) | Current 80/20 fix works. Complex improvement | 🟡 |
| `gpt-5.4-nano` testing | For budget tenants. Verify compatibility | 🟡 |
| Supabase Realtime subscription | Dashboard needs it for live updates | 🟡 |
| Credits/billing system | `usage_logs` table, `consume_credits()` | 🟡 |
| SuperAdmin panel | All-tenants overview, cost tracking | 🟡 |
| BSUID Phase 2 | Lookup swap to BSUID-first. DEADLINE: before June 2026 | 🟡 |
| wamid investigation | Values null in DB. Dedup partially broken | 🟡 |

---

## 📋 LONG-TERM BACKLOG (Sprint 3+)

| Item | Priority |
|:---|:---|
| Calendar Multi-Tenant Architecture Refactor | 🔴 Before tenant #3 |
| Customer Intelligence System (replaces scoring tool) | 🟡 |
| Meta App Review + Tech Provider enrollment | 🟡 Before tenant #7 |
| Facebook Messenger integration | 🟡 |
| Daily briefing generation | 🟢 |
| Staff comments on AI responses | 🟢 |
| Notification system (in-app bell) | 🟢 |
| Sandbox "publish" workflow for prompt changes | 🟢 |

---

## 🔖 Key References

| Resource | URL |
|:---|:---|
| OpenAI Function Calling | https://platform.openai.com/docs/guides/function-calling |
| OpenAI Structured Outputs | https://platform.openai.com/docs/guides/structured-outputs |
| Meta WhatsApp Cloud API | https://developers.facebook.com/docs/whatsapp/cloud-api/ |
| Supabase Python Client | https://supabase.com/docs/guides/getting-started/quickstarts/python |
| Sentry FastAPI | https://docs.sentry.io/platforms/python/integrations/fastapi/ |

---

## 🔖 Environment Quick Reference

| | PROD | DEV |
|:---|:---|:---|
| Backend | `ia-backend-prod` us-central1 | `ia-backend-dev` us-central1 |
| Backend URL | `https://ia-backend-prod-645489345350.us-central1.run.app` | `https://ia-backend-dev-645489345350.us-central1.run.app` |
| Frontend | `dash.tuasistentevirtual.cl` | `ohno.tuasistentevirtual.cl` |
| Supabase | `nemrjlimrnrusodivtoa` (us-east-2) | `nzsksjczswndjjbctasu` (us-west-2) |
| GCP Project | `saas-javiera` | `saas-javiera` |
| Git Branch | `main` | `desarrollo` |
| Discord prefix | (none) | `[🔧 DESARROLLO]` |
| Calendar | Connected (CasaVitaCure SA) | ❌ BY DESIGN |
