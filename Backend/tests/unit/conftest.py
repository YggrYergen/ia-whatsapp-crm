import pytest
from app.core.models import TenantContext

@pytest.fixture
def mock_tenant_context():
    return TenantContext(
        id="tenant_123",
        name="Test Clinic",
        ws_phone_id="11223344",
        ws_token="mock_token",
        llm_provider="openai",
        llm_model="gpt-5.4-mini"
    )
