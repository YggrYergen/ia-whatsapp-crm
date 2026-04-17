"""
Services CRUD API — /api/services endpoints.

Provides tenant-scoped CRUD for the service/product catalog.
Changes here flow to the AI assistant in real-time because the prompt
is assembled fresh from DB on every incoming WhatsApp message.

Observability: Every except block reports through 3 channels:
  1. logger.error() with full context
  2. sentry_sdk.capture_exception() with structured context
  3. send_discord_alert() with severity + traceback

Docs-first references:
  - Supabase Python client: https://supabase.com/docs/reference/python/select
  - FastAPI Body: https://fastapi.tiangolo.com/tutorial/body/
"""

import datetime
import sentry_sdk
from fastapi import APIRouter, Body, Request

from app.core.config import settings
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger

router = APIRouter(prefix="/api/services", tags=["services"])

_WHERE = "services_api"


@router.get("")
async def list_services(tenant_id: str, include_inactive: bool = False):
    """List all services for a tenant. Active-only by default."""
    _where = f"{_WHERE}.list_services"
    _ctx = f"tenant={tenant_id} | include_inactive={include_inactive} | env={settings.ENVIRONMENT}"
    try:
        db = await SupabasePooler.get_client()
        query = db.table("tenant_services").select("*").eq("tenant_id", tenant_id)
        if not include_inactive:
            query = query.eq("is_active", True)
        res = await query.order("sort_order").execute()
        logger.info(f"[{_where}] Listed {len(res.data or [])} services | {_ctx}")
        return {"status": "success", "services": res.data or []}
    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("services_list", {"tenant_id": tenant_id, "environment": settings.ENVIRONMENT})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ List Services Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error listing services: {str(e)}", "services": []}


