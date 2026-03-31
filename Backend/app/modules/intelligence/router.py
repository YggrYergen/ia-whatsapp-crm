from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List
from app.infrastructure.telemetry.logger_service import logger
from app.core.models import TenantContext
from app.core.exceptions import ProviderNotRegisteredError

class LLMResponse(BaseModel):
    """Data Transfer Object explicit definition bounding inference return payloads safely."""
    content: str = ""
    has_tool_calls: bool = False
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)

class LLMStrategy(ABC):
    def __init__(self, api_key: str, model_id: str):
        self.api_key = api_key
        self.model_id = model_id
        
    @abstractmethod
    async def generate_response(
        self, 
        system_prompt: str, 
        message_history: List[Dict[str, str]], 
        tools: List[Dict[str, Any]]
    ) -> LLMResponse:
        pass

class LLMFactory:
    _strategies: Dict[str, Type[LLMStrategy]] = {}

    @classmethod
    def register_strategy(cls, provider_name: str, strategy_class: Type[LLMStrategy]):
        cls._strategies[provider_name] = strategy_class

    @classmethod
    def create(cls, tenant_context: TenantContext, overriding_api_key: str = None) -> LLMStrategy:
        provider = tenant_context.llm_provider
        strategy_class = cls._strategies.get(provider)
        
        if not strategy_class:
            raise ProviderNotRegisteredError(f"Provider {provider} not assigned globally.")
            
        model = tenant_context.llm_model
        return strategy_class(api_key=overriding_api_key, model_id=model)
