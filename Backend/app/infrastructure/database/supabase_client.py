from supabase import create_client, Client
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger

class SupabasePooler:
    """Singleton implementation for Supabase Client to avoid memory leaks across multiple requests."""
    _instance: Client = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            logger.info("Initializing fresh Supabase client connection pool.")
            try:
                cls._instance = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY
                )
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {str(e)}")
                raise
        return cls._instance

def get_db() -> Client:
    """Dependency injection helper for FastAPI."""
    return SupabasePooler.get_client()
