from typing import List, Dict, Any
from app.modules.intelligence.router import LLMStrategy, LLMResponse

class MockStrategy(LLMStrategy):
    """Bypass REAL LLM for internal testing cycles."""
    
    def __init__(self, api_key: str = None, model_id: str = "mock"):
        super().__init__(api_key="mock", model_id=model_id)

    async def generate_response(self, system_prompt: str, message_history: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> LLMResponse:
        # Just echo or simple response
        last_user_msg = message_history[-1]['content'] if message_history else ""
        return LLMResponse(content=f"MOCK RESPONSE: He recibido tu mensaje: '{last_user_msg}'. La lógica de Mutex Lock y Contexto funciona correctamente.")
