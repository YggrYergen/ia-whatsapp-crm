# ================================================================================
# ⚠️  DOCS FIRST: OpenAI Responses API — /v1/responses
#     Ref: https://platform.openai.com/docs/api-reference/responses/create
#     Ref: https://platform.openai.com/docs/guides/conversation-state
#     Ref: Web search 2026-04-15 confirmed:
#       - tools must be re-supplied every request (not inherited from chain)
#       - store=True required for previous_response_id chaining
#       - developer (system) messages carry over through chains
#
# ⚠️  ISOLATION: This endpoint is 100% independent from the WhatsApp webhook pipeline.
#     It does NOT import:
#       - ProcessMessageUseCase
#       - TenantContext (from app.core.models)
#       - MetaGraphAPIClient
#       - LLMFactory
#       - tool_registry (from app.modules.intelligence)
#       - SchedulingService (from app.modules.scheduling)
#       - GoogleCalendarClient (from app.infrastructure.calendar)
#     Zero shared state with the production webhook path.
#
# ⚠️  TOOLS: Sandbox has its own tool registry (sandbox/tools.py):
#       - 5 calendar tools: SIMULATED (realistic responses, no GCal)
#       - 2 non-calendar tools: REAL (DB + event bus)
#     Import chain verified 2026-04-15: zero Google library imports.
#
# ⚠️  OBSERVABILITY: Every except block → logger + Sentry + Discord (3 channels).
# ================================================================================

import json
import traceback
from fastapi import APIRouter, Body
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.database.supabase_client import SupabasePooler
import sentry_sdk

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# The Responses adapter — completely separate from OpenAIStrategy (Chat Completions).
# Ref: openai_responses_adapter.py header comment confirms this separation.
from app.infrastructure.llm_providers.openai_responses_adapter import OpenAIResponsesStrategy

# Sandbox-specific tools — NO GoogleCalendarClient in import chain
# Ref: sandbox/tools.py header comment documents isolation guarantee.
from app.api.sandbox.tools import (
    SANDBOX_TOOL_SCHEMAS,
    execute_sandbox_tool,
)

# Maximum tool execution rounds — same as production (use_cases.py Block D)
# Prevents infinite tool-calling loops.
MAX_TOOL_ROUNDS = 3


