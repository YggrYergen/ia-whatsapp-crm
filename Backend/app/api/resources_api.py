"""
Resources CRUD API — /api/resources endpoints.

Provides tenant-scoped CRUD for scheduling resources (boxes, teams, tables, etc.).
Resources are universal abstractions used by the native scheduling system.

Observability: Every except block → logger + Sentry + Discord (3-channel observability).

Docs-first references:
  - Supabase Python client: https://supabase.com/docs/reference/python/select
  - Existing schema: native_calendar_plan.md §2 — resources table
"""

import datetime
import sentry_sdk
from fastapi import APIRouter, Body

from app.core.config import settings
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger

router = APIRouter(prefix="/api/resources", tags=["resources"])

_WHERE = "resources_api"


@router.get("")
async def list_resources(tenant_id: str, include_inactive: bool = False):
    """List all resources for a tenant. Active-only by default."""
    _where = f"{_WHERE}.list_resources"
    _ctx = f"tenant={tenant_id} | include_inactive={include_inactive} | env={settings.ENVIRONMENT}"
    try:
        db = await SupabasePooler.get_client()
        query = db.table("resources").select("*").eq("tenant_id", tenant_id)
        if not include_inactive:
            query = query.eq("is_active", True)
        res = await query.order("sort_order").execute()
        logger.info(f"[{_where}] Listed {len(res.data or [])} resources | {_ctx}")
        return {"status": "success", "resources": res.data or []}
    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("resources_list", {"tenant_id": tenant_id, "environment": settings.ENVIRONMENT})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ List Resources Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error listing resources: {str(e)}", "resources": []}


