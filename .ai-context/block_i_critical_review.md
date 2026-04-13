# Block I — Critical Review of Diagnostic Report

**Reviewer:** Antigravity (second agent)
**Date:** 2026-04-12
**Verdict:** ⚠️ **Diagnosis is GOOD but implementation plan has DANGEROUS blind spots**

---

## 0. Your Critical Question: Multi-Chat + Multi-Tenancy Isolation

> _"Is our system currently capable of making different conversations for each chat/number?"_

### ✅ YES — Conversation isolation is architecturally sound

After reviewing the full stack, the system DOES properly isolate conversations:

**Tenant isolation (multi-tenancy):**
- Webhook payload → `phone_number_id` extracted ([dependencies.py:65](file:///d:/WebDev/IA/Backend/app/api/dependencies.py#L65))
- `phone_number_id` → DB lookup `tenants.ws_phone_id` ([dependencies.py:76](file:///d:/WebDev/IA/Backend/app/api/dependencies.py#L76))
- Every downstream query uses `tenant.id` as a filter
- PROD schema confirms: `contacts.tenant_id`, `messages.tenant_id` — all FK'd to `tenants.id`
- RLS is enabled on ALL tables (verified via MCP schema query)

**Per-contact conversation isolation:**
- Contact lookup: `phone_number + tenant_id` ([use_cases.py:125](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L125))
- History fetch: filtered by `contact_id` ([use_cases.py:349](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L349))
- Messages persisted with `contact_id + tenant_id` ([use_cases.py:199-201](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L199-L201))
- Rate limiter keyed on `tenant_id:phone` ([rate_limiter.py:61](file:///d:/WebDev/IA/Backend/app/core/rate_limiter.py#L61))

**Bottom line:** If phone A texts CasaVitaCure and phone B texts FumigacionXYZ, they get completely separate conversations, separate contacts, separate histories, separate system prompts. ✅

### ⚠️ BUT: Two contacts on the SAME tenant DO share the same system prompt

This is by design (tenant-level prompt), but it means BUG-B/BUG-C/BUG-G fixes (prompt rewrites) affect ALL contacts of that tenant simultaneously. No per-contact prompt customization exists. This is fine architecturally but important to know when rewriting the prompt — you're changing it for ALL patients.

---

## 1. Diagnosis Accuracy Assessment

| Finding | Accuracy | My Assessment |
|:---|:---|:---|
| **1.1** Dedup logic | ✅ Correct | The other agent's walkback confusion shows they oscillated but landed on the right answer |
| **1.2** `[(Log): timestamp]` pollution | ✅ Correct | Confirmed at [use_cases.py:384](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L384) |
| **1.3** `human_agent` → `"assistant"` role | ✅ Correct, **but fix is WRONG** (see §2) |
| **2.1** `max_completion_tokens=500` truncation | ✅ Correct and CRITICAL | Confirmed at [openai_adapter.py:70](file:///d:/WebDev/IA/Backend/app/infrastructure/llm_providers/openai_adapter.py#L70) |
| **2.2-2.4** API contract | ✅ Correct | No issues found |
| **3.1-3.2** Tool execution | ⚠️ Incomplete | Didn't check if truncation breaks tool_calls JSON |
| **4.1-4.4** System prompt | ✅ Correct | "obligatoria" template wording confirmed as smoking gun |
| **5.1-5.3** Message dedup | ✅ Correct | No `wamid` anywhere in codebase |

---

## 2. DANGEROUS BLIND SPOTS in the Proposed Fixes

### 🔴 BLIND SPOT 1: `max_completion_tokens=500` ALSO truncates tool_calls JSON

The other agent identified the 500-token limit as cause of BUG-A (broken record), but **completely missed** that this SAME limit also truncates `tool_calls` JSON arguments.

**Per OpenAI documentation (confirmed via web search):**
> `max_completion_tokens` governs the ENTIRE generation, including the structured JSON produced for tool calls. If the model runs out of tokens while generating the arguments string, the output is cut off, resulting in **malformed JSON**.

Our code at [use_cases.py:566](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L566) does catch `json.JSONDecodeError`, but:
- It logs the error and continues → the tool gets an error response
- The LLM then sees the error and tries again → same truncation → **infinite loop until MAX_TOOL_ROUNDS**
- This is a **doom loop** that wastes 3 full LLM calls per message

> [!CAUTION]
> **Cascading risk:** If `max_completion_tokens` is raised to 1024 without also checking `finish_reason`, we only reduce the probability of truncation — we don't eliminate it. The doom loop risk remains for any response that exceeds 1024 tokens. **The `finish_reason` check is not optional — it's the ONLY way to detect this.**

### 🔴 BLIND SPOT 2: Fix Priority 2 (human_agent → skip entirely) will BREAK escalation UX

The other agent recommends **Option A: Skip human_agent messages entirely** from LLM history.

**This is WRONG.** Here's why:

1. When a human agent takes over a conversation (e.g. after `request_human_escalation`), they send messages via the dashboard
2. These are stored as `sender_role: "human_agent"` in the messages table
3. The NEXT time the patient sends a WhatsApp message, the webhook fires again
4. If human_agent messages are SKIPPED from history, the LLM has NO IDEA a human already responded
5. The LLM will respond AS IF it's still the active agent, contradicting what the human just said
6. **The patient gets conflicting messages from bot and human simultaneously**

**Per OpenAI documentation (confirmed via web search):**
> Do not use the `assistant` role for human participants. If the model sees an `assistant` message that it did not generate, it may become confused about its own role. Always use the `user` role for humans.

The CORRECT fix per OpenAI best practices:

```python
# Option C (CORRECT): Map human_agent to role:"user" with name field
elif sr == "human_agent":
    rol = "user"
    # Use name field to distinguish from patient
    history.append({"role": "user", "name": "agente_humano", "content": f"[Mensaje del equipo]: {m['content']}"})
    continue  # Skip the generic append below
```

This way:
- The LLM sees the human agent's messages as input (not as its own output)
- The `name` field + prefix distinguishes it from the patient
- The LLM knows a human already intervened and can adapt its behavior
- The system prompt can include: "Si un agente humano ya intervino, respeta lo que dijo y no lo contradigas"

### 🟡 BLIND SPOT 3: Processing lock race condition is REAL and proposed fix doesn't address it

The other agent correctly identified the race condition at [use_cases.py:372-374](file:///d:/WebDev/IA/Backend/app/modules/communication/use_cases.py#L372-L374):

```python
_, history = await asyncio.gather(
    _set_processing(),
    _fetch_history()
)
```

But their **proposed fix** (webhook dedup via `wamid`) only solves Meta re-delivery. It does NOT solve the race condition scenario where:
1. Two DIFFERENT webhooks (different `wamid`s) arrive within milliseconds (user sends "hola" then "buenas" rapidly)
2. Both pass the `is_processing` check (still `false`)
3. Both set the lock and process simultaneously

**Per Supabase/PostgREST documentation (confirmed via web search):**
> Each Supabase client request is an independent HTTP request. Any lock acquired via `SELECT FOR UPDATE` is released immediately. `asyncio.Lock()` only works within the SAME process — Cloud Run may spin up multiple instances.

The CORRECT fix is a **PostgreSQL RPC function** that atomically checks-and-sets the lock:

```sql
CREATE OR REPLACE FUNCTION acquire_processing_lock(p_contact_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
  was_locked BOOLEAN;
BEGIN
  UPDATE contacts 
  SET is_processing_llm = true 
  WHERE id = p_contact_id AND is_processing_llm = false
  RETURNING true INTO was_locked;
  
  RETURN COALESCE(was_locked, false);
END;
$$ LANGUAGE plpgsql;
```

Then in Python: `result = await db.rpc('acquire_processing_lock', {'p_contact_id': contact_id}).execute()` — if `false`, another pipeline already owns the lock. This is atomic at the database level.

---

## 3. Fix Priority Reordering (What I Recommend)

The other agent's priority order has some problems. Here's my recommended order with rationale:

### Priority 1: `finish_reason` check + `max_completion_tokens` increase
**Why first:** This is the ROOT of BUG-A, BUG-D, and the potential doom loop. Without this, everything else is cosmetic.

**Specifics:**
- Raise `max_completion_tokens` from 500 → **2048** (not 1024)
  - gpt-5.4-mini supports 128K output tokens — 2048 is 0.0016% of capacity
  - Cost at $4.50/1M output: 2048 tokens = ~$0.009/response MAX — still under $0.01
  - 1024 may STILL truncate tool_calls with complex arguments (e.g. `book_round_robin` with datetime strings)
  - Average WhatsApp response is 50-150 tokens — you pay for ACTUAL usage, not the cap
- Add `finish_reason` check in `openai_adapter.py` BEFORE returning the DTO
- If `finish_reason == "length"`: log WARNING + Sentry, set `dto.was_truncated = True`
- In `use_cases.py`: if `response_dto.was_truncated` and `response_dto.has_tool_calls` → **DO NOT execute tools** — the JSON is likely corrupt

> [!IMPORTANT]
> **Cost clarification the other agent got wrong:** They said 1024 "doubles the max cost from ~$0.00225 to ~$0.0046." This is misleading. You pay for TOKENS GENERATED, not the cap. Setting `max_completion_tokens=2048` costs **exactly the same** as 1024 if the model only generates 200 tokens. The cap just prevents runaway responses.

### Priority 2: `human_agent` role fix (Option C, not Option A)
**Why second:** BUG-E causes active harm — conflicting messages between bot and human. Fix with role:"user" + name:"agente_humano" as described in §2.

### Priority 3: Remove `[(Log): timestamp]` prefix
**Why third:** Simple, zero-risk, improves LLM context quality immediately.

### Priority 4: Webhook dedup via `wamid` + atomic lock RPC
**Why fourth:** BUG-F (double response) is annoying but not data-corrupting. The `wamid` column addition is a schema migration that needs the full Migration Parity Rule lifecycle.

> [!WARNING]
> **Cascading risk:** Adding a `wamid TEXT UNIQUE` column to the `messages` table (96 rows in PROD) requires:
> 1. Apply migration to DEV
> 2. Verify on DEV
> 3. Apply migration to PROD (with user approval)
> 4. Verify on PROD
> 5. Code change must be deployed AFTER migration is on PROD
> 
> If code deploys before the column exists on PROD → **crash on every message insert** because the code will try to write to a column that doesn't exist.

### Priority 5: System prompt rewrite (BUG-B, BUG-C, BUG-G)
**Why last:** This is the most SUBJECTIVE fix and carries the highest risk of unintended behavioral changes. It should be done carefully with the business owner's input.

**Specific recommendations per OpenAI best practices (confirmed via search):**
1. Remove all "Ejemplo de estructura obligatoria" wording → replace with "Puedes usar esta guía"
2. Add `frequency_penalty: 0.3` and `presence_penalty: 0.3` to the API call — this mathematically penalizes token repetition
3. Add explicit anti-repetition instruction to INTERNAL_TOOL_RULES: "NUNCA repitas la misma respuesta que ya diste en esta conversación"
4. Remove specific symptom words from templates (e.g. "piernas") — use `[síntoma del paciente]` placeholder only when the patient has ACTUALLY mentioned a symptom
5. Add phase gate: "ANTES de pedir datos de agendamiento, CONFIRMA que el paciente respondió las 3 preguntas de triaje. Si no las respondió, hazlas primero."

---

## 4. Risks of Blindly Following the Report

| Risk | Probability | Impact | Mitigation |
|:---|:---|:---|:---|
| `human_agent` messages skipped → bot contradicts human staff | **HIGH** if Option A is implemented | 🔴 CRITICAL — breaks escalation workflow | Use Option C (role:"user" + name field) |
| `wamid` UNIQUE column deployed to code before PROD migration | **MEDIUM** | 🔴 CRITICAL — every message insert crashes | Deploy migration BEFORE code, using Migration Parity Rule |
| 1024 tokens still truncates complex tool_calls | **LOW-MEDIUM** | 🟡 HIGH — doom loop wastes LLM calls | Use 2048 + finish_reason circuit breaker |
| System prompt rewrite changes business behavior unexpectedly | **MEDIUM** | 🟡 HIGH — could stop triaje entirely if gate is too strict | Test prompt changes on DEV sandbox first, get owner approval |
| `frequency_penalty` makes responses too random/incoherent | **LOW** | 🟡 MEDIUM — responses become gibberish | Start at 0.3, not higher |
| Processing lock race condition remains after wamid dedup | **LOW** (but not zero) | 🟡 MEDIUM — double processing on rapid messages | Implement atomic RPC lock |

---

## 5. Things the Report Got RIGHT

Credit where due — the diagnosis quality is strong:

1. ✅ **BUG-A root cause is correct** — `max_completion_tokens=500` + "obligatoria" template = broken record
2. ✅ **BUG-C root cause is correct** — "piernas" in template → hallucinated patient context
3. ✅ **BUG-D hypothesis is sound** — template responses bypass tool calling
4. ✅ **BUG-F root cause is correct** — no webhook dedup
5. ✅ **Track 1 analysis is thorough** — history loading is well-understood
6. ✅ **The `[(Log): timestamp]` finding** is a good catch that would've been easy to miss
7. ✅ **The diagnosis-first approach** (Phase 1 before Phase 2) was exactly right

---

## 6. Summary of Additional Actions Needed (Not in Original Report)

1. **Add `finish_reason` to LLMResponse DTO + check it** — this is the #1 missing piece
2. **Add `was_truncated` boolean flag** to DTO for upstream circuit breaking
3. **Add `frequency_penalty: 0.3` + `presence_penalty: 0.3`** to API call params — research-backed anti-repetition
4. **Add truncation circuit breaker** in agentic loop — if tool_calls are truncated, DON'T execute them
5. **Create `acquire_processing_lock` RPC** for atomic check-and-set
6. **Use role:"user" + name:"agente_humano"** instead of skipping human_agent messages
7. **Use 2048 tokens** not 1024 — cost difference is ZERO for typical responses
8. **Migration sequencing** — `wamid` column MUST exist on PROD before code that writes to it is deployed

---

## 7. Recommended Execution Sequence

```
Step 1: openai_adapter.py changes (zero-migration, code-only)
  ├── max_completion_tokens: 500 → 2048
  ├── Add finish_reason to DTO
  ├── Add frequency_penalty: 0.3, presence_penalty: 0.3
  └── Log finish_reason on every response

Step 2: use_cases.py changes (zero-migration, code-only)
  ├── human_agent → role:"user" + name:"agente_humano" 
  ├── Remove [(Log): timestamp] prefix from line 384
  ├── Add truncation circuit breaker in agentic loop
  └── Test on DEV sandbox → verify all 7 bugs

Step 3: System prompt rewrite (DB change, needs approval)
  ├── Draft new prompt → present to user
  ├── Apply to DEV tenant first
  ├── Test on DEV sandbox
  ├── Apply to PROD after user approval
  └── Follow Migration Parity Rule

Step 4: Webhook dedup (migration + code)
  ├── Create acquire_processing_lock RPC (DEV → verify → PROD)
  ├── Add wamid column to messages (DEV → verify → PROD)  
  ├── Deploy code that uses wamid AFTER both migrations on PROD
  └── Verify dedup works with rapid-fire test messages
```

> [!IMPORTANT]
> Steps 1-2 are **code-only** — no migrations needed. They can be deployed immediately.
> Steps 3-4 involve database changes and need the full Migration Parity Rule lifecycle.
> This sequencing minimizes risk while fixing the most impactful bugs first.
