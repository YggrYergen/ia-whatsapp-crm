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
| ~~**U-1**~~ | ~~Mobile frontend BROKEN~~ | Fixed: `pb-sidebar` on layout, ChatArea input cleared from nav, responsive grids. Build OK. | Commit `2d6e969` on desarrollo | ✅ DONE |
| ~~**U-2**~~ | ~~Escalation UX missing~~ | Fixed: badge on ContactList, Resolve button (ChatArea + ProfilePanel), filter tabs, sorting, gentle pulse, sidebar badge. | Commit `2d6e969` on desarrollo | ✅ DONE |
| ~~**U-3**~~ | ~~PROD calendar UNVERIFIED~~ | Confirmed working — booked successfully multiple times in last 5hrs. | Verified live | ✅ DONE |
| ~~**U-4**~~ | ~~Dashboard fake data~~ | Fixed: Live alerts from Supabase, INTERVENCIÓN MANUAL section, alert history w/ filters, resolve/dismiss, type badges. | Commit `2d6e969` on desarrollo | ✅ DONE |
| **U-5** | Fumigation prompt not drafted | Template drafted in `.ai-context/fumigation_prompt_template.md`. Blocked on client data (services, prices, hours, zones). | Waiting on client onboarding data | ⏳ TEMPLATE READY |
| ~~**U-6**~~ | ~~Rapid-fire fix NOT on PROD~~ | Merged `73789ef`. Cloud Build auto-deployed revision `00003-z77` to us-central1. | Merged ✅ | ✅ DONE |
| **U-7** | wamid extraction null | `wamid` column exists on `messages` table, all values `null`. This is the WhatsApp Message ID used for webhook dedup — if Meta retries a webhook, wamid prevents double-processing. Code extracts `message.get("id")` but real payloads may nest it differently. **Impact:** dedup falls back to atomic lock + timestamp batching (Block I Step 4) which works but wamid would be more precise. **Risk: LOW** — current fallback handles it. | Payload path needs investigation | 🟡 Low priority |
| **U-8** | Prompt Phase 1 skip | Bot asks "nombre y hora" immediately, skips 3-question triaje. Prompt v2 deployed, testing ongoing. | Testing in progress | ⏳ TESTING |
| **U-14** | Booking flow repetition loop | Bot re-asks info already provided. Fix deployed, testing ongoing. | Testing in progress | ⏳ TESTING |
| ~~**U-15**~~ | ~~Hardcoded europe URL × 5~~ | 5 files pointed to deleted europe-west1 backend → 404 on test chat + calendar. Fixed on main `c5d7b06`. | Hotfix pushed | ✅ DONE |
| ~~**U-16**~~ | ~~contacts.notes column missing~~ | ClientProfilePanel silently failed saving notes. Added column to DEV + PROD. | Migration applied both envs | ✅ DONE |

---

## 📋 REMAINING SPRINT 1 WORK (Apr 12-15)

### Tonight (Sat Apr 12, ~7 hrs remaining)

#### ~~Block J: Escalation UX Minimum (U-2) — 2 hrs~~ ✅ DONE
- [x] **J1.** Visual badge on ContactList for `bot_active=false` contacts
- [x] **J2.** "Resolver y reactivar bot" button in ChatArea + ProfilePanel
- [x] **J3.** Filter/tab: "Todos/Pendientes/Activos" with count badges
- [x] **J4.** Sorted: escalated first, then by last_message_at
- [x] **J5.** Gentle 3s pulse animation (not stroboscopic)
- [x] **J6.** Sidebar escalation count badge
- [x] **J7.** NotificationFeed: type-specific icons, navigate-to-chat

#### ~~Block L: Dashboard (U-4)~~ ✅ DONE
- [x] **L1.** Live alerts from Supabase with realtime subscription
- [x] **L2.** INTERVENCIÓN MANUAL section (live escalations)
- [x] **L3.** Alert history with filter tabs (Pendientes/Todas/Resueltas)
- [x] **L4.** Navigate-to-chat from dashboard alerts
- [x] **L5.** Resolve / Dismiss buttons per alert
- [x] **L6.** Type badges: escalation, cita, cancelación, reagendada

#### ~~Mobile Frontend Fix (U-1) — 3-4 hrs~~ ✅ DONE
- [x] Fix chat layout for mobile viewport (pb-sidebar, input clearing)
- [x] Fix dashboard layout for mobile (responsive grids, pb-24)
- [x] Slide-in animation for profile panel on mobile
- [ ] Test on actual phone browser (pending merge to main)

#### Diagnosis Work
- [x] ~~**U-14:** Read OpenAI docs on tool execution patterns~~ — fix deployed, testing
- [x] ~~**U-14:** Test booking flow on PROD~~ — testing ongoing
- [x] ~~**U-3:** Trigger a test booking on PROD~~ — confirmed working

---

#### Step 6: Enriched Patient Context (30 min)
- [ ] `use_cases.py` — Build richer context block (name, phone, role, created_at, notes, tags)

#### Merge `desarrollo` → `main` 
- [ ] Pre-merge drift check per §8
- [ ] Merge and verify PROD deployment

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
