# ================================================================================
# ⚠️  DOCS FIRST: OpenAI Responses API adapter
#     Uses /v1/responses which supports:
#       - reasoning.effort + tools (simultaneously)
#       - Native streaming with typed events
#       - Reasoning summaries
#       - parallel_tool_calls (default true)
#       - truncation: "auto" (auto-drops old messages if context overflows)
#       - response.status == "incomplete" for truncation detection
#     Ref: https://platform.openai.com/docs/api-reference/responses/create
#     Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
#
# ⚠️  ARCHITECTURE: Used by BOTH the WhatsApp pipeline AND the onboarding agent.
#     Sprint 2 (2026-04-18): migrated from openai_adapter.py (Chat Completions)
#     to unlock reasoning.effort + tools simultaneously.
#
# ⚠️  IMPORTANT: Responses API does NOT support frequency_penalty/presence_penalty.
#     Anti-repetition is handled by the model's reasoning capabilities instead.
#     Ref: https://platform.openai.com/docs/api-reference/responses/create
#
# ⚠️  OBSERVABILITY: Every except block → logger + Sentry + Discord (3 channels).
#     Every error includes: where (function), what (operation), who (model/context),
#     full traceback (exc_info=True), and env (settings.ENVIRONMENT).
# ================================================================================

from typing import List, Dict, Any, Optional, AsyncGenerator
from app.modules.intelligence.router import LLMStrategy, LLMResponse
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
import sentry_sdk
import json
import traceback

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None


