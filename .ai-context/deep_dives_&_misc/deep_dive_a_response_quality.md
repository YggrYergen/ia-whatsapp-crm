# Deep Dive A v3: Response Quality Architecture — RESEARCH-BACKED + CITED

> **Status:** FINAL — Fully validated with official docs, all links verified (April 2026)  
> **Last Updated:** 2026-04-11 15:30 CLT  
> **Research:** 25+ dedicated web searches completed  
> **Criticality:** 🔴 CRITICAL — This is the product  

---

## 📚 Official Documentation Index (BOOKMARKS FOR IMPLEMENTATION)

### OpenAI API (Core — Read BEFORE coding)
| Doc | URL | Use For |
|:---|:---|:---|
| **Chat Completions API Reference** | https://platform.openai.com/docs/api-reference/chat/create | Message format, parameters, response shape |
| **Function Calling Guide** | https://platform.openai.com/docs/guides/function-calling | Tool definition, `tools` param, `tool_choice`, parallel calls |
| **Structured Outputs Guide** | https://platform.openai.com/docs/guides/structured-outputs | `strict: true`, `additionalProperties: false`, nullable types |
| **Prompt Caching Guide** | https://platform.openai.com/docs/guides/prompt-caching | Automatic caching, 1024-token min, `cached_tokens` monitoring |
| **Prompt Caching Cookbook (201)** | https://platform.openai.com/docs/cookbook/prompt-caching-201 | Advanced optimization, cache key strategies |
| **Models Page** | https://platform.openai.com/docs/models | Model availability, context windows, capabilities |
| **API Pricing** | https://openai.com/api/pricing/ | Current per-token costs for ALL models |
| **Rate Limits Guide** | https://platform.openai.com/docs/guides/rate-limits | 429 handling, exponential backoff, `Retry-After` |
| **Deprecations Page** | https://platform.openai.com/docs/deprecations | Which models are sunset, migration deadlines |
| **Python SDK (GitHub)** | https://github.com/openai/openai-python | Latest SDK version, usage examples, type hints |
| **Python SDK (PyPI)** | https://pypi.org/project/openai/ | Current version: **2.31.0** (April 2026) |

### Python Libraries
| Doc | URL | Use For |
|:---|:---|:---|
| **Pydantic v2 Models** | https://docs.pydantic.dev/latest/concepts/models/ | `model_validate()`, tool argument validation |
| **Pydantic JSON Schema** | https://docs.pydantic.dev/latest/concepts/json_schema/ | Generating JSON schemas from Python models |

---

## 1. 🔴 CRITICAL CORRECTION: Model & Pricing

> [!CAUTION]
> **Previous docs had WRONG pricing.** The README says `gpt-5-mini` at `$0.25/$2.00` — this is OUTDATED.

### Model Status (April 2026)

| Model String | Status | Input $/1M | Output $/1M | Context | Best For |
|:---|:---|:---|:---|:---|:---|
| `gpt-4o-mini` | **⚠️ DEPRECATED** | $0.15 | $0.60 | 128K | Legacy — our current default in code |
| `gpt-5-mini` | **⚠️ LEGACY** (2025) | ~$0.25 | ~$2.00 | — | Superseded by 5.4 variants |
| **`gpt-5.4-mini`** | **✅ ACTIVE** (Mar 2026) | **$0.75** | **$4.50** | **400K** | Agentic workflows, tool calling, coding |
| `gpt-5.4-nano` | ✅ ACTIVE (Mar 2026) | $0.20 | $1.25 | — | Classification, ranking, simple tasks |

