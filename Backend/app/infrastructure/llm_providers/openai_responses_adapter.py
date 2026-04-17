# ================================================================================
# ⚠️  DOCS FIRST: OpenAI Responses API adapter — side-by-side with openai_adapter.py
#     The existing openai_adapter.py (Chat Completions) is NOT modified.
#     This adapter uses /v1/responses which supports:
#       - reasoning.effort + tools (simultaneously)
#       - Native streaming with typed events
#       - Reasoning summaries
#     Ref: https://platform.openai.com/docs/api-reference/responses
#     Ref: https://platform.openai.com/docs/guides/streaming
#
# ⚠️  ARCHITECTURE: This adapter is used ONLY by the onboarding configuration agent.
#     The WhatsApp pipeline continues to use openai_adapter.py (Chat Completions).
#     Sprint 2: migrate WhatsApp pipeline to this adapter once battle-tested.
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
    
    def __init__(self, api_key: str = None, model_id: str = "gpt-5.4"):
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
        tools: List[Dict[str, Any]],
        tool_choice_override: Optional[Any] = None,
        previous_response_id: Optional[str] = None,
    ) -> LLMResponse:
        """Non-streaming response using Responses API (for compatibility with LLMStrategy interface).
        
        Converts the Chat Completions-style message_history to Responses API input format.
        """
        _where = "OpenAIResponsesStrategy.generate_response"
        _ctx = f"model={self.model_id} | history_len={len(message_history)} | tools={len(tools)} | chain={'→'+previous_response_id[:20] if previous_response_id else 'none'} | env={settings.ENVIRONMENT}"
        
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
        
        # Set Sentry context for this request
        sentry_sdk.set_context("responses_api_request", {
            "model": self.model_id,
            "history_length": len(message_history),
            "tools_count": len(tools),
            "prompt_length": len(system_prompt),
            "environment": settings.ENVIRONMENT,
        })
        
        try:
            # Convert Chat Completions message format → Responses API input format
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            # When chaining, skip system prompt (already in the chain)
            # Ref: https://platform.openai.com/docs/api-reference/responses/create
            effective_system = system_prompt if not previous_response_id else ""
            input_items = self._convert_messages_to_input(effective_system, message_history)
            
            api_kwargs = {
                "model": self.model_id,
                "input": input_items,
                "max_output_tokens": 4096,
                # store=True required for previous_response_id chaining
                # Ref: https://platform.openai.com/docs/api-reference/responses/create
                "store": True,
                # Reasoning config — works WITH tools on Responses API
                "reasoning": {
                    "effort": "medium",
                    "summary": "auto",
                },
            }
            
            # Tools must be re-supplied every request (not inherited from chain)
            # Ref: OpenAI docs confirmed via web search 2026-04-15
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
                        # Unknown format — pass through and let OpenAI error clearly
                        _bad_msg = f"[{_where}] Unknown tool format — no 'function' or 'name' key: {list(t.keys())}"
                        logger.warning(_bad_msg)
                        sentry_sdk.capture_message(_bad_msg, level="warning")
                        converted_tools.append(t)
                api_kwargs["tools"] = converted_tools
            
            # Chain to a previous response (for tool call follow-ups)
            if previous_response_id:
                api_kwargs["previous_response_id"] = previous_response_id
                logger.info(
                    f"🔗 [{_where}] Chaining to previous response: {previous_response_id[:20]}..."
                )
            
            response = await self.client.responses.create(**api_kwargs)
            
            # Guard: response.output could be None or empty
            if not response.output:
                _msg = f"[{_where}] Empty response.output from API | {_ctx}"
                logger.warning(_msg)
                sentry_sdk.capture_message(_msg, level="warning")
                await send_discord_alert(
                    title="⚠️ Empty Responses API Output",
                    description=f"**Where:** `{_where}`\n**What:** response.output is empty/None\n**Context:** {_ctx}",
                    severity="warning"
                )
                return LLMResponse(content="")
            
            # Parse the response output items
            dto = LLMResponse()
            dto.model_used = self.model_id
            dto.response_id = getattr(response, 'id', None)
            
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
            
            # Usage tracking
            try:
                if response.usage:
                    dto.prompt_tokens = response.usage.input_tokens
                    dto.completion_tokens = response.usage.output_tokens
                    logger.info(
                        f"📊 [LLM Usage Responses] model={self.model_id} "
                        f"input={response.usage.input_tokens} output={response.usage.output_tokens} "
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
                    description=f"**Where:** `{_where}`\n**What:** Usage parsing error (response still valid)\n**Error:** {str(usage_err)[:300]}\n**Context:** {_ctx}",
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
        
        Also handles pre-formatted Responses API items (those with a 'type' key,
        e.g. function_call_output) by passing them through unchanged.
        
        Key mapping:
          - "system" → "developer" (Responses API renamed this)
          - "assistant" → "assistant" (same)
          - "user" → "user" (same)
          - "tool" → converted to function_call_output items
          - items with "type" key → passed through as-is
        
        Ref: https://platform.openai.com/docs/api-reference/responses/create
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
                input_items.append({"role": "assistant", "content": content})
            elif role == "tool":
                # Tool results → function_call_output format
                input_items.append({
                    "type": "function_call_output",
                    "call_id": msg.get("tool_call_id", ""),
                    "output": content,
                })
            else:
                # Unknown role — log it, treat as user
                logger.warning(
                    f"[_convert_messages_to_input] Unknown message role: '{role}' — "
                    f"treating as user | content_preview={content[:80]}"
                )
                input_items.append({"role": "user", "content": content})
        
        return input_items
