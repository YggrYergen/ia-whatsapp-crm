from pydantic import BaseModel, Field

class TenantContext(BaseModel):
    id: str
    name: str = ""
    ws_phone_id: str
    ws_token: str = ""
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    system_prompt: str = ""
    is_active: bool = True
