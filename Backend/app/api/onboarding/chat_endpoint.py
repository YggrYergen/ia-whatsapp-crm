# ================================================================================
# ⚠️  DOCS FIRST: SSE streaming endpoint for the onboarding configuration agent.
#     Uses OpenAI Responses API via openai_responses_adapter.py.
#     Streams reasoning summaries → "thinking" events (Matrix visualizer on frontend)
#     Streams response text → "text_delta" events (chat bubble on frontend)
#     Streams tool calls → "field_update" + "progress" events
#
#     Ref: https://platform.openai.com/docs/api-reference/responses/streaming
#     Ref: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
#
# ⚠️  OBSERVABILITY: Every except block → logger + Sentry + Discord (3 channels).
#     Every error includes: where (function:step), what (operation), who (tenant_id),
#     full traceback (exc_info=True), and env (settings.ENVIRONMENT).
# ================================================================================

import json
import asyncio
import traceback as tb_module
from typing import List, Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.core.config import settings
from app.infrastructure.llm_providers.openai_responses_adapter import OpenAIResponsesStrategy
from app.api.onboarding.agent_prompt import (
    ONBOARDING_SYSTEM_PROMPT,
    ONBOARDING_TOOLS,
    ONBOARDING_FIELDS,
)
import sentry_sdk

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

# Singleton adapter — reused across requests (thread-safe via async)
_responses_adapter = None

_WHERE = "onboarding_chat"  # Base for observability context


