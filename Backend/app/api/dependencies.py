# ================================================================================
# ⚠️  DOCS FIRST: Tenant Context Resolution
#     Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks#payload-structure
#
# ⚠️  OBSERVABILITY: Every error path reports to Sentry + Discord (§6).
#
# Block E6: TTLCache for tenant config — avoids redundant DB queries.
#     Ref: https://pypi.org/project/cachetools/
#     Cache key: ws_phone_id (unique per tenant WABA phone)
#     TTL: 180 seconds (3 minutes)
#     Max: 50 tenants (~250KB, negligible vs 512MB Cloud Run limit)
# ================================================================================
import asyncio
from fastapi import HTTPException
from supabase import AsyncClient
from cachetools import TTLCache
import sentry_sdk

from app.core.models import TenantContext
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.core.exceptions import TenantNotFoundError

# Block E6: Tenant config cache — 3 minute TTL, 50 tenant max
# This is a simple in-memory dict. In Cloud Run with single instance, this is shared
# across all requests. Each cold start resets the cache (acceptable).
# Thread safety: Python GIL + single async event loop = no lock needed.
_tenant_cache: TTLCache = TTLCache(maxsize=50, ttl=180)


def invalidate_tenant_cache(phone_id: str | None = None) -> None:
    """
    Invalidate tenant config cache.
    If phone_id is given, only that entry is removed.
    If None, clears entire cache.
    """
    if phone_id and phone_id in _tenant_cache:
        del _tenant_cache[phone_id]
        logger.info(f"🗑️ [CACHE] Invalidated tenant cache for phone_id={phone_id}")
    elif phone_id is None:
        _tenant_cache.clear()
        logger.info("🗑️ [CACHE] Entire tenant cache cleared")


async def get_tenant_context_from_payload(payload: dict, db: AsyncClient) -> TenantContext:
    """
    Extracts tenant context based on webhook payload string safely parsed once gracefully.
    
    OBSERVABILITY: Every error path reports to Sentry + Discord.
    CACHING: Uses TTLCache to avoid redundant DB queries (Block E6).
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
        
        # Block E6: Check cache first
        cached_tenant = _tenant_cache.get(phone_id)
        if cached_tenant is not None:
            logger.debug(f"⚡ [CACHE] Tenant cache HIT for phone_id={phone_id}")
            return cached_tenant
        
        logger.debug(f"🔍 [CACHE] Tenant cache MISS for phone_id={phone_id} — querying DB")
            
        try:
            response = await db.table("tenants").select("*").eq("ws_phone_id", phone_id).execute()
        except Exception as db_err:
            logger.error(f"❌ [DEP] Tenant DB query failed: {db_err}")
            sentry_sdk.capture_exception(db_err)
            await send_discord_alert(
                title="❌ Tenant DB Query Failed",
                description=f"Failed to query tenants table for phone_id={phone_id}: {str(db_err)[:300]}",
                severity="error", error=db_err
            )
            raise HTTPException(status_code=200, detail="DB query failed for tenant lookup")
        
        if not response.data:
            logger.warning(f"Tenant Context missing for internal phone_id mapping: {phone_id}")
            raise TenantNotFoundError(f"Tenant Context not found: {phone_id}")
        
        tenant = TenantContext(**response.data[0])
        
        # Store in cache for future requests
        try:
            _tenant_cache[phone_id] = tenant
            logger.debug(f"💾 [CACHE] Tenant cached for phone_id={phone_id} (TTL=180s, size={len(_tenant_cache)})")
        except Exception as cache_err:
            # Cache storage failure is non-fatal — just log it
            logger.error(f"❌ [CACHE] Failed to cache tenant: {cache_err}")
            sentry_sdk.capture_exception(cache_err)
        
        return tenant
        
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
