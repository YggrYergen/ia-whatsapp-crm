# ================================================================================
# ⚠️  DOCS FIRST: OpenAI Responses API — /v1/responses
#     Ref: https://platform.openai.com/docs/api-reference/responses/create
#     Ref: https://platform.openai.com/docs/guides/conversation-state
#
# ⚠️  ISOLATION: This endpoint is 100% independent from the WhatsApp webhook pipeline.
#     It does NOT import:
#       - ProcessMessageUseCase
#       - TenantContext (from app.core.models)
#       - MetaGraphAPIClient
#       - LLMFactory
#       - tool_registry
#     Zero shared state with the production webhook path.
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


@router.post("/chat")
async def sandbox_chat(payload: dict = Body(...)):
    """Process a sandbox chat message using the Responses API.
    
    This endpoint:
      1. Receives a user message + tenant_id + contact_id
      2. Loads the tenant's system_prompt from DB (direct query, NO TenantContext)
      3. Loads conversation history from `messages` table
      4. Calls OpenAI Responses API (NOT Chat Completions)
      5. Stores the AI response in `messages` table
      6. Frontend receives it via Supabase Realtime subscription
    
    ISOLATION GUARANTEE:
      - Does NOT touch ProcessMessageUseCase
      - Does NOT touch MetaGraphAPIClient
      - Does NOT construct TenantContext
      - Does NOT use LLMFactory
      - Does NOT go through tool_registry
      - Uses its own OpenAIResponsesStrategy instance
    
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
        
        # ─── 1. Load tenant's system_prompt (direct query, NO TenantContext) ───
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
        
        # ─── 2. Load conversation history from messages table ───
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
            f"[{_WHERE}] Calling Responses API | history={len(message_history)} msgs | "
            f"model={llm_model} | {_ctx}"
        )
        
        # ─── 3. Call OpenAI Responses API (NO tools — sandbox is text-only) ───
        # Ref: https://platform.openai.com/docs/api-reference/responses/create
        # Using generate_response() (non-streaming) for simplicity.
        # No tools needed in sandbox — the sandbox is for testing conversation quality,
        # not tool execution.
        try:
            adapter = OpenAIResponsesStrategy(model_id=llm_model)
            response_dto = await adapter.generate_response(
                system_prompt=system_prompt,
                message_history=message_history,
                tools=[],  # No tools in sandbox — pure conversation
            )
        except Exception as llm_err:
            _tb = traceback.format_exc()
            _msg = (
                f"[{_WHERE}] Responses API call FAILED | {_ctx} | "
                f"model={llm_model} | error={str(llm_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(llm_err)
            await send_discord_alert(
                title=f"💥 Sandbox: LLM Call Failed",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**Model:** `{llm_model}`\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**History:** {len(message_history)} messages\n"
                    f"**Error:** ```{str(llm_err)[:300]}```\n"
                    f"**Traceback (last 300 chars):** ```{_tb[-300:]}```"
                ),
                severity="error", error=llm_err
            )
            return ORJSONResponse(
                status_code=500,
                content={"status": "error", "message": "Error generando respuesta. Intenta de nuevo."}
            )
        
        ai_response = response_dto.content or ""
        
        if not ai_response.strip():
            logger.warning(f"[{_WHERE}] Empty AI response | {_ctx}")
            sentry_sdk.capture_message(f"Sandbox empty response | {_ctx}", level="warning")
            ai_response = "No pude generar una respuesta. Por favor intenta reformular tu pregunta."
        
        logger.info(
            f"[{_WHERE}] Responses API success | response_len={len(ai_response)} | "
            f"model={response_dto.model_used or llm_model} | "
            f"tokens_in={response_dto.prompt_tokens} | tokens_out={response_dto.completion_tokens} | "
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
                "prompt_tokens": response_dto.prompt_tokens,
                "completion_tokens": response_dto.completion_tokens,
                "model": response_dto.model_used or llm_model,
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
