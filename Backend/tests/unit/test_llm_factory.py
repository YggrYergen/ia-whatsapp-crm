import pytest
from app.modules.intelligence.router import LLMFactory, LLMStrategy
from app.core.models import TenantContext
from app.core.exceptions import ProviderNotRegisteredError

class MockStrategy(LLMStrategy):
    async def generate_response(self, system_prompt, message_history, tools):
        return "mocked_response"

def test_factory_instantiation(mock_tenant_context):
    LLMFactory.register_strategy("openai", MockStrategy)
    
    strategy = LLMFactory.create(tenant_context=mock_tenant_context, overriding_api_key="mocked_key")
    
    assert isinstance(strategy, MockStrategy)
    assert strategy.model_id == "gpt-4o-mini"
    assert strategy.api_key == "mocked_key"

def test_factory_not_registered(mock_tenant_context):
    mock_tenant_context.active_llm_provider = "unregistered_provider"
    with pytest.raises(ProviderNotRegisteredError):
        LLMFactory.create(tenant_context=mock_tenant_context)
