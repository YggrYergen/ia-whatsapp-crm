"""
Scheduling Config API — /api/scheduling-config endpoints.

Provides GET/PUT for tenant scheduling configuration (business hours, duration, buffer, etc.).
Configuration is tenant-scoped via the scheduling_config table.

Observability: Every except block → logger + Sentry + Discord (3-channel observability).

Docs-first references:
  - scheduling_config table schema: native_calendar_plan.md §2
"""

import datetime
import sentry_sdk
from fastapi import APIRouter, Body

from app.core.config import settings
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger

router = APIRouter(prefix="/api/scheduling-config", tags=["scheduling-config"])

_WHERE = "scheduling_config_api"

# Default business hours — used when no config exists
DEFAULT_BUSINESS_HOURS = {
    "monday":    {"open": "09:00", "close": "19:00", "enabled": True},
    "tuesday":   {"open": "09:00", "close": "19:00", "enabled": True},
    "wednesday": {"open": "09:00", "close": "19:00", "enabled": True},
    "thursday":  {"open": "09:00", "close": "19:00", "enabled": True},
    "friday":    {"open": "09:00", "close": "19:00", "enabled": True},
    "saturday":  {"open": "09:00", "close": "14:00", "enabled": True},
    "sunday":    {"open": "09:00", "close": "14:00", "enabled": False},
}


@router.get("")
async def get_scheduling_config(tenant_id: str):
    """Get the scheduling configuration for a tenant. Creates a default if none exists."""
    _where = f"{_WHERE}.get_config"
    _ctx = f"tenant={tenant_id} | env={settings.ENVIRONMENT}"
    try:
        db = await SupabasePooler.get_client()
        res = await db.table("scheduling_config").select("*").eq("tenant_id", tenant_id).maybe_single().execute()

        if res.data:
            logger.info(f"[{_where}] Loaded existing config | {_ctx}")
            return {"status": "success", "config": res.data}

        # Auto-create default config for this tenant
        try:
            default_config = {
                "tenant_id": tenant_id,
                "business_hours": DEFAULT_BUSINESS_HOURS,
                "default_duration_minutes": 30,
                "buffer_between_appointments": 0,
                "timezone": "America/Santiago",
                "round_robin_enabled": True,
                "metadata": {},
            }
            new_res = await db.table("scheduling_config").insert(default_config).execute()
            if new_res.data:
                logger.info(f"✅ [{_where}] Auto-created default config | {_ctx}")
                return {"status": "success", "config": new_res.data[0], "auto_created": True}
        except Exception as create_err:
            logger.error(f"[{_where}] Auto-create config failed | {_ctx} | error={str(create_err)[:200]}", exc_info=True)
            sentry_sdk.capture_exception(create_err)
            await send_discord_alert(
                title=f"⚠️ Scheduling Config Auto-Create Failed | Tenant {tenant_id}",
                description=f"**Where:** `{_where}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(create_err)[:300]}```",
                severity="warning", error=create_err,
            )

        # Fallback: return defaults even if DB write failed
        return {
            "status": "success",
            "config": {
                "tenant_id": tenant_id,
                "business_hours": DEFAULT_BUSINESS_HOURS,
                "default_duration_minutes": 30,
                "buffer_between_appointments": 0,
                "timezone": "America/Santiago",
                "round_robin_enabled": True,
            },
            "fallback": True,
        }

    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("scheduling_config_get", {"tenant_id": tenant_id, "environment": settings.ENVIRONMENT})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Get Scheduling Config Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error loading scheduling config: {str(e)}"}


@router.put("")
async def update_scheduling_config(payload: dict = Body(...)):
    """Update scheduling configuration for a tenant."""
    _where = f"{_WHERE}.update_config"
    tenant_id = payload.get("tenant_id", "")
    _ctx = f"tenant={tenant_id} | env={settings.ENVIRONMENT}"
    try:
        if not tenant_id:
            return {"status": "error", "message": "tenant_id is required."}

        db = await SupabasePooler.get_client()

        # Validate business_hours structure if provided
        bh = payload.get("business_hours")
        if bh is not None:
            valid_days = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
            if not isinstance(bh, dict):
                return {"status": "error", "message": "business_hours must be an object with day keys."}
            for day, config in bh.items():
                if day not in valid_days:
                    return {"status": "error", "message": f"Día inválido: {day}"}
                if not isinstance(config, dict) or "open" not in config or "close" not in config or "enabled" not in config:
                    return {"status": "error", "message": f"Configuración inválida para {day}. Requiere open, close, enabled."}

        # Validate numeric fields
        duration = payload.get("default_duration_minutes")
        if duration is not None:
            try:
                duration = int(duration)
                if duration <= 0:
                    return {"status": "error", "message": "La duración debe ser mayor a 0."}
            except (ValueError, TypeError):
                return {"status": "error", "message": "Duración inválida."}

        buffer = payload.get("buffer_between_appointments")
        if buffer is not None:
            try:
                buffer = int(buffer)
                if buffer < 0:
                    return {"status": "error", "message": "El buffer no puede ser negativo."}
            except (ValueError, TypeError):
                return {"status": "error", "message": "Buffer inválido."}

        # Build update
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        update_data = {"updated_at": now_iso}
        allowed_fields = [
            "business_hours", "default_duration_minutes", "buffer_between_appointments",
            "timezone", "round_robin_enabled", "metadata",
        ]
        for field in allowed_fields:
            if field in payload:
                update_data[field] = payload[field]

        # Upsert: update if exists, insert if not
        existing = await db.table("scheduling_config").select("id").eq("tenant_id", tenant_id).maybe_single().execute()

        if existing.data:
            res = await db.table("scheduling_config").update(update_data).eq("tenant_id", tenant_id).execute()
        else:
            update_data["tenant_id"] = tenant_id
            res = await db.table("scheduling_config").insert(update_data).execute()

        if not res.data:
            logger.warning(f"[{_where}] No rows updated/inserted | {_ctx}")
            return {"status": "error", "message": "Error al guardar configuración."}

        logger.info(f"✅ [{_where}] Config saved | {_ctx} | fields={list(update_data.keys())}")
        return {"status": "success", "config": res.data[0]}

    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("scheduling_config_update", {
            "tenant_id": tenant_id, "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Update Scheduling Config Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error saving config: {str(e)}"}