@router.post("/chat")
async def sandbox_chat(payload: dict = Body(...)):
    """Process a sandbox chat message with full tool support using the Responses API.
    
    This endpoint:
      1. Receives a user message + tenant_id + contact_id
      2. Loads the tenant's system_prompt from DB (direct query, NO TenantContext)
      3. Loads conversation history from `messages` table
      4. Calls OpenAI Responses API with all 7 sandbox tools
      5. Executes tool calls (5 simulated calendar + 2 real)
      6. Loops back to LLM with tool results (up to MAX_TOOL_ROUNDS)
      7. Stores the AI response in `messages` table
      8. Frontend receives it via Supabase Realtime subscription
    
    ISOLATION GUARANTEE:
      - Does NOT touch ProcessMessageUseCase
      - Does NOT touch MetaGraphAPIClient
      - Does NOT construct TenantContext
      - Does NOT use LLMFactory
      - Does NOT use app.modules.intelligence.tool_registry
      - Uses its own OpenAIResponsesStrategy instance
      - Uses sandbox-specific tool implementations (sandbox/tools.py)
    
    Ref: https://platform.openai.com/docs/api-reference/responses/create
    """
    _WHERE = "sandbox_chat"
    tenant_id = payload.get("tenant_id")
    contact_id = payload.get("contact_id")
    message = payload.get("message", "").strip()
    
    _ctx = f"tenant={tenant_id} | contact={contact_id} | msg_len={len(message)} | env={settings.ENVIRONMENT}"
    
    # ─── Input validation ─────────────────────────────────────────
    if not tenant_id or not contact_id or not message:
        logger.warning(f"[{_WHERE}] Missing required fields | {_ctx}")
        return ORJSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing tenant_id, contact_id, or message"}
        )
    
    sentry_sdk.set_tag("tenant_id", tenant_id)
    sentry_sdk.set_tag("sandbox", "true")
    
    try:
        db = await SupabasePooler.get_client()
        
        # ─── 1. Load tenant data (direct query, NO TenantContext) ──────
        try:
            tenant_res = await db.table("tenants").select(
                "system_prompt, name, llm_model"
            ).eq("id", tenant_id).single().execute()
        except Exception as tenant_err:
            _msg = f"[{_WHERE}] Tenant query failed | {_ctx} | error={str(tenant_err)[:200]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(tenant_err)
            await send_discord_alert(
                title=f"❌ Sandbox: Tenant Lookup Failed",
                description=f"**Where:** `{_WHERE}`\n**Tenant:** `{tenant_id}`\n**Error:** ```{str(tenant_err)[:300]}```",
                severity="error", error=tenant_err
            )
            return ORJSONResponse(
                status_code=404,
                content={"status": "error", "message": "Empresa no encontrada."}
            )
        
        if not tenant_res.data:
            logger.warning(f"[{_WHERE}] Tenant not found | {_ctx}")
            return ORJSONResponse(
                status_code=404,
                content={"status": "error", "message": "Empresa no encontrada."}
            )
        
        tenant_data = tenant_res.data
        system_prompt = tenant_data.get("system_prompt") or ""
        tenant_name = tenant_data.get("name") or "Negocio"
        llm_model = tenant_data.get("llm_model") or "gpt-5.4-mini"
        
        # If no system_prompt yet (fresh tenant), use a sensible default
        if not system_prompt.strip():
            system_prompt = (
                f"Eres el asistente virtual de {tenant_name}. "
                "Responde de forma amable, profesional y concisa a las consultas de los clientes. "
                "Si no sabes algo, indica que transferirás la consulta al equipo."
            )
            logger.info(f"[{_WHERE}] Using default system_prompt (tenant has none configured) | {_ctx}")
        
        # ─── 2. Load conversation history from messages table ──────────
        try:
            history_res = await db.table("messages").select(
                "sender_role, content"
            ).eq("contact_id", contact_id).order(
                "timestamp", desc=True
            ).limit(30).execute()
        except Exception as hist_err:
            _msg = f"[{_WHERE}] History query failed | {_ctx} | error={str(hist_err)[:200]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(hist_err)
            await send_discord_alert(
                title=f"❌ Sandbox: History Fetch Failed",
                description=f"**Where:** `{_WHERE}`\n**Contact:** `{contact_id}`\n**Error:** ```{str(hist_err)[:300]}```",
                severity="error", error=hist_err
            )
            # Non-fatal: proceed with empty history
            history_res = type("Obj", (), {"data": []})()
        
        # Convert to Chat Completions-style history (the adapter handles conversion)
        message_history = []
        if history_res.data:
            for m in reversed(history_res.data):
                role = m.get("sender_role", "user")
                if role == "assistant":
                    message_history.append({"role": "assistant", "content": m.get("content", "")})
                else:
                    message_history.append({"role": "user", "content": m.get("content", "")})
        
        # Append the current user message if not already in history
        if not message_history or message_history[-1].get("content", "").lower() != message.lower():
            message_history.append({"role": "user", "content": message})
        
        logger.info(
            f"[{_WHERE}] Starting agentic loop | history={len(message_history)} msgs | "
            f"model={llm_model} | tools={len(SANDBOX_TOOL_SCHEMAS)} | {_ctx}"
        )
        
        # ─── 3. Agentic Loop — Responses API with tool calling ─────────
        #
        # Protocol: OpenAI Responses API function calling with chaining
        # Ref: https://platform.openai.com/docs/api-reference/responses/create
        #
        # Flow per round:
        #   1. Call Responses API with tools + previous_response_id (if chaining)
        #   2. If response has function_call items → execute tools
        #   3. Build function_call_output items as new input
        #   4. Call Responses API again with previous_response_id
        #   5. If no function calls → extract reply text and break
        #
        # Safety:
        #   - MAX_TOOL_ROUNDS caps tool execution rounds (prevents infinite loops)
        #   - Calendar tools return simulated responses (zero GCal dependency)
        #   - Non-calendar tools execute for real (with observability)
        # ──────────────────────────────────────────────────────────────
        
        adapter = OpenAIResponsesStrategy(model_id=llm_model)
        ai_response = ""
        previous_response_id = None
        rounds_executed = 0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        response_dto = None  # Initialized here to prevent UnboundLocalError if round 0 fails
        
        for round_num in range(MAX_TOOL_ROUNDS + 1):  # +1 allows a final text-only response
            try:
                # First round: send full history + system prompt
                # Subsequent rounds: send only tool results, chain via previous_response_id
                if round_num == 0:
                    # First call — full history
                    response_dto = await adapter.generate_response(
                        system_prompt=system_prompt,
                        message_history=message_history,
                        tools=SANDBOX_TOOL_SCHEMAS,
                        previous_response_id=None,
                    )
                else:
                    # Chained call — only tool results as input
                    # Per OpenAI docs: tools must be re-supplied every request
                    response_dto = await adapter.generate_response(
                        system_prompt="",  # Already in the chain
                        message_history=tool_result_items,  # function_call_output items
                        tools=SANDBOX_TOOL_SCHEMAS,
                        previous_response_id=previous_response_id,
                    )
                    
            except Exception as llm_err:
                _tb = traceback.format_exc()
                _msg = (
                    f"[{_WHERE}] Responses API FAILED on round {round_num + 1} | {_ctx} | "
                    f"model={llm_model} | chain={previous_response_id or 'none'} | "
                    f"error={str(llm_err)[:200]}"
                )
                logger.error(_msg, exc_info=True)
                sentry_sdk.set_context("sandbox_agentic_loop", {
                    "round": round_num + 1,
                    "max_rounds": MAX_TOOL_ROUNDS,
                    "tenant_id": tenant_id,
                    "chain_id": previous_response_id,
                })
                sentry_sdk.capture_exception(llm_err)
                await send_discord_alert(
                    title=f"💥 Sandbox: LLM Failed Round {round_num + 1} | Tenant {tenant_id}",
                    description=(
                        f"**Where:** `{_WHERE}`\n"
                        f"**Model:** `{llm_model}`\n"
                        f"**Round:** {round_num + 1}/{MAX_TOOL_ROUNDS}\n"
                        f"**Chain:** `{previous_response_id or 'none'}`\n"
                        f"**Error:** ```{str(llm_err)[:300]}```\n"
                        f"**Traceback (last 300 chars):** ```{_tb[-300:]}```"
                    ),
                    severity="error", error=llm_err
                )
                ai_response = "Disculpa, tuve un inconveniente técnico. ¿Podrías intentar de nuevo?"
                break
            
            rounds_executed = round_num + 1
            
            # Track usage across rounds
            total_prompt_tokens += response_dto.prompt_tokens or 0
            total_completion_tokens += response_dto.completion_tokens or 0
            
            # Capture response_id for chaining
            previous_response_id = response_dto.response_id
            
            logger.info(
                f"✅ [{_WHERE}] Round {rounds_executed}/{MAX_TOOL_ROUNDS} — "
                f"ToolCalls={response_dto.has_tool_calls} | "
                f"ContentPreview='{(response_dto.content or '')[:120]}' | "
                f"ResponseID={previous_response_id or 'none'}"
            )
            
            # ── No tool calls → final text response, we're done ──
            if not response_dto.has_tool_calls:
                ai_response = response_dto.content or ""
                break
            
            # ── Tool calls present → execute and loop ──
            # Per Responses API: tool results go as function_call_output items
            # in the next request's input, chained via previous_response_id
            tool_result_items = []
            
            for tc in response_dto.tool_calls:
                tool_name = tc.get("name", "unknown")
                tool_call_id = tc.get("id", "")
                
                if not tool_call_id:
                    logger.error(f"[{_WHERE}] Missing call_id for tool '{tool_name}' — using fallback")
                    sentry_sdk.capture_message(
                        f"Sandbox: missing tool_call_id for '{tool_name}' | Tenant {tenant_id}",
                        level="error"
                    )
                    tool_call_id = f"fallback_{tool_name}_{round_num}"
                
                # Parse arguments
                try:
                    if isinstance(tc.get("arguments"), str):
                        args = json.loads(tc["arguments"])
                    else:
                        args = tc.get("arguments", {})
                except (json.JSONDecodeError, TypeError) as parse_err:
                    _msg = f"[{_WHERE}] Failed to parse tool args for '{tool_name}': {parse_err}"
                    logger.error(_msg, exc_info=True)
                    sentry_sdk.set_context("sandbox_arg_parse", {
                        "tool_name": tool_name,
                        "raw_arguments": str(tc.get("arguments", ""))[:500],
                        "tenant_id": tenant_id,
                    })
                    sentry_sdk.capture_exception(parse_err)
                    await send_discord_alert(
                        title=f"❌ Sandbox: Arg Parse Error | {tool_name}",
                        description=f"Raw: {str(tc.get('arguments', ''))[:200]}\nError: {str(parse_err)[:200]}",
                        severity="error", error=parse_err
                    )
                    result_str = json.dumps({
                        "status": "error",
                        "message": f"Error procesando argumentos de {tool_name}: {str(parse_err)[:100]}"
                    })
                    # Still append function_call_output (API requires it for every function_call)
                    tool_result_items.append({
                        "type": "function_call_output",
                        "call_id": tool_call_id,
                        "output": result_str,
                    })
                    continue
                
                logger.info(
                    f"🛠️ [{_WHERE}] Round {rounds_executed} — executing tool: {tool_name} | "
                    f"call_id={tool_call_id[:20]}... | args_keys={list(args.keys())}"
                )
                
                # Execute the sandbox tool
                result_str = await execute_sandbox_tool(
                    tool_name=tool_name,
                    arguments=args,
                    tenant_id=tenant_id,
                    tenant_name=tenant_name,
                )
                
                logger.info(
                    f"✅ [{_WHERE}] Tool '{tool_name}' result: {result_str[:200]}"
                )
                
                # Build function_call_output for Responses API
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                tool_result_items.append({
                    "type": "function_call_output",
                    "call_id": tool_call_id,
                    "output": result_str,
                })
            
            # If we have tool results but we're at MAX_TOOL_ROUNDS, do one more
            # text-only call (the for loop's +1 allows this)
            # Loop continues → next iteration calls LLM with tool results
        
        else:
            # for/else: MAX_TOOL_ROUNDS exhausted — loop never broke
            logger.warning(
                f"⚠️ [{_WHERE}] MAX_TOOL_ROUNDS ({MAX_TOOL_ROUNDS}) exhausted | {_ctx}"
            )
            sentry_sdk.set_context("sandbox_max_rounds", {
                "tenant_id": tenant_id,
                "rounds_executed": rounds_executed,
                "max_rounds": MAX_TOOL_ROUNDS,
            })
            sentry_sdk.capture_message(
                f"Sandbox: max tool rounds exhausted ({MAX_TOOL_ROUNDS}) | Tenant {tenant_id}",
                level="warning"
            )
            await send_discord_alert(
                title=f"⚠️ Sandbox: Max Tool Rounds | Tenant {tenant_id}",
                description=(
                    f"LLM kept calling tools for {MAX_TOOL_ROUNDS} rounds without final response.\n"
                    f"Contact: {contact_id}"
                ),
                severity="warning"
            )
            if not ai_response:
                ai_response = "Disculpa, tuve un problema procesando tu solicitud. ¿Podrías intentar de nuevo?"
        
        # ─── Final response handling ──────────────────────────────────
        if not ai_response.strip():
            logger.warning(f"[{_WHERE}] Empty AI response after agentic loop | {_ctx}")
            sentry_sdk.capture_message(f"Sandbox empty response after loop | {_ctx}", level="warning")
            ai_response = "No pude generar una respuesta. Por favor intenta reformular tu pregunta."
        
        logger.info(
            f"[{_WHERE}] Agentic loop complete | rounds={rounds_executed} | "
            f"response_len={len(ai_response)} | "
            f"model={(response_dto.model_used or llm_model) if response_dto else llm_model} | "
            f"total_in={total_prompt_tokens} | total_out={total_completion_tokens} | "
            f"{_ctx}"
        )
        
        # ─── 4. Store AI response in messages table (Realtime delivers to frontend) ───
        try:
            insert_result = await db.table("messages").insert({
                "contact_id": contact_id,
                "tenant_id": tenant_id,
                "sender_role": "assistant",
                "content": ai_response,
            }).execute()
            
            if not insert_result.data:
                logger.warning(f"[{_WHERE}] Message insert returned no data | {_ctx}")
            else:
                logger.info(f"[{_WHERE}] AI response persisted | msg_id={insert_result.data[0].get('id', '?')} | {_ctx}")
                
        except Exception as persist_err:
            _msg = f"[{_WHERE}] Failed to persist AI response | {_ctx} | error={str(persist_err)[:200]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(persist_err)
            await send_discord_alert(
                title=f"❌ Sandbox: Response Persistence Failed",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**What:** AI response generated but NOT saved to DB\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Contact:** `{contact_id}`\n"
                    f"**Response preview:** `{ai_response[:100]}...`\n"
                    f"**Error:** ```{str(persist_err)[:300]}```"
                ),
                severity="error", error=persist_err
            )
            # Still return the response to the frontend even if persistence failed
        
        return {
            "status": "success",
            "content": ai_response,
            "usage": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "model": response_dto.model_used or llm_model,
                "rounds": rounds_executed,
            }
        }
    
    except Exception as e:
        _tb = traceback.format_exc()
        _msg = f"[{_WHERE}] UNEXPECTED crash | {_ctx} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"💥 Sandbox: Unexpected Crash",
            description=(
                f"**Where:** `{_WHERE}`\n"
                f"**Tenant:** `{tenant_id}`\n"
                f"**Error:** ```{str(e)[:300]}```\n"
                f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
            ),
            severity="error", error=e
        )
        return ORJSONResponse(
            status_code=500,
            content={"status": "error", "message": "Error interno del servidor."}
        )
