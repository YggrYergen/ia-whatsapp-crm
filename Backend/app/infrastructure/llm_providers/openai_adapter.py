from typing import List, Dict, Any
from app.modules.intelligence.router import LLMStrategy, LLMResponse
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

class OpenAIStrategy(LLMStrategy):
    """OpenAI Adapter parsing response logically into standard DTOs."""
    
    def __init__(self, api_key: str = None, model_id: str = "gpt-4o-mini"):
        key = api_key or settings.OPENAI_API_KEY
        super().__init__(api_key=key, model_id=model_id)
        if AsyncOpenAI: self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_response(self, system_prompt: str, message_history: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> LLMResponse:
        if not AsyncOpenAI:
            return LLMResponse(content="System Setup fault: OpenAI not resolved")
            
        messages = [{"role": "system", "content": system_prompt}] + message_history
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
            message = response.choices[0].message
            
            dto = LLMResponse()
            if message.tool_calls:
                dto.has_tool_calls = True
                dto.tool_calls = [
                    {"id": tool.id, "name": tool.function.name, "arguments": tool.function.arguments}
                    for tool in message.tool_calls
                ]
            else:
                dto.content = message.content or ""
                
            return dto
        except Exception as e:
            logger.error(f"OpenAI Fault: {str(e)}")
            raise
