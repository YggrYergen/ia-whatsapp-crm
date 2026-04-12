from typing import List, Dict, Any, Optional
from app.modules.intelligence.router import LLMStrategy, LLMResponse
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
import sentry_sdk

try:
    from openai import AsyncOpenAI, BadRequestError
except ImportError:
    AsyncOpenAI = None
    BadRequestError = None

class OpenAIStrategy(LLMStrategy):
    """OpenAI Adapter parsing response logically into standard DTOs.
    
    Per OpenAI Function Calling docs:
    - tool_choice="auto" → LLM decides whether to call tools (default)
    - tool_choice="required" → LLM MUST call at least one tool
    - tool_choice={"type": "function", "function": {"name": "X"}} → force specific tool
    Ref: https://platform.openai.com/docs/guides/function-calling
    """
    
    def __init__(self, api_key: str = None, model_id: str = "gpt-5.4-mini"):
        key = api_key or settings.OPENAI_API_KEY
        super().__init__(api_key=key, model_id=model_id)
        # Step 5: reasoning_effort experiment flag.
        # Starts True — if API rejects the param, flips to False permanently
        # for this instance's lifetime. Prevents retrying a known-bad param.
        self._reasoning_supported = True
        if AsyncOpenAI:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.error("[OpenAIStrategy] openai package not installed — LLM calls will fail")
            sentry_sdk.capture_message("OpenAI SDK not installed — AsyncOpenAI is None", level="error")

    async def generate_response(
        self, 
        system_prompt: str, 
        message_history: List[Dict[str, str]], 
        tools: List[Dict[str, Any]],
        tool_choice_override: Optional[Any] = None
    ) -> LLMResponse:
        if not AsyncOpenAI or not self.client:
            logger.error("[OpenAIStrategy] Cannot generate response — openai package not installed")
            sentry_sdk.capture_message("OpenAI generate_response called but SDK not available", level="error")
            await send_discord_alert(
                title="💥 OpenAI SDK Missing",
                description="generate_response() called but openai package is not installed. All LLM calls are failing.",
                severity="error"
            )
            return LLMResponse(content="Error interno del sistema. Por favor intenta de nuevo.")
            
        messages = [{"role": "system", "content": system_prompt}] + message_history
        
        # Determine tool_choice:
        # - If override provided (e.g. force_escalation), use it
        # - Otherwise default to "auto" per OpenAI best practices
        # Ref: https://platform.openai.com/docs/guides/function-calling
        if tools:
            tool_choice = tool_choice_override if tool_choice_override else "auto"
        else:
            tool_choice = None
        
        try:
            # Build API kwargs — parallel_tool_calls must be OMITTED (not null)
            # when no tools are present. OpenAI API rejects null for this param.
            # Ref: https://platform.openai.com/docs/api-reference/chat/create
            api_kwargs = {
                "model": self.model_id,
                "messages": messages,
                # Block I: Raised from 500 → 2048 (April 12 2026 incident)
                # 500 tokens was truncating BOTH text responses AND tool_calls JSON.
                # Truncated tool_calls = corrupt JSON → doom loop of parse failures.
                # 2048 is 0.0016% of gpt-5.4-mini's 128K output capacity.
                # Cost: you pay for TOKENS GENERATED, not the cap.
                # At $4.50/1M output tokens: 2048 tokens = ~$0.009/response MAX.
                # Average WhatsApp response is 50-150 tokens = ~$0.0004-0.0007 actual.
                # Ref: https://platform.openai.com/docs/api-reference/chat/create
                "max_completion_tokens": 2048,
                # Block I: Anti-repetition penalties (BUG-A broken record fix)
                # frequency_penalty: penalizes tokens proportional to how often they
                # appear in the output so far. 0.3 = mild bias against repetition.
                # presence_penalty: penalizes tokens that have appeared at all.
                # 0.3 = mild encouragement to introduce new topics.
                # Ref: https://platform.openai.com/docs/api-reference/chat/create
                "frequency_penalty": 0.3,
                "presence_penalty": 0.3,
            }
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["tool_choice"] = tool_choice
                # B1: Disable parallel tool calls — required for strict: true schemas
                # Ref: OpenAI Structured Outputs docs — strict mode incompatible with parallel calls
                api_kwargs["parallel_tool_calls"] = False
            
            # Step 5 (Apr 12): reasoning_effort experiment
            # gpt-5.4-mini defaults to reasoning_effort="none" — zero internal reasoning.
            # This caused shallow responses: template parroting, no conversational pacing.
            # Setting to "medium" adds ~300ms latency but enables actual multi-step thinking.
            # Ref: https://platform.openai.com/docs/api-reference/chat/create
            # 
            # SAFETY: Conflicting docs on whether gpt-5.4-mini supports this param.
            # Some sources confirm support; others warn it may error for "non-reasoning models".
            # Strategy: try with param first → if API rejects (BadRequestError), retry without.
            # The _reasoning_supported flag prevents retrying the param on every call after
            # the first failure — fail once, learn, never try again for this instance's lifetime.
            if self._reasoning_supported:
                api_kwargs["reasoning_effort"] = "medium"
            
            try:
                response = await self.client.chat.completions.create(**api_kwargs)
            except (BadRequestError, Exception) as reasoning_err:
                # Step 5 safety net: if reasoning_effort caused the error, retry without it
                if "reasoning_effort" in api_kwargs and (
                    "reasoning_effort" in str(reasoning_err).lower()
                    or "reasoning" in str(reasoning_err).lower()
                ):
                    self._reasoning_supported = False
                    logger.warning(
                        f"⚠️ [LLM] reasoning_effort rejected by API for model={self.model_id}. "
                        f"Disabling for this instance. Error: {str(reasoning_err)[:200]}"
                    )
                    sentry_sdk.capture_message(
                        f"reasoning_effort unsupported for {self.model_id} — disabling",
                        level="warning"
                    )
                    await send_discord_alert(
                        title=f"⚠️ reasoning_effort Unsupported | {self.model_id}",
                        description=(
                            f"API rejected reasoning_effort param. Retrying without it.\n"
                            f"Error: {str(reasoning_err)[:200]}"
                        ),
                        severity="warning"
                    )
                    del api_kwargs["reasoning_effort"]
                    response = await self.client.chat.completions.create(**api_kwargs)
                else:
                    raise  # Re-raise if the error is NOT about reasoning_effort
            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason  # "stop", "length", "tool_calls", etc.
            
            # C1: ALWAYS preserve text content — content and tool_calls can coexist
            # Per OpenAI docs: the model may provide explanatory text alongside tool calls.
            # Previously this was an if/else that silently discarded content when tool_calls existed.
            dto = LLMResponse()
            dto.content = message.content or ""
            dto.finish_reason = finish_reason
            
            # Block I: Truncation detection — CRITICAL for preventing doom loops
            # If finish_reason="length", the output was cut off by max_completion_tokens.
            # This means:
            #   - Text responses are incomplete (cut mid-sentence)
            #   - tool_calls JSON arguments may be CORRUPT (truncated JSON)
            # The agentic loop MUST check was_truncated before executing tool_calls.
            # Ref: https://platform.openai.com/docs/api-reference/chat/object
            if finish_reason == "length":
                dto.was_truncated = True
                logger.warning(
                    f"⚠️ [LLM] Response TRUNCATED (finish_reason=length) | "
                    f"model={self.model_id} | has_tool_calls={bool(message.tool_calls)} | "
                    f"content_len={len(dto.content)}"
                )
                sentry_sdk.set_context("llm_truncation", {
                    "model": self.model_id,
                    "finish_reason": finish_reason,
                    "has_tool_calls": bool(message.tool_calls),
                    "content_length": len(dto.content),
                    "content_preview": dto.content[:200],
                })
                sentry_sdk.capture_message(
                    f"LLM response truncated (finish_reason=length) | model={self.model_id}",
                    level="warning"
                )
                await send_discord_alert(
                    title=f"⚠️ LLM Response Truncated | {self.model_id}",
                    description=(
                        f"finish_reason=length — output hit max_completion_tokens cap.\n"
                        f"has_tool_calls={bool(message.tool_calls)}\n"
                        f"content_preview: {dto.content[:150]}..."
                    ),
                    severity="warning"
                )
            
            if message.tool_calls:
                dto.has_tool_calls = True
                dto.tool_calls = [
                    {"id": tool.id, "name": tool.function.name, "arguments": tool.function.arguments}
                    for tool in message.tool_calls
                ]
            
            # C2: Populate usage tracking fields from response.usage
            # Wrapped in its own try/except so usage parsing failure doesn't
            # kill the valid LLM response (content + tool_calls)
            try:
                usage = response.usage
                if usage:
                    dto.prompt_tokens = usage.prompt_tokens
                    dto.completion_tokens = usage.completion_tokens
                    dto.model_used = response.model
                    # Nested details — may be None depending on model/request
                    prompt_details = getattr(usage, 'prompt_tokens_details', None)
                    completion_details = getattr(usage, 'completion_tokens_details', None)
                    dto.cached_tokens = getattr(prompt_details, 'cached_tokens', None) if prompt_details else None
                    dto.reasoning_tokens = getattr(completion_details, 'reasoning_tokens', None) if completion_details else None
                    
                    logger.info(
                        f"📊 [LLM Usage] model={response.model} "
                        f"prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
                        f"cached={dto.cached_tokens or 0} reasoning={dto.reasoning_tokens or 0}"
                    )
            except Exception as usage_err:
                # Usage parsing failed but the LLM response is still valid — don't crash
                logger.warning(f"[OpenAIStrategy] Usage parsing failed (non-fatal): {usage_err}")
                sentry_sdk.capture_exception(usage_err)
                await send_discord_alert(
                    title="⚠️ OpenAI Usage Parsing Failed",
                    description=f"Usage tracking failed (response still valid): {str(usage_err)[:300]}",
                    severity="warning"
                )
                
            return dto
        except Exception as e:
            logger.error(f"OpenAI Fault: {str(e)}")
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title="💥 OpenAI LLM Error",
                description=f"OpenAI inference failed (model={self.model_id}): {str(e)[:300]}",
                severity="error",
                error=e
            )
            raise
