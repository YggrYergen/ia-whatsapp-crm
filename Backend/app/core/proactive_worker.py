import asyncio
import pytz
from datetime import datetime, timedelta
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.core.config import settings
import httpx

class ProactiveWorker:
    def __init__(self, interval_seconds: int = 3600):
        self.interval = interval_seconds
        self.is_running = False

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        logger.info(f"🚀 Proactive Worker started (Interval: {self.interval}s)")
        
        while self.is_running:
            try:
                await self.process_tasks()
            except httpx.ConnectError:
                logger.warning("⚠️ Proactive Worker: Temporary network connection issue to DB ignored. Retrying next tick.")
            except Exception as e:
                logger.error(f"❌ Error in Proactive Worker loop: {e}", exc_info=True)
            await asyncio.sleep(self.interval)

    async def process_tasks(self):
        logger.info("Checking for proactive tasks...")
        db = SupabasePooler.get_client()
        chile_tz = pytz.timezone("America/Santiago")
        now = datetime.now(chile_tz)

        # 1. Reminders (Example: -24h)
        # 2. Post-appointment (Example: +24h)
        # 3. Re-engagement (Example: 30 days inactive)
        
        # --- Simplified Re-engagement Example ---
        thirty_days_ago = (now - timedelta(days=30)).isoformat()
        
        # Get tenants to process
        tenants_res = await asyncio.to_thread(lambda: db.table("tenants").select("*").eq("is_active", True).execute())
        
        for tenant_data in tenants_res.data:
            # Get inactive contacts
            # Note: This is an architectural stub. Realistic implementation needs a dedicated 'tasks' table or more complex queries.
            pass

    def stop(self):
        self.is_running = False
        logger.info("Proactive Worker stopping...")

proactive_worker = ProactiveWorker(interval_seconds=settings.PROACTIVE_INTERVAL if hasattr(settings, 'PROACTIVE_INTERVAL') else 3600)
