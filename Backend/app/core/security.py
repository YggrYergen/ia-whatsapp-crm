from fastapi import Query, HTTPException
from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger

async def verify_whatsapp_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """Dependency to verify Meta Webhook validation requests upon subscribing."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp Webhook verification successful.")
        return int(hub_challenge)
    
    logger.warning("WhatsApp Webhook verification failed due to invalid token or mode.")
    raise HTTPException(status_code=403, detail="Verification failed")