@router.post("")
async def create_resource(payload: dict = Body(...)):
    """Create a new resource for a tenant."""
    _where = f"{_WHERE}.create_resource"
    tenant_id = payload.get("tenant_id", "")
    resource_name = payload.get("name", "")
    _ctx = f"tenant={tenant_id} | resource={resource_name} | env={settings.ENVIRONMENT}"
    try:
        if not tenant_id or not resource_name:
            return {"status": "error", "message": "tenant_id and name are required."}

        db = await SupabasePooler.get_client()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = {
            "tenant_id": tenant_id,
            "name": resource_name.strip(),
            "label": (payload.get("label") or resource_name).strip(),
            "color": payload.get("color", "#10b981"),
            "resource_type": payload.get("resource_type", "room"),
            "is_active": payload.get("is_active", True),
            "sort_order": payload.get("sort_order", 0),
            "metadata": payload.get("metadata", {}),
            "updated_at": now_iso,
        }

        res = await db.table("resources").insert(data).execute()

        if not res.data:
            logger.error(f"[{_where}] INSERT returned no data | {_ctx}")
            sentry_sdk.capture_message(f"resources INSERT empty response | {_ctx}", level="error")
            await send_discord_alert(
                title=f"⚠️ Create Resource Empty Response | Tenant {tenant_id}",
                description=f"**Where:** `{_where}`\n**Resource:** {resource_name}\n**Env:** {settings.ENVIRONMENT}",
                severity="error",
            )
            return {"status": "error", "message": "Error creating resource."}

        logger.info(f"✅ [{_where}] Created resource '{resource_name}' | id={res.data[0]['id']} | {_ctx}")
        return {"status": "success", "resource": res.data[0]}

    except Exception as e:
        err_str = str(e)
        if "duplicate" in err_str.lower() or "unique" in err_str.lower():
            return {"status": "error", "message": f"Ya existe un recurso con el nombre '{resource_name}'."}

        logger.error(f"[{_where}] Failed | {_ctx} | error={err_str[:300]}", exc_info=True)
        sentry_sdk.set_context("resources_create", {
            "tenant_id": tenant_id, "resource_name": resource_name,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Create Resource Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Resource:** {resource_name}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{err_str[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error creating resource: {err_str}"}


@router.put("/{resource_id}")
async def update_resource(resource_id: str, payload: dict = Body(...)):
    """Update an existing resource."""
    _where = f"{_WHERE}.update_resource"
    tenant_id = payload.get("tenant_id", "")
    _ctx = f"tenant={tenant_id} | resource_id={resource_id} | env={settings.ENVIRONMENT}"
    try:
        if not tenant_id:
            return {"status": "error", "message": "tenant_id is required."}

        db = await SupabasePooler.get_client()
        update_data = {"updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        allowed_fields = ["name", "label", "color", "resource_type", "is_active", "sort_order", "metadata"]
        for field in allowed_fields:
            if field in payload:
                val = payload[field]
                if isinstance(val, str):
                    val = val.strip()
                update_data[field] = val

        res = await db.table("resources").update(update_data).eq("id", resource_id).eq("tenant_id", tenant_id).execute()

        if not res.data:
            logger.warning(f"[{_where}] No rows updated | {_ctx}")
            return {"status": "error", "message": "Recurso no encontrado."}

        logger.info(f"✅ [{_where}] Updated resource | {_ctx} | fields={list(update_data.keys())}")
        return {"status": "success", "resource": res.data[0]}

    except Exception as e:
        err_str = str(e)
        if "duplicate" in err_str.lower() or "unique" in err_str.lower():
            return {"status": "error", "message": "Ya existe otro recurso con ese nombre."}

        logger.error(f"[{_where}] Failed | {_ctx} | error={err_str[:300]}", exc_info=True)
        sentry_sdk.set_context("resources_update", {
            "tenant_id": tenant_id, "resource_id": resource_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Update Resource Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Resource ID:** {resource_id}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{err_str[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error updating resource: {err_str}"}


@router.delete("/{resource_id}")
async def delete_resource(resource_id: str, tenant_id: str):
    """Soft-delete a resource. Prevents deactivating the last resource or one with future appointments."""
    _where = f"{_WHERE}.delete_resource"
    _ctx = f"tenant={tenant_id} | resource_id={resource_id} | env={settings.ENVIRONMENT}"
    try:
        db = await SupabasePooler.get_client()

        # Check: not the last active resource
        try:
            active_count = await db.table("resources").select("id", count="exact").eq("tenant_id", tenant_id).eq("is_active", True).execute()
            if active_count.count is not None and active_count.count <= 1:
                target = await db.table("resources").select("is_active").eq("id", resource_id).eq("tenant_id", tenant_id).execute()
                if target.data and target.data[0].get("is_active"):
                    logger.warning(f"[{_where}] Prevented deactivation of last active resource | {_ctx}")
                    return {
                        "status": "error",
                        "message": "No puedes desactivar tu último recurso activo. Se necesita al menos uno para agendar citas.",
                    }
        except Exception as count_err:
            logger.warning(f"[{_where}] Active count check failed (proceeding): {count_err}")
            sentry_sdk.add_breadcrumb(category="resources", message=f"Count check failed: {count_err}", level="warning")

        # Check: no future confirmed appointments
        try:
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            future_appts = await db.table("appointments").select("id", count="exact") \
                .eq("resource_id", resource_id).eq("status", "confirmed") \
                .gte("start_time", now_iso).execute()
            if future_appts.count and future_appts.count > 0:
                logger.warning(f"[{_where}] Blocked deactivation: {future_appts.count} future appointments | {_ctx}")
                return {
                    "status": "error",
                    "message": f"Este recurso tiene {future_appts.count} cita(s) futuras confirmadas. Cancélalas o reasígnalas antes de desactivar.",
                }
        except Exception as appts_err:
            logger.warning(f"[{_where}] Future appointments check failed (proceeding): {appts_err}")
            sentry_sdk.add_breadcrumb(category="resources", message=f"Appointments check failed: {appts_err}", level="warning")

        # Soft-delete
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        res = await db.table("resources").update({
            "is_active": False, "updated_at": now_iso
        }).eq("id", resource_id).eq("tenant_id", tenant_id).execute()

        if not res.data:
            return {"status": "error", "message": "Recurso no encontrado."}

        logger.info(f"✅ [{_where}] Deactivated resource | {_ctx}")
        return {"status": "success", "message": "Recurso desactivado exitosamente."}

    except Exception as e:
        logger.error(f"[{_where}] Failed | {_ctx} | error={str(e)[:300]}", exc_info=True)
        sentry_sdk.set_context("resources_delete", {
            "tenant_id": tenant_id, "resource_id": resource_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Delete Resource Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_where}`\n**Resource ID:** {resource_id}\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e,
        )
        return {"status": "error", "message": f"Error deleting resource: {str(e)}"}
