from supabase import create_async_client, AsyncClient
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
import sentry_sdk

class SupabasePooler:
    """Singleton implementation for Supabase Client to avoid memory leaks across multiple requests."""
    _instance: AsyncClient = None

    @classmethod
    async def get_client(cls) -> AsyncClient:
        if cls._instance is None:
            logger.info("Initializing fresh Async Supabase client connection pool.")
            try:
                cls._instance = await create_async_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_SERVICE_ROLE_KEY
                )
            except Exception as e:
                logger.error(f"Failed to initialize Async Supabase client: {str(e)}")
                sentry_sdk.capture_exception(e)
                raise
        return cls._instance

async def get_db() -> AsyncClient:
    """Dependency injection helper for FastAPI."""
    return await SupabasePooler.get_client()

# Alias for legacy or mismatched imports in other modules
get_supabase_client = get_db
