import pytest
from app.core.models import TenantContext

@pytest.fixture
def mock_tenant_context():
    return TenantContext(
        id="tenant_123",
        name="Test Clinic",
        phone_number_id="11223344",
        staff_notification_number="+123456789",
        active_llm_provider="openai",
        active_llm_model="gpt-4o-mini"
    )