def _get_adapter() -> OpenAIResponsesStrategy:
    """Lazy-init the Responses API adapter.
    
    Wrapped in try/except because OpenAI client init can fail
    (bad API key, import issues, etc).
    """
    global _responses_adapter
    if _responses_adapter is None:
        try:
            # Config agent uses gpt-5.4 (flagship) with reasoning effort medium
            _responses_adapter = OpenAIResponsesStrategy(model_id="gpt-5.4")
            logger.info(
                f"✅ [{_WHERE}._get_adapter] Responses adapter initialized | "
                f"model=gpt-5.4 | env={settings.ENVIRONMENT}"
            )
        except Exception as init_err:
            _msg = (
                f"[{_WHERE}._get_adapter] CRITICAL: Adapter initialization failed | "
                f"env={settings.ENVIRONMENT} | error={str(init_err)[:300]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(init_err)
            # Can't await in sync function — log + re-raise, caller will handle
            raise
    return _responses_adapter


def _format_sse(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event string.
    
    Ref: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
    """
    try:
        json_data = json.dumps(data, ensure_ascii=False)
        return f"event: {event_type}\ndata: {json_data}\n\n"
    except (TypeError, ValueError) as json_err:
        # JSON serialization failure — extremely unlikely but must not crash the stream
        logger.error(
            f"[{_WHERE}._format_sse] JSON serialization failed | "
            f"event_type={event_type} | data_type={type(data).__name__} | "
            f"error={str(json_err)[:200]}",
            exc_info=True
        )
        sentry_sdk.capture_exception(json_err)
        # Fallback: send a safe error event
        return f'event: error\ndata: {{"message": "SSE serialization error"}}\n\n'


@router.post("/chat")
async def onboarding_chat(request: Request):
    """SSE streaming endpoint for the onboarding configuration agent.
    
    Request body:
      {
        "message": "Mi negocio se llama PetShop Chile",
        "tenant_id": "uuid",
        "conversation_history": [{"role": "user", "content": "..."}, ...],
        "fields_status": {"business_name": true, "business_type": false, ...}
      }
    
    Response: text/event-stream with events:
      event: thinking    — reasoning summary deltas → Matrix visualizer
      event: text_delta  — response text deltas → chat bubble
      event: field_update — tool extracted a field → field turns green
      event: progress    — overall progress update
      event: done        — stream complete
      event: config_complete — all fields done, system prompt generated
      event: error       — error occurred
    """
    tenant_id = None
    current_step = "init"
    
    try:
        # --- Parse request ---
        current_step = "parse_request"
        try:
            body = await request.json()
        except Exception as parse_err:
            _msg = (
                f"[{_WHERE}:{current_step}] Failed to parse request JSON | "
                f"env={settings.ENVIRONMENT} | error={str(parse_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(parse_err)
            await send_discord_alert(
                title="❌ Config Agent: Invalid Request Body",
                description=f"**Where:** `{_WHERE}:{current_step}`\n**What:** JSON parse failed\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(parse_err)[:300]}```",
                severity="error", error=parse_err
            )
            return StreamingResponse(
                iter([_format_sse("error", {"message": "Invalid JSON body"})]),
                media_type="text/event-stream",
            )
        
        message = body.get("message", "")
        tenant_id = body.get("tenant_id")
        raw_history = body.get("conversation_history", [])
        fields_status = body.get("fields_status", {})
        
        # ── Sanitize conversation history ──────────────────────────────────
        # The frontend may include messages from previous turns that contain
        # tool-call related items. The Responses API requires every
        # function_call_output to have a matching function_call in the input,
        # but we don't persist function_call items across turns.
        # FIX: Strip everything except user/assistant text messages.
        conversation_history = []
        stripped_count = 0
        for msg in raw_history:
            role = msg.get("role", "")
            if role in ("user", "assistant"):
                conversation_history.append({
                    "role": role,
                    "content": msg.get("content", "")
                })
            else:
                stripped_count += 1
        if stripped_count > 0:
            logger.warning(
                f"[{_WHERE}:sanitize_history] Stripped {stripped_count} non-user/assistant "
                f"messages from conversation_history | tenant={tenant_id} | "
                f"original_len={len(raw_history)} | clean_len={len(conversation_history)}"
            )
        
        _tenant_ctx = f"tenant={tenant_id} | msg_len={len(message)} | history_len={len(conversation_history)} | env={settings.ENVIRONMENT}"
        
        if not tenant_id:
            logger.warning(f"[{_WHERE}] Missing tenant_id in request | body_keys={list(body.keys())}")
            return StreamingResponse(
                iter([_format_sse("error", {"message": "tenant_id is required"})]),
                media_type="text/event-stream",
            )
        
        # Set Sentry context for all operations in this request
        sentry_sdk.set_context("config_agent_chat", {
            "tenant_id": tenant_id,
            "message_length": len(message),
            "history_length": len(conversation_history),
            "history_raw_length": len(raw_history),
            "history_stripped": stripped_count,
            "fields_complete": sum(1 for v in fields_status.values() if v),
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.set_tag("tenant_id", tenant_id)
        sentry_sdk.set_tag("feature", "onboarding_chat")
        
        logger.info(f"🤖 [CONFIG-AGENT] Chat request: {_tenant_ctx}")
        
        # Build the message history for the adapter
        full_history = list(conversation_history)
        if message:
            full_history.append({"role": "user", "content": message})
            # Persist user message to DB (non-blocking, non-fatal)
            await _persist_message(tenant_id, "user", message)
        
        # --- Init adapter ---
        current_step = "get_adapter"
        try:
            adapter = _get_adapter()
        except Exception as adapter_err:
            _msg = (
                f"[{_WHERE}:{current_step}] Adapter init FAILED | {_tenant_ctx} | "
                f"error={str(adapter_err)[:200]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(adapter_err)
            await send_discord_alert(
                title="💥 Config Agent: Adapter Init Failed",
                description=(
                    f"**Where:** `{_WHERE}:{current_step}`\n"
                    f"**What:** OpenAIResponsesStrategy failed to initialize\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(adapter_err)[:300]}```"
                ),
                severity="error", error=adapter_err
            )
            return StreamingResponse(
                iter([_format_sse("error", {"message": "Error inicializando agente de configuración."})]),
                media_type="text/event-stream",
            )
        
        async def event_generator():
            """Generate SSE events from the streaming response."""
            tool_calls_buffer = []  # Collect tool calls for post-processing
            gen_step = "stream_main"
            last_response_id = None  # Track response ID for chaining follow-ups
            config_complete_sent = False  # Track whether config_complete SSE was sent
            
            try:
                async for event in adapter.generate_response_stream(
                    system_prompt=ONBOARDING_SYSTEM_PROMPT,
                    message_history=full_history,
                    tools=ONBOARDING_TOOLS,
                    reasoning_effort="medium",
                ):
                    event_type = event.get("type")
                    
                    if event_type == "thinking":
                        # Reasoning summary → Matrix visualizer
                        yield _format_sse("thinking", {"text": event["text"]})
                    
                    elif event_type == "text_delta":
                        # Response text → chat bubble
                        yield _format_sse("text_delta", {"delta": event["delta"]})
                    
                    elif event_type == "tool_call":
                        # Tool call completed — process immediately
                        gen_step = "process_tool_call"
                        tool_name = event.get("name", "")
                        tool_args_raw = event.get("arguments", "{}")
                        tool_call_id = event.get("call_id", "")
                        
                        try:
                            tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
                        except json.JSONDecodeError as json_err:
                            _msg = (
                                f"[{_WHERE}:{gen_step}] Tool args JSON parse failed | "
                                f"tenant={tenant_id} | tool={tool_name} | "
                                f"raw_preview={str(tool_args_raw)[:200]} | "
                                f"env={settings.ENVIRONMENT} | error={str(json_err)[:200]}"
                            )
                            logger.error(_msg, exc_info=True)
                            sentry_sdk.capture_exception(json_err)
                            await send_discord_alert(
                                title="⚠️ Config Agent: Tool Args JSON Invalid",
                                description=(
                                    f"**Where:** `{_WHERE}:{gen_step}`\n"
                                    f"**What:** json.loads() failed on tool arguments\n"
                                    f"**Tenant:** `{tenant_id}`\n"
                                    f"**Tool:** `{tool_name}`\n"
                                    f"**Raw preview:** ```{str(tool_args_raw)[:200]}```\n"
                                    f"**Env:** {settings.ENVIRONMENT}\n"
                                    f"**Error:** ```{str(json_err)[:200]}```"
                                ),
                                severity="warning", error=json_err
                            )
                            tool_args = {}
                        
                        tool_calls_buffer.append({
                            "call_id": tool_call_id,
                            "name": tool_name,
                            "arguments": tool_args,
                        })
                        
                        if tool_name == "report_configuration_field":
                            gen_step = "report_field"
                            field_name = tool_args.get("field_name", "")
                            field_value = tool_args.get("field_value", "")
                            confidence = tool_args.get("confidence", "inferred")
                            
                            # Update fields_status
                            fields_status[field_name] = True
                            
                            # Persist to database
                            await _save_field(tenant_id, field_name, field_value)
                            
                            # Send field_update event → field turns green on frontend
                            yield _format_sse("field_update", {
                                "field": field_name,
                                "value": field_value,
                                "confidence": confidence,
                                "complete": True,
                            })
                            
                            # Send progress update
                            completed = sum(1 for f in ONBOARDING_FIELDS if fields_status.get(f, False))
                            total = len(ONBOARDING_FIELDS)
                            yield _format_sse("progress", {
                                "fields_complete": completed,
                                "fields_total": total,
                                "percentage": round((completed / total) * 100),
                            })
                            
                            logger.info(
                                f"📝 [CONFIG-AGENT] Field reported: {field_name}='{field_value[:40]}' | "
                                f"progress={completed}/{total} | tenant={tenant_id}"
                            )
                        
                        elif tool_name == "mark_configuration_complete":
                            gen_step = "finalize_config"
                            generated_prompt = tool_args.get("generated_prompt", "")
                            summary = tool_args.get("summary", "")
                            
                            # Save to database
                            await _finalize_onboarding(tenant_id, generated_prompt, summary)
                            
                            # Send config_complete event
                            yield _format_sse("config_complete", {
                                "system_prompt": generated_prompt,
                                "summary": summary,
                                "all_fields": fields_status,
                            })
                            config_complete_sent = True
                        
                        else:
                            # Unknown tool name — log it
                            logger.warning(
                                f"[{_WHERE}:{gen_step}] Unknown tool called: '{tool_name}' | "
                                f"tenant={tenant_id} | args_preview={str(tool_args)[:200]}"
                            )
                        
                        gen_step = "stream_main"  # Reset step tracker
                    
                    elif event_type == "done":
                        # Capture response_id for potential follow-up chaining
                        last_response_id = event.get("response_id")
                        
                        # Always send 'done' to finalize the current text into a
                        # message on the frontend. If tool calls exist, the follow-up
                        # stream will produce a SECOND 'done' for the follow-up text.
                        # Previous approach (suppressing done) caused the first
                        # stream's text to be lost — see incident 2026-04-14.
                        done_content = event.get("content", "")
                        yield _format_sse("done", {
                            "content": done_content,
                            "all_complete": all(
                                fields_status.get(f, False) for f in ONBOARDING_FIELDS
                            ),
                            "usage": event.get("usage"),
                        })
                        # Persist assistant message (non-fatal)
                        if done_content.strip():
                            await _persist_message(
                                tenant_id, "assistant", done_content,
                                metadata={"tool_calls": len(tool_calls_buffer), "response_id": last_response_id},
                            )
                        logger.info(
                            f"📨 [CONFIG-AGENT] Stream done | tenant={tenant_id} | "
                            f"text_len={len(done_content)} | tool_calls={len(tool_calls_buffer)} | "
                            f"response_id={last_response_id[:16] if last_response_id else 'NONE'}..."
                        )
                
                # ── Follow-up loop ──────────────────────────────────────
                # If there were tool calls, continue the conversation by feeding
                # tool results back using previous_response_id chaining.
                # This is a LOOP because a follow-up can itself produce more
                # tool calls (e.g., report last field → mark_configuration_complete
                # in the same chained response). The old code only handled
                # thinking/text_delta/done in follow-ups — tool_call events were
                # SILENTLY DROPPED, causing the post-completion flow to get stuck
                # (discovered 2026-04-15).
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                followup_round = 0
                MAX_FOLLOWUP_ROUNDS = 5  # Safety limit to prevent infinite loops

                while tool_calls_buffer and followup_round < MAX_FOLLOWUP_ROUNDS:
                    followup_round += 1
                    gen_step = f"tool_followup_r{followup_round}"
                    logger.info(
                        f"🔄 [CONFIG-AGENT] Follow-up round {followup_round} with "
                        f"{len(tool_calls_buffer)} tool results | tenant={tenant_id} | "
                        f"response_id={last_response_id[:20] if last_response_id else 'NONE'}..."
                    )

                    # Build function_call_output items for the follow-up.
                    # The Responses API chains via previous_response_id — we don't resend history.
                    followup_input = []
                    for tc in tool_calls_buffer:
                        if tc["name"] == "report_configuration_field":
                            result = json.dumps({
                                "status": "saved",
                                "field": tc["arguments"].get("field_name"),
                                "value": tc["arguments"].get("field_value"),
                            })
                        elif tc["name"] == "mark_configuration_complete":
                            result = json.dumps({
                                "status": "complete",
                                "message": "Configuration finalized successfully"
                            })
                        else:
                            result = json.dumps({"status": "ok"})

                        followup_input.append({
                            "type": "function_call_output",
                            "call_id": tc["call_id"],
                            "output": result,
                        })

                    # Clear buffer — will be re-populated if follow-up has tool calls
                    prev_tool_count = len(tool_calls_buffer)
                    tool_calls_buffer = []

                    try:
                        async for follow_event in adapter.generate_response_stream(
                            system_prompt=ONBOARDING_SYSTEM_PROMPT,
                            message_history=followup_input,
                            tools=ONBOARDING_TOOLS,
                            reasoning_effort="medium",
                            previous_response_id=last_response_id,
                        ):
                            follow_type = follow_event.get("type")

                            if follow_type == "thinking":
                                yield _format_sse("thinking", {"text": follow_event["text"]})

                            elif follow_type == "text_delta":
                                yield _format_sse("text_delta", {"delta": follow_event["delta"]})

                            elif follow_type == "tool_call":
                                # ── Handle tool calls in follow-up ──────────────
                                # FIX 2026-04-15: This handler was MISSING. Tool calls
                                # in follow-up responses (especially mark_configuration_complete)
                                # were silently dropped, breaking the entire post-completion flow.
                                fu_tool_name = follow_event.get("name", "")
                                fu_tool_args_raw = follow_event.get("arguments", "{}")
                                fu_tool_call_id = follow_event.get("call_id", "")

                                try:
                                    fu_tool_args = json.loads(fu_tool_args_raw) if isinstance(fu_tool_args_raw, str) else fu_tool_args_raw
                                except json.JSONDecodeError as fu_json_err:
                                    _msg = (
                                        f"[{_WHERE}:{gen_step}] Follow-up tool args JSON parse failed | "
                                        f"tenant={tenant_id} | tool={fu_tool_name} | "
                                        f"error={str(fu_json_err)[:200]}"
                                    )
                                    logger.error(_msg, exc_info=True)
                                    sentry_sdk.capture_exception(fu_json_err)
                                    await send_discord_alert(
                                        title=f"⚠️ Config Agent: Follow-up Tool Args Invalid (r{followup_round})",
                                        description=(
                                            f"**Where:** `{_WHERE}:{gen_step}`\n"
                                            f"**Tool:** `{fu_tool_name}`\n"
                                            f"**Tenant:** `{tenant_id}`\n"
                                            f"**Error:** ```{str(fu_json_err)[:200]}```"
                                        ),
                                        severity="warning", error=fu_json_err
                                    )
                                    fu_tool_args = {}

                                # Buffer for potential next follow-up round
                                tool_calls_buffer.append({
                                    "call_id": fu_tool_call_id,
                                    "name": fu_tool_name,
                                    "arguments": fu_tool_args,
                                })

                                if fu_tool_name == "report_configuration_field":
                                    fu_field = fu_tool_args.get("field_name", "")
                                    fu_value = fu_tool_args.get("field_value", "")
                                    fu_conf = fu_tool_args.get("confidence", "inferred")

                                    fields_status[fu_field] = True
                                    await _save_field(tenant_id, fu_field, fu_value)

                                    yield _format_sse("field_update", {
                                        "field": fu_field,
                                        "value": fu_value,
                                        "confidence": fu_conf,
                                        "complete": True,
                                    })

                                    completed = sum(1 for f in ONBOARDING_FIELDS if fields_status.get(f, False))
                                    total = len(ONBOARDING_FIELDS)
                                    yield _format_sse("progress", {
                                        "fields_complete": completed,
                                        "fields_total": total,
                                        "percentage": round((completed / total) * 100),
                                    })
                                    logger.info(
                                        f"📝 [CONFIG-AGENT] Field reported (follow-up r{followup_round}): "
                                        f"{fu_field}='{fu_value[:40]}' | progress={completed}/{total} | "
                                        f"tenant={tenant_id}"
                                    )

                                elif fu_tool_name == "mark_configuration_complete":
                                    fu_prompt = fu_tool_args.get("generated_prompt", "")
                                    fu_summary = fu_tool_args.get("summary", "")

                                    await _finalize_onboarding(tenant_id, fu_prompt, fu_summary)

                                    yield _format_sse("config_complete", {
                                        "system_prompt": fu_prompt,
                                        "summary": fu_summary,
                                        "all_fields": fields_status,
                                    })
                                    config_complete_sent = True
                                    logger.info(
                                        f"🎉 [CONFIG-AGENT] mark_configuration_complete processed in "
                                        f"follow-up round {followup_round} | tenant={tenant_id}"
                                    )

                                else:
                                    logger.warning(
                                        f"[{_WHERE}:{gen_step}] Unknown tool in follow-up: "
                                        f"'{fu_tool_name}' | tenant={tenant_id}"
                                    )

                            elif follow_type == "done":
                                last_response_id = follow_event.get("response_id") or last_response_id
                                follow_content = follow_event.get("content", "")
                                yield _format_sse("done", {
                                    "content": follow_content,
                                    "all_complete": all(
                                        fields_status.get(f, False) for f in ONBOARDING_FIELDS
                                    ),
                                    "usage": follow_event.get("usage"),
                                })
                                if follow_content.strip():
                                    await _persist_message(
                                        tenant_id, "assistant", follow_content,
                                        metadata={
                                            "is_followup": True,
                                            "followup_round": followup_round,
                                            "tool_calls_processed": prev_tool_count,
                                        },
                                    )
                                logger.info(
                                    f"📨 [CONFIG-AGENT] Follow-up r{followup_round} done | "
                                    f"tenant={tenant_id} | text_len={len(follow_content)} | "
                                    f"new_tool_calls={len(tool_calls_buffer)}"
                                )

                    except Exception as followup_err:
                        _tb = tb_module.format_exc()
                        _msg = (
                            f"[{_WHERE}:{gen_step}] Follow-up stream FAILED | "
                            f"tenant={tenant_id} | round={followup_round} | "
                            f"tool_calls={prev_tool_count} | "
                            f"response_id={last_response_id} | "
                            f"env={settings.ENVIRONMENT} | error={str(followup_err)[:200]}"
                        )
                        logger.error(_msg, exc_info=True)
                        sentry_sdk.capture_exception(followup_err)
                        await send_discord_alert(
                            title=f"❌ Config Agent: Follow-up Round {followup_round} Failed",
                            description=(
                                f"**Where:** `{_WHERE}:{gen_step}`\n"
                                f"**What:** Follow-up stream failed (round {followup_round})\n"
                                f"**Tenant:** `{tenant_id}`\n"
                                f"**Response ID:** `{last_response_id}`\n"
                                f"**Env:** {settings.ENVIRONMENT}\n"
                                f"**Error:** ```{str(followup_err)[:300]}```\n"
                                f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
                            ),
                            severity="error", error=followup_err
                        )
                        yield _format_sse("error", {"message": "Error en respuesta de seguimiento del agente."})
                        break  # Exit loop on error

                # ── Safety net: auto-completion if all fields done ──────────
                # If all 10 fields are complete but mark_configuration_complete
                # was never called by the model, proactively finalize.
                if not config_complete_sent and all(
                    fields_status.get(f, False) for f in ONBOARDING_FIELDS
                ):
                    _msg = (
                        f"[{_WHERE}:safety_net] All fields complete but mark_configuration_complete "
                        f"never called — auto-finalizing | tenant={tenant_id} | "
                        f"followup_rounds={followup_round} | env={settings.ENVIRONMENT}"
                    )
                    logger.warning(_msg)
                    sentry_sdk.capture_message(_msg, level="warning")
                    await send_discord_alert(
                        title="⚠️ Config Agent: Auto-Finalization Triggered",
                        description=(
                            f"**Where:** `{_WHERE}:safety_net`\n"
                            f"**What:** Model never called mark_configuration_complete "
                            f"despite all fields being done\n"
                            f"**Tenant:** `{tenant_id}`\n"
                            f"**Follow-up rounds:** {followup_round}\n"
                            f"**Env:** {settings.ENVIRONMENT}\n"
                            f"**Action:** Auto-generating basic prompt and finalizing"
                        ),
                        severity="warning",
                    )

                    try:
                        from app.infrastructure.database.supabase_client import SupabasePooler
                        db = await SupabasePooler.get_client()
                        onb_result = await db.table("tenant_onboarding") \
                            .select("*") \
                            .eq("tenant_id", tenant_id) \
                            .maybe_single() \
                            .execute()

                        if onb_result.data:
                            row = onb_result.data
                            auto_prompt = (
                                f"Eres el asistente virtual de WhatsApp de {row.get('business_name', 'el negocio')}. "
                                f"Tipo de negocio: {row.get('business_type', 'no especificado')}. "
                                f"Descripción: {row.get('business_description', 'no disponible')}. "
                                f"Público objetivo: {row.get('target_audience', 'general')}. "
                                f"Horario: {row.get('business_hours', 'no especificado')}. "
                                f"Tono: {row.get('tone_of_voice', 'profesional')}. "
                                f"Instrucciones especiales: {row.get('special_instructions', 'ninguna')}. "
                                f"Saludo inicial: {row.get('greeting_message', 'Hola, ¿en qué puedo ayudarte?')}. "
                                f"Reglas de escalación: {row.get('escalation_rules', 'derivar a humano cuando sea necesario')}."
                            )
                            auto_summary = f"Auto-configuración de {row.get('business_name', 'negocio')} (safety net)."

                            await _finalize_onboarding(tenant_id, auto_prompt, auto_summary)

                            yield _format_sse("config_complete", {
                                "system_prompt": auto_prompt,
                                "summary": auto_summary,
                                "all_fields": fields_status,
                                "auto_finalized": True,
                            })
                            config_complete_sent = True
                            logger.info(
                                f"🔧 [CONFIG-AGENT] Auto-finalized onboarding | "
                                f"tenant={tenant_id} | prompt_len={len(auto_prompt)}"
                            )
                    except Exception as safety_err:
                        _tb = tb_module.format_exc()
                        logger.error(
                            f"[{_WHERE}:safety_net] Auto-finalization FAILED | "
                            f"tenant={tenant_id} | error={str(safety_err)[:200]}",
                            exc_info=True
                        )
                        sentry_sdk.capture_exception(safety_err)
                        await send_discord_alert(
                            title="❌ Config Agent: Auto-Finalization FAILED",
                            description=(
                                f"**Where:** `{_WHERE}:safety_net`\n"
                                f"**What:** Safety net tried to auto-finalize but failed\n"
                                f"**Tenant:** `{tenant_id}`\n"
                                f"**Env:** {settings.ENVIRONMENT}\n"
                                f"**Error:** ```{str(safety_err)[:300]}```"
                            ),
                            severity="error", error=safety_err
                        )
                            
            except Exception as stream_err:
                _tb = tb_module.format_exc()
                _msg = (
                    f"[{_WHERE}:{gen_step}] Stream FAILED | tenant={tenant_id} | "
                    f"env={settings.ENVIRONMENT} | error={str(stream_err)[:300]}"
                )
                logger.error(_msg, exc_info=True)
                sentry_sdk.capture_exception(stream_err)
                await send_discord_alert(
                    title=f"❌ Config Agent Stream Error at {gen_step}",
                    description=(
                        f"**Where:** `{_WHERE}:{gen_step}`\n"
                        f"**What:** Event generator crashed\n"
                        f"**Tenant:** `{tenant_id}`\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**History:** {len(full_history)} msgs\n"
                        f"**Error:** ```{str(stream_err)[:300]}```\n"
                        f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
                    ),
                    severity="error",
                    error=stream_err,
                )
                yield _format_sse("error", {"message": "Error en el agente de configuración."})
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
            },
        )
    
    except Exception as e:
        _tb = tb_module.format_exc()
        _msg = (
            f"[{_WHERE}:{current_step}] UNEXPECTED crash | tenant={tenant_id} | "
            f"env={settings.ENVIRONMENT} | error={str(e)[:300]}"
        )
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Config Agent CRASH at {current_step}",
            description=(
                f"**Where:** `{_WHERE}:{current_step}`\n"
                f"**What:** Endpoint-level exception before stream started\n"
                f"**Tenant:** `{tenant_id or 'unknown'}`\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Error:** ```{str(e)[:300]}```\n"
                f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
            ),
            severity="error",
            error=e,
        )
        return StreamingResponse(
            iter([_format_sse("error", {"message": "Error interno del servidor."})]),
            media_type="text/event-stream",
        )


async def _save_field(tenant_id: str, field_name: str, field_value: str):
    """Persist a single configuration field to the tenant_onboarding table.
    
    Non-fatal: if this fails, the field was still reported to the frontend.
    The user experience continues, but we need to know it failed for manual recovery.
    """
    _where = f"{_WHERE}._save_field"
    _ctx = f"tenant={tenant_id} | field={field_name} | value_len={len(field_value)} | env={settings.ENVIRONMENT}"
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        
        # Map field_name to column name (they match 1:1)
        valid_columns = {
            "business_name", "business_type", "business_description",
            "target_audience", "business_hours", "tone_of_voice",
            "special_instructions", "greeting_message", "escalation_rules",
        }
        
        if field_name in valid_columns:
            await db.table("tenant_onboarding").update({
                field_name: field_value,
            }).eq("tenant_id", tenant_id).execute()
        elif field_name == "services_offered":
            # Services is JSONB — store as array
            try:
                services = json.loads(field_value) if field_value.startswith("[") else [field_value]
            except json.JSONDecodeError as svc_json_err:
                logger.warning(
                    f"[{_where}] services_offered JSON parse failed (using as single item) | "
                    f"{_ctx} | raw_preview={field_value[:100]} | error={str(svc_json_err)[:100]}",
                    exc_info=True
                )
                sentry_sdk.capture_exception(svc_json_err)
                services = [field_value]
            await db.table("tenant_onboarding").update({
                "services_offered": services,
            }).eq("tenant_id", tenant_id).execute()
        else:
            # Unknown field name — log it, don't crash
            logger.warning(
                f"[{_where}] Unknown field_name '{field_name}' — not persisted | {_ctx}"
            )
            sentry_sdk.capture_message(
                f"Unknown onboarding field: {field_name}", level="warning"
            )
            return
        
        logger.info(f"💾 [CONFIG-AGENT] Saved field {field_name}='{field_value[:50]}...' | {_ctx}")
        
    except Exception as e:
        _tb = tb_module.format_exc()
        _msg = f"[{_where}] DB UPDATE failed | {_ctx} | error={str(e)[:200]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="⚠️ Config Agent: Field Save Failed (Non-Fatal)",
            description=(
                f"**Where:** `{_where}`\n"
                f"**What:** tenant_onboarding UPDATE failed for field `{field_name}`\n"
                f"**Tenant:** `{tenant_id}`\n"
                f"**Value preview:** `{field_value[:80]}`\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Error:** ```{str(e)[:300]}```\n"
                f"**Traceback (last 300 chars):** ```{_tb[-300:]}```\n"
                f"**⚠️ Note:** Field was reported to frontend but NOT saved to DB."
            ),
            severity="warning",
            error=e,
        )
        # Non-fatal — the field was still reported to the frontend


async def _finalize_onboarding(tenant_id: str, generated_prompt: str, summary: str):
    """Finalize the onboarding: save prompt, mark tenant as setup complete.
    
    CRITICAL: If this fails, the tenant's system_prompt won't be saved and
    is_setup_complete will remain false, causing the wizard to re-appear.
    """
    _where = f"{_WHERE}._finalize_onboarding"
    _ctx = f"tenant={tenant_id} | prompt_len={len(generated_prompt)} | env={settings.ENVIRONMENT}"
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        
        # Step 1: Update tenant with generated system prompt + mark complete
        try:
            await db.table("tenants").update({
                "system_prompt": generated_prompt,
                "is_setup_complete": True,
            }).eq("id", tenant_id).execute()
            logger.info(f"✅ [{_where}] Tenant updated with prompt | {_ctx}")
        except Exception as tenant_err:
            _tb = tb_module.format_exc()
            _msg = f"[{_where}:update_tenant] tenants UPDATE failed | {_ctx} | error={str(tenant_err)[:200]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(tenant_err)
            await send_discord_alert(
                title="❌ Onboarding Finalize: Tenant Update FAILED",
                description=(
                    f"**Where:** `{_where}:update_tenant`\n"
                    f"**What:** CRITICAL — system_prompt NOT saved, is_setup_complete still false\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Prompt length:** {len(generated_prompt)} chars\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(tenant_err)[:300]}```\n"
                    f"**⚠️ ACTION REQUIRED:** Manual prompt update for tenant `{tenant_id}`"
                ),
                severity="error", error=tenant_err
            )
            raise  # This IS fatal — re-raise
        
        # Step 2: Update onboarding record
        try:
            await db.table("tenant_onboarding").update({
                "configuration_complete": True,
                "generated_system_prompt": generated_prompt,
            }).eq("tenant_id", tenant_id).execute()
            logger.info(f"✅ [{_where}] Onboarding record finalized | {_ctx}")
        except Exception as onb_err:
            # Non-fatal: tenant was already updated, onboarding record is secondary
            _msg = f"[{_where}:update_onboarding] tenant_onboarding UPDATE failed (non-fatal) | {_ctx} | error={str(onb_err)[:200]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(onb_err)
            await send_discord_alert(
                title="⚠️ Onboarding Finalize: Onboarding Record Failed (Non-Fatal)",
                description=(
                    f"**Where:** `{_where}:update_onboarding`\n"
                    f"**What:** tenant_onboarding UPDATE failed (tenant already updated OK)\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(onb_err)[:300]}```"
                ),
                severity="warning", error=onb_err
            )
        
        logger.info(f"🎉 [CONFIG-AGENT] Onboarding COMPLETE for tenant {tenant_id}! Prompt length: {len(generated_prompt)}")
        
        await send_discord_alert(
            title="🎉 Onboarding Complete!",
            description=(
                f"**Tenant:** `{tenant_id}`\n"
                f"**Summary:** {summary[:200]}\n"
                f"**Prompt length:** {len(generated_prompt)} chars\n"
                f"**Env:** {settings.ENVIRONMENT}"
            ),
            severity="info",
        )
        
    except Exception as e:
        # Only reaches here if tenant update raised (re-raised above)
        # or if something truly unexpected happened
        if "tenant_err" not in dir():
            _tb = tb_module.format_exc()
            _msg = f"[{_where}] UNEXPECTED finalization error | {_ctx} | error={str(e)[:300]}"
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title="❌ Onboarding Finalization CRASH",
                description=(
                    f"**Where:** `{_where}`\n"
                    f"**What:** Unexpected error during finalization\n"
                    f"**Tenant:** `{tenant_id}`\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```\n"
                    f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
                ),
                severity="error",
                error=e,
            )


# ========================================================================
# Message Persistence — onboarding_messages table
# ========================================================================

async def _persist_message(
    tenant_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> None:
    """Persist a single message to onboarding_messages.
    
    Non-fatal: if this fails, the stream continues. But we MUST know about it
    via all 3 observability channels (logger + Sentry + Discord).
    
    Access control: The onboarding_messages table has RLS that restricts SELECT
    to tenant_users of the same tenant. Inserts use the service-role client
    (backend-only). Superadmins query via Supabase Studio or admin API.
    """
    _where = f"{_WHERE}._persist_message"
    _ctx = f"tenant={tenant_id} | role={role} | content_len={len(content)} | env={settings.ENVIRONMENT}"
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        
        await db.table("onboarding_messages").insert({
            "tenant_id": tenant_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }).execute()
        
        logger.debug(f"💬 [{_where}] Persisted {role} message | {_ctx}")
        
    except Exception as e:
        _tb = tb_module.format_exc()
        _msg = f"[{_where}] DB INSERT failed (non-fatal) | {_ctx} | error={str(e)[:200]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="⚠️ Config Agent: Message Persist Failed",
            description=(
                f"**Where:** `{_where}`\n"
                f"**What:** onboarding_messages INSERT failed (non-fatal — stream continues)\n"
                f"**Tenant:** `{tenant_id}`\n"
                f"**Role:** `{role}`\n"
                f"**Content length:** {len(content)} chars\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Error:** ```{str(e)[:300]}```"
            ),
            severity="warning",
            error=e,
        )


# ========================================================================
# GET /api/onboarding/chat/history — Load persisted conversation
# ========================================================================

@router.get("/chat/history")
async def get_chat_history(request: Request):
    """Load persisted conversation history for a tenant.
    
    Query params:
        tenant_id: UUID of the tenant
    
    Returns: JSON array of messages sorted by created_at ASC.
    
    Access: The backend validates that the requesting user belongs to the tenant.
    RLS on onboarding_messages also enforces tenant isolation at DB level.
    Only the newcomer (who belongs to tenant_users) and superadmins 
    (via Supabase Studio / admin API) can access these messages.
    """
    _where = f"{_WHERE}.get_chat_history"
    tenant_id = request.query_params.get("tenant_id")
    
    if not tenant_id:
        return {"error": "tenant_id is required", "messages": []}
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        
        result = await db.table("onboarding_messages") \
            .select("id, role, content, metadata, created_at") \
            .eq("tenant_id", tenant_id) \
            .order("created_at", desc=False) \
            .execute()
        
        messages = result.data if result.data else []
        
        # Also load field completion status from tenant_onboarding
        # so the frontend can restore the progress bar on session resume.
        fields_status = {}
        configuration_complete = False
        try:
            onboarding_result = await db.table("tenant_onboarding") \
                .select(", ".join(ONBOARDING_FIELDS) + ", configuration_complete") \
                .eq("tenant_id", tenant_id) \
                .maybe_single() \
                .execute()
            
            if onboarding_result.data:
                row = onboarding_result.data
                configuration_complete = bool(row.get("configuration_complete", False))
                for field in ONBOARDING_FIELDS:
                    value = row.get(field)
                    # A field is "complete" if it has a non-empty value
                    fields_status[field] = {
                        "complete": bool(value and str(value).strip()),
                        "value": str(value) if value else "",
                        "confidence": "confirmed",
                    }
        except Exception as fields_err:
            # Non-fatal: progress won't restore but messages will
            logger.warning(
                f"[{_where}] Failed to load field status (non-fatal) | "
                f"tenant={tenant_id} | error={str(fields_err)[:200]}"
            )
        
        fields_complete = sum(1 for f in fields_status.values() if f.get("complete"))
        
        logger.info(
            f"📜 [{_where}] Loaded {len(messages)} messages + "
            f"{fields_complete}/{len(ONBOARDING_FIELDS)} fields | "
            f"tenant={tenant_id} | env={settings.ENVIRONMENT}"
        )
        
        return {
            "messages": messages,
            "count": len(messages),
            "fields_status": fields_status,
            "fields_complete": fields_complete,
            "fields_total": len(ONBOARDING_FIELDS),
            "configuration_complete": configuration_complete,
        }
        
    except Exception as e:
        _tb = tb_module.format_exc()
        _msg = (
            f"[{_where}] Failed to load chat history | "
            f"tenant={tenant_id} | env={settings.ENVIRONMENT} | "
            f"error={str(e)[:200]}"
        )
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="❌ Config Agent: History Load Failed",
            description=(
                f"**Where:** `{_where}`\n"
                f"**What:** onboarding_messages SELECT failed\n"
                f"**Tenant:** `{tenant_id}`\n"
                f"**Env:** {settings.ENVIRONMENT}\n"
                f"**Error:** ```{str(e)[:300]}```"
            ),
            severity="error",
            error=e,
        )
        return {"error": "Failed to load history", "messages": []}