@router.post("")
async def create_service(payload: dict = Body(...)):
    """Create a new service for a tenant."""
    _where = f"{_WHERE}.create_service"
    tenant_id = payload.get("tenant_id", "")
    service_name = payload.get("name", "")
    _ctx = f"tenant={tenant_id} | service={service_name} | env={settings.ENVIRONMENT}"
    try:
        if not tenant_id or not service_name:
            return {"status": "error", "message": "tenant_id and name are required."}

        # Validate price
        price = payload.get("price")
        if price is not None:
            try:
                price = int(price)
                if price < 0:
                    return {"status": "error", "message": "El precio no puede ser negativo."}
            except (ValueError, TypeError) as val_err:
                logger.warning(f"[{_where}] Invalid price value: {payload.get('price')} | {_ctx}")
                sentry_sdk.capture_message(f"Invalid price in create_service: {payload.get('price')}", level="warning")
                return {"status": "error", "message": "Precio inválido. Debe ser un número entero."}

        # Validate duration
        duration = payload.get("duration_minutes")
        if duration is not None:
            try:
                duration = int(duration)
                if duration <= 0:
                    return {"status": "error", "message": "La duración debe ser mayor a 0."}
            except (ValueError, TypeError):
                logger.warning(f"[{_where}] Invalid duration: {payload.get('duration_minutes')} | {_ctx}")
                return {"status": "error", "message": "Duración inválida. Debe ser un número entero positivo."}

        db = await SupabasePooler.get_client()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = {
            "tenant_id": tenant_id,
            "name": service_name.strip(),
            "description": (payload.get("description") or "").strip() or None,
            "price": price,
            "price_is_variable": payload.get("price_is_variable", False),
            "duration_minutes": duration,
            "is_active": payload.get("is_active", True),
            "sort_order": payload.get("sort_order", 0),
            "updated_at": now_iso,
        }

        res = await db.table("tenant_services").insert(data).execute()

        if not res.data:
            logger.error(f"[{_where}] INSERT returned no data | {_ctx}")
            sentry_sdk.capture_message(f"tenant_services INSERT empty response | {_ctx}", level="error")
            await send_discord_alert(
                title=f"⚠️ Create Service Empty Response | Tenant {tenant_id}",
                description=f"**Where:** `{_where}`\n**Service:** {service_name}\n**Env:** {settings.ENVIRONMENT}",
                severity="error",
            )
            return {"status": "error", "message": "Error creating service."}

        logger.info(f"✅ [{_where}] Created service '{service_name}' | id={res.data[0]['id']} | {_ctx}")
        return {"status": "success", "service": res.data[0]}

    except Exception as e:
        err_str = str(e)
        # Handle unique constraint violation
        if "duplicate" in err_str.lower() or "unique" in err_str.lower():
            logger.warning(f"[{_where}] Duplicate service name: '{service_name}' | {_ctx}")
            return {"status": "error", "message": f"Ya existe un servicio con el nombre '{service_name}'."}

        logger.error(f"[{_where}] Failed | {_ctx} | error={err_str[:300]}", exc_info=True)
        sentry_sdk.set_context("services_create", {
            "tenant_id": tenant_id, "service_name": service_name,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Create Service Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Service:** {service_name}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{err_str[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error creating service: {err_str}"}


@router.put("/{service_id}")
async def update_service(service_id: str, payload: dict = Body(...)):
    """Update an existing service."""
    _where = f"{_WHERE}.update_service"
    tenant_id = payload.get("tenant_id", "")
    _ctx = f"tenant={tenant_id} | service_id={service_id} | env={settings.ENVIRONMENT}"
    try:
        if not tenant_id:
            return {"status": "error", "message": "tenant_id is required."}

        db = await SupabasePooler.get_client()

        # Build update dict — only include fields that were provided
        update_data = {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        allowed_fields = ["name", "description", "price", "price_is_variable", "duration_minutes", "is_active", "sort_order"]
        for field in allowed_fields:
            if field in payload:
                val = payload[field]
                # Validate price
                if field == "price" and val is not None:
                    try:
                        val = int(val)
                        if val < 0:
                            return {"status": "error", "message": "El precio no puede ser negativo."}
                    except (ValueError, TypeError):
                        return {"status": "error", "message": "Precio inválido."}
                # Validate duration
                if field == "duration_minutes" and val is not None:
                    try:
                        val = int(val)
                        if val <= 0:
                            return {"status": "error", "message": "La duración debe ser mayor a 0."}
                    except (ValueError, TypeError):
                        return {"status": "error", "message": "Duración inválida."}
                # Strip strings
                if isinstance(val, str):
                    val = val.strip()
                update_data[field] = val

        res = await db.table("tenant_services").update(update_data).eq("id", service_id).eq("tenant_id", tenant_id).execute()

        if not res.data:
            logger.warning(f"[{_where}] No rows updated (wrong tenant or ID?) | {_ctx}")
            return {"status": "error", "message": "Servicio no encontrado."}

        logger.info(f"✅ [{_where}] Updated service | {_ctx} | fields={list(update_data.keys())}")
        return {"status": "success", "service": res.data[0]}

    except Exception as e:
        err_str = str(e)
        if "duplicate" in err_str.lower() or "unique" in err_str.lower():
            return {"status": "error", "message": "Ya existe otro servicio con ese nombre."}

        logger.error(f"[{_where}] Failed | {_ctx} | error={err_str[:300]}", exc_info=True)
        sentry_sdk.set_context("services_update", {
            "tenant_id": tenant_id, "service_id": service_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Update Service Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Service ID:** {service_id}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{err_str[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error updating service: {err_str}"}


@router.delete("/{service_id}")
async def delete_service(service_id: str, tenant_id: str):
    """Soft-delete a service (set is_active=false). Hard-deletes only if explicitly requested."""
    _where = f"{_WHERE}.delete_service"
    _ctx = f"tenant={tenant_id} | service_id={service_id} | env={settings.ENVIRONMENT}"
    try:
        db = await SupabasePooler.get_client()

        # Check this isn't the last active service
        try:
            active_count = await db.table("tenant_services").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
            if active_count.count is not None and active_count.count <= 1:
                # Check if the one we're deleting IS the last active one
                target = await db.table("tenant_services").select("is_active").eq("id", service_id).eq("tenant_id", tenant_id).execute()
                if target.data and target.data[0].get("is_active"):
                    logger.warning(f"[{_where}] Prevented deactivation of last active service | {_ctx}")
                    return {
                        "status": "error",
                        "message": "No puedes desactivar tu último servicio activo. Tu asistente necesita al menos un servicio.",
                    }
        except Exception as count_err:
            # Non-critical: allow the deactivation if we can't count
            logger.warning(f"[{_where}] Active count check failed (proceeding anyway): {count_err}")
            sentry_sdk.add_breadcrumb(
                category="services", message=f"Active count check failed: {count_err}", level="warning"
            )

        # Soft-delete
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        res = await db.table("tenant_services").update({
            "is_active": False, "updated_at": now_iso
        }).eq("id", service_id).eq("tenant_id", tenant_id).execute()

        if not res.data:
            logger.warning(f"[{_where}] No rows updated | {_ctx}")
            return {"status": "error", "message": "Servicio no encontrado."}

        logger.info(f"✅ [{_where}] Deactivated service | {_ctx}")
        return {"status": "success", "message": "Servicio desactivado exitosamente."}

    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("services_delete", {
            "tenant_id": tenant_id, "service_id": service_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Delete Service Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Service ID:** {service_id}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error deleting service: {str(e)}"}
