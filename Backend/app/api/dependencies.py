import asyncio
from fastapi import HTTPException
from supabase import AsyncClient
import sentry_sdk
from app.core.models import TenantContext
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.core.exceptions import TenantNotFoundError

async def get_tenant_context_from_payload(payload: dict, db: AsyncClient) -> TenantContext:
    """
    Extracts tenant context based on webhook payload string safely parsed once gracefully.
    
    OBSERVABILITY: Every error path reports to Sentry + Discord.
    """
    try:
        if "entry" not in payload or not payload["entry"]:
            raise ValueError("No entry array found.")
            
        entry = payload["entry"][0]
        if "changes" not in entry or not entry["changes"]:
            raise ValueError("No changes found.")
            
        value = entry["changes"][0]["value"]
        
        if "metadata" not in value or "phone_number_id" not in value["metadata"]:
            raise ValueError("No phone_number_id found in metadata.")
            
        phone_id = value["metadata"]["phone_number_id"]
            
        response = await db.table("tenants").select("*").eq("ws_phone_id", phone_id).execute()
        
        if not response.data:
            logger.warning(f"Tenant Context missing for internal phone_id mapping: {phone_id}")
            raise TenantNotFoundError(f"Tenant Context not found: {phone_id}")
            
        return TenantContext(**response.data[0])
        
    except TenantNotFoundError:
        sentry_sdk.capture_message(f"Tenant not found for phone_id in payload", level="warning")
        await send_discord_alert(
            title="⚠️ Tenant Not Found",
            description=f"Webhook received for unknown phone_number_id. Payload may be from an unregistered number.",
            severity="warning"
        )
        raise
    except Exception as e:
        logger.error(f"Error extracting context dict: {str(e)}")
        sentry_sdk.set_context("webhook_payload", {"payload_keys": list(payload.keys()) if isinstance(payload, dict) else "not_a_dict"})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="❌ Webhook Payload Parse Error",
            description=f"Failed to extract tenant context from webhook payload: {str(e)[:300]}",
            severity="error",
            error=e
        )
        raise HTTPException(status_code=200, detail="Ignored context extract")
