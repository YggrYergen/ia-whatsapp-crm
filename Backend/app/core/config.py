# ================================================================================
# ⚠️  DOCS FIRST: Antes de modificar configuración o agregar variables de entorno,
#     consultar la documentación oficial del servicio correspondiente.
#     - Sentry DSN: https://docs.sentry.io/platforms/python/integrations/fastapi/
#     - Cloud Run env vars: https://cloud.google.com/run/docs/configuring/environment-variables
#     - Supabase keys: https://supabase.com/docs/guides/api/api-keys
# ================================================================================
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
    
    # Sentry DSN — https://docs.sentry.io/platforms/python/integrations/fastapi/
    # Configured as env var in Cloud Run. Falls back to None which disables Sentry.
    SENTRY_DSN: str | None = None
    
    GOOGLE_SERVICE_ACCOUNT_JSON: str | None = None
    GOOGLE_OAUTH_CLIENT_ID: str | None = None
    GOOGLE_OAUTH_CLIENT_SECRET: str | None = None
    GOOGLE_OAUTH_REDIRECT_URI: str | None = None
    
    PROACTIVE_INTERVAL: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
