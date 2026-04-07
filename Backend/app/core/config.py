from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "DEBUG" 
    MOCK_LLM: bool = False
    
    WHATSAPP_VERIFY_TOKEN: str
    OPENAI_API_KEY: str
    GEMINI_API_KEY: str
    
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    DISCORD_WEBHOOK_URL: str | None = None
    RESEND_API_KEY: str | None = None
    
    PROACTIVE_INTERVAL: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
