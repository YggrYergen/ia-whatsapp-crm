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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
