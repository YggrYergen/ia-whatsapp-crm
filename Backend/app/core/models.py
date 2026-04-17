from pydantic import BaseModel, Field
from typing import Optional

class TenantContext(BaseModel):
    id: str
    name: str = ""
    # WhatsApp credentials — only needed for WhatsApp message sending.
    # New tenants from onboarding won't have these until they configure
    # their Meta WABA integration. Everything else (booking, scheduling,
    # CRM dashboard) works without them.
    ws_phone_id: Optional[str] = None
    ws_token: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    system_prompt: str = ""
    is_active: bool = True

