import asyncio
from fastapi import HTTPException
from supabase import AsyncClient
from app.core.models import TenantContext
from app.infrastructure.telemetry.logger_service import logger
from app.core.exceptions import TenantNotFoundError

async def get_tenant_context_from_payload(payload: dict, db: AsyncClient) -> TenantContext:
    """
    Extracts tenant context based on webhook payload string safely parsed once gracefully.
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
        raise
    except Exception as e:
        logger.error(f"Error extracting context dict: {str(e)}")
        raise HTTPException(status_code=200, detail="Ignored context extract")
