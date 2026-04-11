from typing import List, Dict, Any, Optional
from app.modules.intelligence.router import LLMStrategy, LLMResponse
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
import sentry_sdk

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

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
                # A6: Cost cap — limit output tokens per response
                # At $4.50/1M output tokens, 500 tokens ≈ $0.00225/response max
                "max_completion_tokens": 500,
            }
            if tools:
                api_kwargs["tools"] = tools
                api_kwargs["tool_choice"] = tool_choice
                # B1: Disable parallel tool calls — required for strict: true schemas
                # Ref: OpenAI Structured Outputs docs — strict mode incompatible with parallel calls
                api_kwargs["parallel_tool_calls"] = False
            
            response = await self.client.chat.completions.create(**api_kwargs)
            message = response.choices[0].message
            
            # C1: ALWAYS preserve text content — content and tool_calls can coexist
            # Per OpenAI docs: the model may provide explanatory text alongside tool calls.
            # Previously this was an if/else that silently discarded content when tool_calls existed.
            dto = LLMResponse()
            dto.content = message.content or ""
            
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