**Source:** [OpenAI API Pricing](https://openai.com/api/pricing/)

> [!IMPORTANT]
> **DECISION NEEDED FROM USER:** We have 3 options:
> 1. **`gpt-5.4-mini`** ($0.75/$4.50) — Best tool calling, most expensive. Cost ~$15-30/tenant/mo
> 2. **`gpt-5.4-nano`** ($0.20/$1.25) — Cheapest current model, but may lack quality for complex conversations
> 3. **`gpt-5-mini`** ($0.25/$2.00) — If still accessible via API, good middle ground
> 
> The code currently defaults to `gpt-4o-mini` which is **DEPRECATED**. Must change ASAP.

### Code Current State (MUST FIX)
```python
# Backend/app/core/models.py L9:
llm_model: str = "gpt-4o-mini"  # ← DEPRECATED MODEL!

# Backend/app/infrastructure/llm_providers/openai_adapter.py L23:
def __init__(self, api_key: str = None, model_id: str = "gpt-4o-mini"):  # ← DEPRECATED!

# Backend/app/main.py L219:
tenant_data.setdefault('llm_model', 'gpt-4o-mini')  # ← DEPRECATED!
```

---

## 2. Research Findings (With Sources)

### Finding A1: Structured Outputs (`strict: true`) — GUARANTEED Schema
**Source:** [Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs)

When `strict: true` is set on a tool definition, OpenAI's **Context-Free Grammar** engine guarantees that generated function arguments match the schema exactly. This eliminates hallucinated parameters, missing fields, and wrong types.

**Requirements for strict mode:**
- All properties MUST be in `required` array
- `additionalProperties` MUST be `false` for every object
- Optional parameters → use `"type": ["original_type", "null"]` and still list in `required`
- First request with new schema has slightly higher latency (schema compilation)
- Refusal handling: model returns specific `refusal` field if safety policies triggered

```python
# CORRECT strict tool definition
{
    "type": "function",
    "function": {
        "name": "check_availability",
        "description": "Check appointment availability for a given date",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time_preference": {
                    "type": ["string", "null"],  # Optional → nullable
                    "description": "Morning, afternoon, or evening"
                }
            },
            "required": ["date", "time_preference"],  # ALL fields required
            "additionalProperties": False
        }
    }
}
```

### Finding A2: Prompt Caching — AUTOMATIC, 50%+ Input Savings
**Source:** [Prompt Caching Guide](https://platform.openai.com/docs/guides/prompt-caching) | [Cookbook 201](https://platform.openai.com/docs/cookbook/prompt-caching-201)

**Prompt caching is AUTOMATIC — no code changes to enable.** But structure MUST follow rules:

| Rule | Requirement | Our Status |
|:---|:---|:---|
| System prompt ≥1024 tokens | Must be at least 1024 tokens for caching to activate | ❓ Verify |
| Static content FIRST | System prompt + tool definitions at start of messages array | ✅ Already correct |
| No dynamic prefixes | No timestamps/IDs before system message | ❓ Verify |
| Same prompt prefix | Cache hits require exact prefix match between requests | ✅ Natural for per-tenant |
| Cache retention | 5-10 minutes between requests | ✅ Active conversations |
| Optional: `prompt_cache_key` | Routes requests to same engine for higher hit rate | 🟡 Sprint 2 |
| Monitor: `usage.prompt_tokens_details.cached_tokens` | Must add logging for this field | ❌ Not implemented |

### Finding A3: Parallel Tool Calls
**Source:** [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

- `parallel_tool_calls` parameter defaults to `true` — model CAN return multiple tool calls in one turn
- Each tool call has unique `call_id` — must match when returning results
- Model does NOT manage execution order or dependencies between tools
- If model returns error for this param: drop it from request (some model versions don't support it)
- GPT-5.4 mini fully supports parallel tool calling

### Finding A4: Usage Tracking — Exact Fields
**Source:** [Chat Completions API Reference](https://platform.openai.com/docs/api-reference/chat/create)

```python
# After each LLM call:
usage = response.usage
log_entry = {
    "prompt_tokens": usage.prompt_tokens,
    "completion_tokens": usage.completion_tokens,
    "total_tokens": usage.total_tokens,
    "cached_tokens": getattr(usage.prompt_tokens_details, 'cached_tokens', 0) if usage.prompt_tokens_details else 0,
    "reasoning_tokens": getattr(usage.completion_tokens_details, 'reasoning_tokens', 0) if usage.completion_tokens_details else 0,
    "model_used": response.model,  # ACTUAL model (may differ from requested)
}
```

### Finding A5: Error Handling — EVERY tool_call MUST get a response
**Source:** [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

If a tool call doesn't receive a `role: "tool"` message, the entire conversation chain breaks:

```python
# CORRECT — always respond, even on errors
try:
    result = await execute_tool(tool_name, arguments)
    tool_result = json.dumps(result)
except Exception as e:
    tool_result = json.dumps({
        "error": f"Tool {tool_name} failed: {str(e)}. Please inform the user."
    })
    sentry_sdk.capture_exception(e)

messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": tool_result
})
```

### Finding A6: Rate Limits & Retries
**Source:** [Rate Limits Guide](https://platform.openai.com/docs/guides/rate-limits)

- 429 error → implement exponential backoff with random jitter
- Check `Retry-After` header when present
- Use `tenacity` library for Python retry logic
- Monitor organization-level rate limits in OpenAI dashboard
- Consider `max_completion_tokens` to control output costs

### Finding A7: Spanish Prompt Engineering Best Practices
**Source:** Multiple LatAm AI chatbot production guides (2025-2026)

| Practice | Implementation |
|:---|:---|
| **"Tú" vs "Usted"** | Per-tenant config: wellness → tú, fumigation → usted |
| **Few-shot examples** | Add 2-3 example conversations to system prompt |
| **Positive instructions** | "Responde con empatía" NOT "No seas grosero" |
| **Empathy first** | "Si el cliente expresa frustración, reconoce primero" |
| **Bot disclosure** | "Soy un asistente de IA de [nombre negocio]" at conversation start |
| **Escalation clarity** | Clear instructions for WHEN to use EscalateHumanTool |

---

## 3. Implementation Phases (Exact File + Line References)

### Phase 1: Quick Wins (30 min)
| Fix | File | Line | What |
|:---|:---|:---|:---|
| RC-3 | `use_cases.py` | L64 | Remove `.lower()` — destroys name casing |
| RC-4 | `openai_adapter.py` | L23+ | Always capture `message.content`, even with `tool_calls` |
| RC-7 | `use_cases.py` | BUG-5 area | Disable `TOOL_ACTION_PATTERNS` detector (95% false positives) |
| RC-6 | `use_cases.py` | History logic | Increase from 20 to 30 messages |

**Docs to consult:** None needed, these are fixes to our own code

### Phase 2: Model String Fix (15 min)
| Fix | File | Line | What |
|:---|:---|:---|:---|
| Default model | `core/models.py` | L9 | Change `gpt-4o-mini` → chosen model |
| Adapter default | `openai_adapter.py` | L23 | Change `gpt-4o-mini` → chosen model |
| Main fallback | `main.py` | L219 | Change `gpt-4o-mini` → chosen model |

**Docs to consult:** [Models page](https://platform.openai.com/docs/models), [Pricing](https://openai.com/api/pricing/)

### Phase 3: `strict: true` Tool Schemas (1 hour)
Apply to ALL tools in `Backend/app/modules/scheduling/tools.py`:

| Tool | Changes Needed |
|:---|:---|
| `CheckAvailabilityTool` | `time_preference` → `["string", "null"]`, add to `required`, add `additionalProperties: false` |
| `BookAppointmentTool` | Add `additionalProperties: false`, verify all in `required` |
| `CheckMyAppointmentsTool` | `patient_name`, `phone` → `["string", "null"]`, add to `required` |
| `CancelAppointmentTool` | Add `additionalProperties: false` |
| `EscalateHumanTool` | `urgency` → `["string", "null"]`, add to `required` |
| `UpdatePatientScoringTool` | Full schema overhaul |
| `ConsultScheduleRulesTool` | Add `additionalProperties: false` |

**Docs to consult:** [Structured Outputs Guide](https://platform.openai.com/docs/guides/structured-outputs)

### Phase 4: Agentic Loop Rewrite (3-5 hours)
**File:** `Backend/app/modules/communication/use_cases.py`

**Docs to consult:**
- [Function Calling Guide](https://platform.openai.com/docs/guides/function-calling) — message format, `role: "tool"`
- [Chat Completions API Reference](https://platform.openai.com/docs/api-reference/chat/create) — response shape
- [Pydantic v2 Validation](https://docs.pydantic.dev/latest/concepts/models/) — tool argument validation

**Implementation:**
1. Max rounds: `MAX_TOOL_ROUNDS = 5`
2. Proper `role: "tool"` with matching `tool_call_id`
3. Parallel tool execution: `asyncio.gather(*tool_tasks)`
4. Error recovery: EVERY tool_call gets a response
5. Observation masking: summarize large tool outputs before next LLM call
6. Usage tracking: log all fields from `response.usage`

### Phase 5: LLM Adapter Enhancement (30 min)
**File:** `Backend/app/infrastructure/llm_providers/openai_adapter.py`

**Docs to consult:**
- [Chat Completions API Reference](https://platform.openai.com/docs/api-reference/chat/create) — usage object shape
- [Python SDK](https://github.com/openai/openai-python) — Pydantic models, `.model_dump()`

**Changes:**
- Always return `content` even when `tool_calls` present
- Capture full usage: `prompt_tokens`, `completion_tokens`, `cached_tokens`, `model_used`
- Update `LLMResponse` DTO with new fields

### Phase 6: Context Enrichment (30 min)
**File:** `Backend/app/modules/communication/use_cases.py`

Inject structured contact context into conversation:
```
Name: María García | Phone: +56912345678
Tags: VIP, Returning | Created: 2026-03-15
Last appointment: 2026-04-05 (Masaje facial)
Notes: Prefiere horarios de tarde
```

### Phase 7: System Prompt Best Practices (1 hour)
Ensure system prompt follows prompt caching requirements:
- Static content first, ≥1024 tokens total
- Few-shot examples of ideal conversations
- Empathy acknowledgment instructions
- Bot disclosure
- Per-tenant tone configuration

**Docs to consult:** [Prompt Caching Guide](https://platform.openai.com/docs/guides/prompt-caching)

---

## 4. Tool Schema Migration Checklist

| Tool | Test After Migration | Expected Behavior |
|:---|:---|:---|
| `CheckAvailabilityTool` | "¿tienen hora para mañana?" | Returns dates correctly, no hallucinated params |
| `BookAppointmentTool` | "Quiero agendar para el martes a las 3" | Books with exact params from schema |
| `CheckMyAppointmentsTool` | "¿Cuáles son mis citas?" | Works with name=null, phone=null |
| `CancelAppointmentTool` | "Cancelar mi cita del martes" | Cancels correctly |
| `EscalateHumanTool` | "Necesito hablar con alguien" | Escalates with reason |
| `UpdatePatientScoringTool` | (internal tool) | Updates without errors |
| `ConsultScheduleRulesTool` | "¿A qué hora atienden?" | Returns schedule info |

**Validation:** If `strict: true` causes 400 error → check schemas against [supported JSON schema subset](https://platform.openai.com/docs/guides/structured-outputs)

---

## 5. Cost Impact Analysis (CORRECTED)

### Using gpt-5.4-mini ($0.75/$4.50):
- ~40 conversations/day × 30 days = 1,200 conversations/tenant
- ~3 LLM calls per conversation = 3,600 calls
- ~2K tokens avg per call (input + output split)
- **Input:** ~1.2K avg × 3,600 calls = 4.32M tokens → $3.24/mo
- **Output:** ~0.8K avg × 3,600 calls = 2.88M tokens → $12.96/mo
- **With prompt caching (50% input):** $1.62 input → **~$14.58/mo per tenant**

### Using gpt-5.4-nano ($0.20/$1.25):
- Same volume
- **Input:** $0.86/mo → **With caching:** $0.43
- **Output:** $3.60/mo
- **Total:** **~$4.03/mo per tenant** ← massive savings if quality holds

### Margin comparison at 7 tenants:

| Model | Cost/Tenant | Total Cost (7) | Revenue | Margin |
|:---|:---|:---|:---|:---|
| gpt-5.4-mini | ~15K CLP | ~105K CLP | 560K | **81%** |
| gpt-5.4-nano | ~4K CLP | ~28K CLP | 560K | **95%** |
| gpt-5-mini (if available) | ~8K CLP | ~56K CLP | 560K | **90%** |

---

## 6. Testing Matrix

| Scenario | Expected Behavior | How to Verify | Docs |
|:---|:---|:---|:---|
| Simple greeting | Natural, warm response in Spanish | Manual test | — |
| Tool call (single) | Correct args, natural response | Simulation | [Function Calling](https://platform.openai.com/docs/guides/function-calling) |
| Multi-tool chain | check_avail → book in same convo | Simulation | [Function Calling](https://platform.openai.com/docs/guides/function-calling) |
| Tool error | Graceful "disculpa, problema técnico" | Break tool intentionally | [API Reference](https://platform.openai.com/docs/api-reference/chat/create) |
| Max rounds hit | Fallback message, no infinite loop | Set MAX=1 | — |
| Prompt caching | `cached_tokens > 0` in logs | Check after 2nd message | [Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) |
| Strict mode | No 400 from schemas | Monitor Sentry | [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) |
| Spanish empathy | Acknowledges frustration first | Send frustrated msg | — |
| Name preservation | "María García" stays capitalized | Check DB | — |

---

## 7. Files to Modify (Final)

| File | Changes | Docs Needed |
|:---|:---|:---|
| `Backend/app/modules/communication/use_cases.py` | Agentic loop, RC-1,2,3,5,6,7, correlation ID | [Function Calling](https://platform.openai.com/docs/guides/function-calling) |
| `Backend/app/infrastructure/llm_providers/openai_adapter.py` | Usage tracking, content preservation, model update | [API Reference](https://platform.openai.com/docs/api-reference/chat/create) |
| `Backend/app/modules/scheduling/tools.py` | `strict: true` migration | [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) |
| `Backend/app/core/models.py` | Model default, correlation_id | [Models](https://platform.openai.com/docs/models) |
| `Backend/app/modules/intelligence/router.py` | LLMResponse DTO update | [API Reference](https://platform.openai.com/docs/api-reference/chat/create) |
| `Backend/app/main.py` | Model default fallback | [Models](https://platform.openai.com/docs/models) |
| `Backend/requirements.txt` | `openai>=2.31.0`, `asgi-correlation-id` | [PyPI](https://pypi.org/project/openai/) |