class OpenAIResponsesStrategy(LLMStrategy):
    """OpenAI Responses API adapter with streaming + reasoning support.
    
    Key differences from Chat Completions (openai_adapter.py):
    - Uses client.responses.create() instead of client.chat.completions.create()
    - History: `input` list + `previous_response_id` (not `messages` array)
    - Response shape: `output` items array (not choices[0].message)
    - Tool calls: `function_call` output items (not message.tool_calls)
    - Tool results: `function_call_output` items (not role:"tool" messages)
    - Reasoning: `reasoning.effort` works WITH tools (unlike Chat Completions)
    
    Ref: https://platform.openai.com/docs/api-reference/responses
    """
    
    def __init__(self, api_key: str = None, model_id: str = "gpt-5.4-mini"):
        key = api_key or settings.OPENAI_API_KEY
        super().__init__(api_key=key, model_id=model_id)
        if AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=self.api_key)
            logger.info(
                f"✅ [OpenAIResponsesStrategy] Initialized | model={model_id} | env={settings.ENVIRONMENT}"
            )
        else:
            self.client = None
            _msg = (
                f"[OpenAIResponsesStrategy.__init__] openai package not installed — ALL "
                f"Responses API calls will fail | model={model_id} | env={settings.ENVIRONMENT}"
            )
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            # NOTE: Discord is async, can't call from __init__ directly.
            # The first call to generate_response/stream will report to Discord.

    async def generate_response(
        self,
        system_prompt: str,
        message_history: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        tool_choice_override: Optional[Any] = None,
        previous_response_id: Optional[str] = None,
    ) -> LLMResponse:
        """Non-streaming response using Responses API (for compatibility with LLMStrategy interface).
        
        Converts the Chat Completions-style message_history to Responses API input format.
        Supports:
          - reasoning.effort + tools simultaneously
          - parallel_tool_calls (enabled by default)
          - tool_choice override (force specific tool)
          - truncation detection (status="incomplete")
          - auto-truncation of context overflow
        
        Ref: https://platform.openai.com/docs/api-reference/responses/create
        Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
        """
        _where = "OpenAIResponsesStrategy.generate_response"
        tools = tools or []
        _ctx = (
            f"model={self.model_id} | history_len={len(message_history)} | "
            f"tools={len(tools)} | "
            f"chain={'→'+previous_response_id[:20] if previous_response_id else 'none'} | "
            f"env={settings.ENVIRONMENT}"
        )
        
        if not AsyncOpenAI or not self.client:
            _msg = f"[{_where}] SDK not available — cannot generate response | {_ctx}"
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            await send_discord_alert(
                title="💥 OpenAI SDK Missing (Responses API)",
                description=f"**Where:** `{_where}`\n**What:** SDK not installed\n**Context:** {_ctx}",
                severity="error"
            )
            return LLMResponse(content="Error interno del sistema. Por favor intenta de nuevo.")
        
        # Set Sentry context for this request — helps debug any downstream error
        sentry_sdk.set_context("responses_api_request", {
            "model": self.model_id,
            "history_length": len(message_history),
            "tools_count": len(tools),
            "prompt_length": len(system_prompt),
            "tool_choice_override": str(tool_choice_override)[:100] if tool_choice_override else None,
            "previous_response_id": previous_response_id[:20] if previous_response_id else None,
            "environment": settings.ENVIRONMENT,
        })
        
        try:
            # Convert Chat Completions message format → Responses API input format
            # When chaining via previous_response_id, skip system prompt (already in the chain)
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            effective_system = system_prompt if not previous_response_id else ""
            input_items = self._convert_messages_to_input(effective_system, message_history)
            
            # ── Build API kwargs ──
            # max_output_tokens: WhatsApp responses are short (rarely >500 tokens).
            # 2048 is generous for our use case (greeting + tool calls).
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            api_kwargs = {
                "model": self.model_id,
                "input": input_items,
                "max_output_tokens": 2048,
                # store=True: MUST be enabled so the response is persisted on OpenAI
                # servers. This allows subsequent rounds to chain via previous_response_id.
                # BUG FIX (2026-04-24): Previously was `bool(previous_response_id)` which
                # meant Round 1 had store=False → Round 2 got "previous_response_not_found".
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                "store": True,
                # truncation="auto": if input exceeds context window, auto-drop
                # older messages instead of failing with 400.
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                "truncation": "auto",
            }
            
            # ── Adaptive Reasoning Strategy ──
            # Problem: reasoning adds quality but KILLS latency (4.5+ min observed).
            # Solution: conditionally enable based on conversation stage.
            #
            # Stage 1 (greeting): history ≤ 2 msgs → NO reasoning → instant response
            #   The model doesn't need chain-of-thought to say "Hola, bienvenido".
            #
            # Stage 2 (conversation): history > 2 msgs → reasoning.effort="low"
            #   Quality matters for booking, answering service questions, etc.
            #   NOTE: summary="auto" was REMOVED — it added extra generation pass
            #   with no benefit (we don't surface reasoning to the user).
            #
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            _history_len = len(message_history)
            if _history_len > 2:
                api_kwargs["reasoning"] = {"effort": "low"}
                logger.debug(
                    f"🧠 [{_where}] Reasoning ENABLED (effort=low) — "
                    f"history={_history_len} msgs (>2 threshold)"
                )
            else:
                logger.debug(
                    f"⚡ [{_where}] Reasoning DISABLED — "
                    f"history={_history_len} msgs (≤2 = greeting stage)"
                )
            
            # ── Tool conversion ──
            # Tools must be re-supplied every request (not inherited from chain)
            # Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
            #
            # IMPORTANT: Responses API uses a FLAT format for tools:
            #   {type: "function", name: "...", description: "...", parameters: {...}, strict: true}
            # But Chat Completions format nests under "function":
            #   {type: "function", function: {name: "...", ...}}
            # We auto-convert so both formats work transparently.
            if tools:
                converted_tools = []
                for t in tools:
                    if "function" in t and isinstance(t["function"], dict):
                        # Chat Completions format → Responses API flat format
                        func = t["function"]
                        converted = {
                            "type": "function",
                            "name": func.get("name", ""),
                            "description": func.get("description", ""),
                            "parameters": func.get("parameters", {}),
                        }
                        if func.get("strict") is not None:
                            converted["strict"] = func["strict"]
                        converted_tools.append(converted)
                    elif "name" in t:
                        # Already in Responses API format
                        converted_tools.append(t)
                    else:
                        # Unknown format — log + pass through for OpenAI to error clearly
                        _bad_msg = (
                            f"[{_where}] Unknown tool format — no 'function' or 'name' key: "
                            f"{list(t.keys())} | {_ctx}"
                        )
                        logger.warning(_bad_msg)
                        sentry_sdk.capture_message(_bad_msg, level="warning")
                        await send_discord_alert(
                            title="⚠️ Unknown Tool Format",
                            description=f"**Where:** `{_where}`\n**Keys:** {list(t.keys())}\n**Context:** {_ctx}",
                            severity="warning"
                        )
                        converted_tools.append(t)
                api_kwargs["tools"] = converted_tools
                
                # parallel_tool_calls: allow model to call multiple tools per turn.
                # Default is true per OpenAI docs. We keep it enabled for speed.
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                api_kwargs["parallel_tool_calls"] = True
            
            # ── Tool choice override ──
            # Used for force_escalation (forces model to call a specific tool)
            # Responses API format: {"type": "function", "name": "..."}
            # (Note: slightly different from Chat Completions which nests under "function")
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            if tool_choice_override and tools:
                if isinstance(tool_choice_override, dict):
                    # Convert from Chat Completions format if needed
                    if "function" in tool_choice_override and isinstance(tool_choice_override["function"], dict):
                        # Chat Completions: {"type": "function", "function": {"name": "X"}}
                        # Responses API:    {"type": "function", "name": "X"}
                        api_kwargs["tool_choice"] = {
                            "type": "function",
                            "name": tool_choice_override["function"]["name"],
                        }
                    else:
                        api_kwargs["tool_choice"] = tool_choice_override
                elif isinstance(tool_choice_override, str):
                    # String values: "auto", "none", "required"
                    api_kwargs["tool_choice"] = tool_choice_override
                logger.info(
                    f"🔒 [{_where}] tool_choice override applied: {api_kwargs.get('tool_choice')}"
                )
            
            # Chain to a previous response (for tool call follow-ups)
            if previous_response_id:
                api_kwargs["previous_response_id"] = previous_response_id
                logger.info(
                    f"🔗 [{_where}] Chaining to previous response: {previous_response_id[:20]}..."
                )
            
            response = await self.client.responses.create(**api_kwargs)
            
            # ── Truncation detection (Responses API equivalent of finish_reason="length") ──
            # Per OpenAI docs: response.status can be "completed" or "incomplete".
            # If incomplete, response.incomplete_details.reason tells us why.
            # Ref: https://platform.openai.com/docs/api-reference/responses/object
            response_status = getattr(response, 'status', 'completed')
            was_truncated = False
            if response_status == "incomplete":
                was_truncated = True
                incomplete_reason = "unknown"
                if hasattr(response, 'incomplete_details') and response.incomplete_details:
                    incomplete_reason = getattr(response.incomplete_details, 'reason', 'unknown')
                _trunc_msg = (
                    f"[{_where}] Response INCOMPLETE (status=incomplete, reason={incomplete_reason}) | "
                    f"{_ctx} | output_items={len(response.output) if response.output else 0}"
                )
                logger.warning(_trunc_msg)
                sentry_sdk.set_context("responses_api_truncation", {
                    "status": response_status,
                    "reason": incomplete_reason,
                    "model": self.model_id,
                    "has_output": bool(response.output),
                    "output_count": len(response.output) if response.output else 0,
                    "environment": settings.ENVIRONMENT,
                })
                sentry_sdk.capture_message(
                    f"Responses API incomplete (reason={incomplete_reason}) | model={self.model_id}",
                    level="warning"
                )
                await send_discord_alert(
                    title=f"⚠️ Responses API INCOMPLETE | {self.model_id}",
                    description=(
                        f"**Where:** `{_where}`\n"
                        f"**Status:** incomplete\n"
                        f"**Reason:** {incomplete_reason}\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**Context:** {_ctx}"
                    ),
                    severity="warning"
                )
            
            # Guard: response.output could be None or empty
            if not response.output:
                _msg = f"[{_where}] Empty response.output from API | {_ctx} | status={response_status}"
                logger.warning(_msg)
                sentry_sdk.capture_message(_msg, level="warning")
                await send_discord_alert(
                    title="⚠️ Empty Responses API Output",
                    description=(
                        f"**Where:** `{_where}`\n"
                        f"**What:** response.output is empty/None\n"
                        f"**Status:** {response_status}\n"
                        f"**Context:** {_ctx}"
                    ),
                    severity="warning"
                )
                return LLMResponse(content="", was_truncated=was_truncated)
            
            # Parse the response output items
            dto = LLMResponse()
            dto.model_used = self.model_id
            dto.response_id = getattr(response, 'id', None)
            dto.was_truncated = was_truncated
            dto.finish_reason = response_status  # "completed" or "incomplete"
            
            for item in response.output:
                if item.type == "message":
                    for content_part in item.content:
                        if content_part.type == "output_text":
                            dto.content += content_part.text
                elif item.type == "function_call":
                    dto.has_tool_calls = True
                    dto.tool_calls.append({
                        "id": item.call_id,
                        "name": item.name,
                        "arguments": item.arguments,
                    })
                elif item.type == "reasoning":
                    # Reasoning items are internal — log for diagnostics but don't expose
                    logger.debug(
                        f"🧠 [{_where}] Reasoning item present | "
                        f"summary_len={len(getattr(item, 'summary', []) or [])}"
                    )
                else:
                    # Unexpected output item type — log for investigation
                    _unk_msg = (
                        f"[{_where}] Unexpected output item type: {item.type} | {_ctx}"
                    )
                    logger.warning(_unk_msg)
                    sentry_sdk.capture_message(_unk_msg, level="info")
            
            # ── Usage tracking ──
            # Responses API uses input_tokens/output_tokens (not prompt/completion)
            # We map to the LLMResponse DTO fields for backward compatibility
            # with the cost tracking in use_cases.py
            try:
                if response.usage:
                    dto.prompt_tokens = response.usage.input_tokens
                    dto.completion_tokens = response.usage.output_tokens
                    
                    # Detailed token breakdown if available
                    output_details = getattr(response.usage, 'output_tokens_details', None)
                    if output_details:
                        dto.reasoning_tokens = getattr(output_details, 'reasoning_tokens', None)
                    
                    logger.info(
                        f"📊 [LLM Usage Responses] model={self.model_id} "
                        f"input={response.usage.input_tokens} output={response.usage.output_tokens} "
                        f"reasoning={dto.reasoning_tokens or 0} "
                        f"env={settings.ENVIRONMENT}"
                    )
            except Exception as usage_err:
                _msg = (
                    f"[{_where}] Usage parsing failed (non-fatal) | {_ctx} | "
                    f"error={str(usage_err)[:200]}"
                )
                logger.warning(_msg, exc_info=True)
                sentry_sdk.capture_exception(usage_err)
                await send_discord_alert(
                    title="⚠️ Responses API Usage Parsing Failed",
                    description=(
                        f"**Where:** `{_where}`\n"
                        f"**What:** Usage parsing error (response still valid)\n"
                        f"**Error:** {str(usage_err)[:300]}\n"
                        f"**Context:** {_ctx}"
                    ),
                    severity="warning"
                )
            
            return dto
            
        except Exception as e:
            _tb = traceback.format_exc()
            _msg = (
                f"[{_where}] API call FAILED | {_ctx} | "
                f"error={str(e)[:300]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title="💥 OpenAI Responses API Error",
                description=(
                    f"**Where:** `{_where}`\n"
                    f"**What:** Responses API inference failed\n"
                    f"**Model:** {self.model_id}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**History:** {len(message_history)} msgs\n"
                    f"**Error:** ```{str(e)[:300]}```\n"
                    f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
                ),
                severity="error",
                error=e
            )
            raise

    async def generate_response_stream(
        self,
        system_prompt: str,
        message_history: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        reasoning_effort: str = "medium",
        previous_response_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming response using Responses API — yields typed SSE events.
        
        Yields dicts with:
          {"type": "thinking", "text": "..."}          — reasoning summary deltas
          {"type": "text_delta", "delta": "..."}       — response text deltas
          {"type": "tool_call", "name": "...", "arguments": "..."}  — completed tool calls
          {"type": "done", "content": "...", "usage": {...}}         — stream complete
        
        Event mapping from OpenAI Responses API:
          response.reasoning_summary_text.delta → "thinking"
          response.text_delta → "text_delta"  (also: response.output_text.delta)
          response.function_call_arguments.done → "tool_call"
          response.completed → "done"
        
        Ref: https://platform.openai.com/docs/api-reference/responses/streaming
        """
        _where = "OpenAIResponsesStrategy.generate_response_stream"
        _ctx = (
            f"model={self.model_id} | history_len={len(message_history)} | "
            f"tools={len(tools)} | effort={reasoning_effort} | env={settings.ENVIRONMENT}"
        )
        
        if not AsyncOpenAI or not self.client:
            _msg = f"[{_where}] SDK not available — cannot stream | {_ctx}"
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            await send_discord_alert(
                title="💥 OpenAI SDK Missing (Stream)",
                description=f"**Where:** `{_where}`\n**What:** SDK not installed, stream impossible\n**Context:** {_ctx}",
                severity="error"
            )
            yield {"type": "done", "content": "Error interno del sistema.", "usage": None}
            return
        
        # Set Sentry context for this stream
        sentry_sdk.set_context("responses_api_stream", {
            "model": self.model_id,
            "history_length": len(message_history),
            "tools_count": len(tools),
            "reasoning_effort": reasoning_effort,
            "prompt_length": len(system_prompt),
            "environment": settings.ENVIRONMENT,
        })
        
        try:
            input_items = self._convert_messages_to_input(
                system_prompt if not previous_response_id else "",
                message_history
            )
            
            api_kwargs = {
                "model": self.model_id,
                "input": input_items,
                "max_output_tokens": 4096,
                "stream": True,
                "reasoning": {
                    "effort": reasoning_effort,
                    "summary": "auto",
                },
            }
            
            if tools:
                api_kwargs["tools"] = tools
            
            # Chain to a previous response (for tool call follow-ups)
            # Ref: https://platform.openai.com/docs/api-reference/responses/create#responses-create-previous_response_id
            if previous_response_id:
                api_kwargs["previous_response_id"] = previous_response_id
                logger.info(
                    f"🔗 [STREAM] Chaining to previous response: {previous_response_id[:20]}..."
                )
            
            stream = await self.client.responses.create(**api_kwargs)
            
            # Buffers for accumulating content
            full_text = ""
            current_tool_name = ""
            current_tool_args = ""
            current_tool_call_id = ""
            events_processed = 0
            
            async for event in stream:
                events_processed += 1
                event_type = event.type
                
                # Reasoning summary text deltas → "thinking"
                if event_type == "response.reasoning_summary_text.delta":
                    yield {"type": "thinking", "text": event.delta}
                
                # Output text deltas → "text_delta" 
                elif event_type in ("response.output_text.delta", "response.text_delta"):
                    full_text += event.delta
                    yield {"type": "text_delta", "delta": event.delta}
                
                # Function call started — capture name
                elif event_type == "response.output_item.added":
                    if hasattr(event, 'item') and hasattr(event.item, 'type'):
                        if event.item.type == "function_call":
                            current_tool_name = getattr(event.item, 'name', '')
                            current_tool_call_id = getattr(event.item, 'call_id', '')
                            current_tool_args = ""
                            logger.info(
                                f"🔧 [STREAM] Tool call started: {current_tool_name} | "
                                f"call_id={current_tool_call_id}"
                            )
                
                # Function call arguments streaming
                elif event_type == "response.function_call_arguments.delta":
                    current_tool_args += event.delta
                
                # Function call complete → yield tool_call event
                elif event_type == "response.function_call_arguments.done":
                    yield {
                        "type": "tool_call",
                        "call_id": current_tool_call_id,
                        "name": current_tool_name,
                        "arguments": event.arguments if hasattr(event, 'arguments') else current_tool_args,
                    }
                    logger.info(
                        f"✅ [STREAM] Tool call complete: {current_tool_name} | "
                        f"args_len={len(current_tool_args)}"
                    )
                    # Reset buffers
                    current_tool_name = ""
                    current_tool_args = ""
                    current_tool_call_id = ""
                
                # Stream completed
                elif event_type == "response.completed":
                    usage_data = None
                    response_id = None
                    if hasattr(event, 'response'):
                        response_id = getattr(event.response, 'id', None)
                        if hasattr(event.response, 'usage') and event.response.usage:
                            u = event.response.usage
                            usage_data = {
                                "input_tokens": u.input_tokens,
                                "output_tokens": u.output_tokens,
                            }
                            logger.info(
                                f"📊 [LLM Stream Usage] model={self.model_id} "
                                f"input={u.input_tokens} output={u.output_tokens} "
                                f"events_processed={events_processed} | env={settings.ENVIRONMENT}"
                            )
                    
                    yield {
                        "type": "done",
                        "content": full_text,
                        "usage": usage_data,
                        "response_id": response_id,  # For chaining follow-up calls
                    }
                
                # Catch-all: log any unhandled event types for debugging
                elif event_type not in (
                    "response.created", "response.in_progress",
                    "response.output_item.done", "response.content_part.added",
                    "response.content_part.done", "response.reasoning_summary_part.added",
                    "response.reasoning_summary_part.done", "response.reasoning_summary_text.done",
                    "response.output_text.done",
                ):
                    logger.debug(
                        f"🔍 [STREAM] Unhandled event type: {event_type} | "
                        f"events_so_far={events_processed}"
                    )
            
        except Exception as e:
            _tb = traceback.format_exc()
            _msg = (
                f"[{_where}] Stream FAILED after {events_processed if 'events_processed' in dir() else '?'} events | "
                f"{_ctx} | error={str(e)[:300]}"
            )
            logger.error(_msg, exc_info=True)
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title="💥 OpenAI Responses API Stream Error",
                description=(
                    f"**Where:** `{_where}`\n"
                    f"**What:** Streaming failed\n"
                    f"**Model:** {self.model_id}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**History:** {len(message_history)} msgs\n"
                    f"**Effort:** {reasoning_effort}\n"
                    f"**Error:** ```{str(e)[:300]}```\n"
                    f"**Traceback (last 500 chars):** ```{_tb[-500:]}```"
                ),
                severity="error",
                error=e
            )
            yield {"type": "done", "content": f"Error en el sistema de streaming: {str(e)[:100]}", "usage": None}

    def _convert_messages_to_input(
        self, system_prompt: str, message_history: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """Convert Chat Completions message format to Responses API input format.
        
        Chat Completions uses: [{"role": "system", "content": "..."}, {"role": "user", ...}]
        Responses API uses: [{"role": "developer", "content": "..."}, {"role": "user", ...}]
        
        Also handles:
          - Pre-formatted Responses API items (those with a 'type' key)
          - Assistant messages with tool_calls (from agentic loop in use_cases.py)
            → converted to function_call items
          - Tool result messages (role: "tool") → function_call_output items
        
        Key mapping:
          - "system" → "developer" (Responses API renamed this)
          - "assistant" (plain) → "assistant"
          - "assistant" (with tool_calls) → function_call items
          - "user" → "user" 
          - "tool" → function_call_output
          - items with "type" key → passed through as-is
        
        Ref: https://platform.openai.com/docs/api-reference/responses/create
        Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
        """
        input_items = []
        
        # System prompt → developer role
        if system_prompt:
            input_items.append({
                "role": "developer",
                "content": system_prompt,
            })
        
        # Convert message history
        for msg in message_history:
            # If the item already has a 'type' key, it's already in Responses API format
            # (e.g. function_call_output items from tool follow-ups). Pass through directly.
            if "type" in msg:
                input_items.append(msg)
                continue
            
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                # Additional system messages → developer
                input_items.append({"role": "developer", "content": content})
            elif role == "user":
                input_items.append({"role": "user", "content": content})
            elif role == "assistant":
                # ── Assistant messages: two cases ──
                # Case 1: Assistant msg WITH tool_calls (from agentic loop in use_cases.py)
                #   Chat Completions format: {"role": "assistant", "tool_calls": [{"id": ..., "type": "function", "function": {"name": ..., "arguments": ...}}]}
                #   Responses API: each tool_call becomes a separate function_call item
                # Case 2: Plain text assistant message → pass through
                if "tool_calls" in msg and msg["tool_calls"]:
                    # First, add any content the assistant sent alongside tool_calls
                    if content:
                        input_items.append({"role": "assistant", "content": content})
                    # Convert each tool_call to a function_call input item
                    # Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
                    for tc in msg["tool_calls"]:
                        func = tc.get("function", {})
                        call_id = tc.get("id", "")
                        # Support both nested (Chat Completions) and flat formats
                        name = func.get("name", "") if func else tc.get("name", "")
                        arguments = func.get("arguments", "{}") if func else tc.get("arguments", "{}")
                        input_items.append({
                            "type": "function_call",
                            "call_id": call_id,
                            "name": name,
                            "arguments": arguments if isinstance(arguments, str) else json.dumps(arguments),
                        })
                else:
                    input_items.append({"role": "assistant", "content": content})
            elif role == "tool":
                # Tool results → function_call_output format
                # Ref: https://platform.openai.com/docs/guides/function-calling?api-mode=responses
                input_items.append({
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id", ""),
                    "output": content,
                })
            else:
                # Unknown role — log and treat as user to avoid silent drops
                _unk_msg = (
                    f"[_convert_messages_to_input] Unknown message role: '{role}' — "
                    f"treating as user | content_preview={content[:80]}"
                )
                logger.warning(_unk_msg)
                sentry_sdk.capture_message(_unk_msg, level="info")
                input_items.append({"role": "user", "content": content})
        
        return input_items
