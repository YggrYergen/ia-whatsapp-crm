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
    
    # Block E1: Meta webhook HMAC-SHA256 signature verification
    # Get from: Meta App Dashboard → Settings → Basic → App Secret
    # If None: webhook signature verification is skipped (soft mode, logs warning)
    META_APP_SECRET: str | None = None
    
    # Block E4: Shadow-forward all conversations to admin WhatsApp
    # Full international number without '+', e.g. '56931374341'
    # The FROM phone is dynamic per tenant (uses tenant.ws_phone_id + ws_token)
    SHADOW_FORWARD_PHONE: str | None = None
    
    # Block R: Superadmin emails — comma-separated list of Google emails
    # Users with these emails get is_superadmin=true in profiles table,
    # which grants them read-all RLS policies on all tables + tenant switching.
    # Ref: https://cloud.google.com/run/docs/configuring/environment-variables
    SUPERADMIN_EMAILS: str | None = None
    
    
    PROACTIVE_INTERVAL: int = 3600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
