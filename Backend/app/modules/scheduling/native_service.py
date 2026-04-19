"""
Native Scheduling Service — Replaces GoogleCalendarClient with Supabase queries.

Docs-first references:
  - Supabase Python client: https://supabase.com/docs/reference/python/select
  - PostgreSQL EXCLUDE constraint: https://www.postgresql.org/docs/current/btree-gist.html
  - psycopg2 constraint violations: https://www.psycopg.org/docs/errors.html

Observability: Every except block reports through 3 channels:
  1. logger.error() with full context
  2. sentry_sdk.capture_exception() with structured context
  3. send_discord_alert() with severity + traceback

Architecture:
  - Tools (scheduling/tools.py) call SchedulingService methods
  - SchedulingService delegates to NativeSchedulingService (this file)
  - NativeSchedulingService queries Supabase tables: resources, appointments, scheduling_config
  - EXCLUDE USING gist constraint prevents double-booking at DB level
"""

import datetime
import traceback
from typing import Optional

import pytz
import sentry_sdk

from app.core.config import settings
from app.core.models import TenantContext
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.infrastructure.telemetry.logger_service import logger

# ────────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────────


async def _get_tenant_config(tenant_id: str) -> dict:
    """
    Fetch scheduling_config for a tenant.
    Returns config dict or sensible defaults if none configured.

    Observability: Logs warning + Sentry breadcrumb if no config found (not an error,
    but important for debugging cases where a tenant never completed onboarding).
    """
    _WHERE = "NativeSchedulingService._get_tenant_config"
    try:
        db = await SupabasePooler.get_client()
        res = await db.table("scheduling_config").select("*").eq("tenant_id", tenant_id).limit(1).execute()
        if res.data:
            return res.data[0]

        # No config yet — return defaults (tenant hasn't completed onboarding scheduling setup)
        logger.warning(
            f"[{_WHERE}] No scheduling_config for tenant={tenant_id}. Using defaults."
        )
        sentry_sdk.add_breadcrumb(
            category="scheduling",
            message=f"No scheduling_config for tenant {tenant_id}, using defaults",
            level="warning",
        )
        return {
            "business_hours": {
                "monday": {"start": "09:00", "end": "19:00"},
                "tuesday": {"start": "09:00", "end": "19:00"},
                "wednesday": {"start": "09:00", "end": "19:00"},
                "thursday": {"start": "09:00", "end": "19:00"},
                "friday": {"start": "09:00", "end": "19:00"},
                "saturday": None,
                "sunday": None,
            },
            "default_duration_minutes": 30,
            "slot_interval_minutes": 30,
            "buffer_between_minutes": 0,
            "round_robin_enabled": True,
            "timezone": "America/Santiago",
        }
    except Exception as e:
        logger.error(
            f"[{_WHERE}] DB error fetching config | tenant={tenant_id} | error={str(e)[:300]}",
            exc_info=True,
        )
        sentry_sdk.set_context("scheduling_config_fetch", {
            "tenant_id": tenant_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Scheduling Config Fetch Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_WHERE}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error",
            error=e,
        )
        # Return defaults so the caller doesn't crash
        return {
            "business_hours": {
                "monday": {"start": "09:00", "end": "19:00"},
                "tuesday": {"start": "09:00", "end": "19:00"},
                "wednesday": {"start": "09:00", "end": "19:00"},
                "thursday": {"start": "09:00", "end": "19:00"},
                "friday": {"start": "09:00", "end": "19:00"},
                "saturday": None,
                "sunday": None,
            },
            "default_duration_minutes": 30,
            "slot_interval_minutes": 30,
            "buffer_between_minutes": 0,
            "round_robin_enabled": True,
            "timezone": "America/Santiago",
        }


async def _get_active_resources(tenant_id: str) -> list:
    """Fetch all active resources for a tenant, ordered by sort_order."""
    _WHERE = "NativeSchedulingService._get_active_resources"
    try:
        db = await SupabasePooler.get_client()
        res = (
            await db.table("resources")
            .select("id, name, label, color, sort_order")
            .eq("tenant_id", tenant_id)
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        if not res.data:
            logger.warning(
                f"[{_WHERE}] No active resources for tenant={tenant_id}. "
                "Tenant may not have completed resource setup."
            )
            sentry_sdk.add_breadcrumb(
                category="scheduling",
                message=f"No active resources for tenant {tenant_id}",
                level="warning",
            )
        return res.data or []
    except Exception as e:
        logger.error(
            f"[{_WHERE}] DB error fetching resources | tenant={tenant_id} | error={str(e)[:300]}",
            exc_info=True,
        )
        sentry_sdk.set_context("resource_fetch", {
            "tenant_id": tenant_id,
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Resource Fetch Failed | Tenant {tenant_id}",
            description=f"**Where:** `{_WHERE}`\n**Env:** {settings.ENVIRONMENT}\n**Error:** ```{str(e)[:300]}```",
            severity="error",
            error=e,
        )
        return []


def _day_name_spanish_to_english(day_name_spanish: str) -> str:
    """Convert Spanish day name to English for business_hours key lookup."""
    mapping = {
        "lunes": "monday", "martes": "tuesday", "miércoles": "wednesday",
        "miercoles": "wednesday", "jueves": "thursday", "viernes": "friday",
        "sábado": "saturday", "sabado": "saturday", "domingo": "sunday",
    }
    return mapping.get(day_name_spanish.lower(), day_name_spanish.lower())


def _get_day_key(target_date: datetime.date) -> str:
    """Get the English day-of-week key for business_hours lookup."""
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    return days[target_date.weekday()]


# ────────────────────────────────────────────────────────────────────────────────
# Main Service
# ────────────────────────────────────────────────────────────────────────────────


class NativeSchedulingService:
    """
    Pure Supabase scheduling service. No Google Calendar dependency.

    All methods return dicts with at minimum {"status": "success"|"error", "message": str}.
    This matches the contract expected by scheduling/tools.py.
    """

    @staticmethod
    async def check_availability(
        tenant: TenantContext, date_str: str, duration_minutes: Optional[int] = None
    ) -> dict:
        """
        Check available time slots for a given date across all resources.

        Returns: {"status": "success", "available_slots": ["09:00", "09:30", ...], "duration": int, "message": str}

        Logic:
        1. Get tenant's scheduling config (business hours, slot interval)
        2. Get all active resources
        3. For each slot in the day, check if ANY resource is free
        4. A slot is "available" if at least one resource has no overlapping confirmed appointment
        """
        _WHERE = "NativeSchedulingService.check_availability"
        tenant_id = tenant.id if tenant else "unknown"
        try:
            config = await _get_tenant_config(tenant_id)
            tz = pytz.timezone(config.get("timezone", "America/Santiago"))
            duration = duration_minutes or config.get("default_duration_minutes", 30)
            slot_interval = config.get("slot_interval_minutes", 30)

            # Parse target date
            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as ve:
                logger.warning(f"[{_WHERE}] Invalid date format: {date_str} | tenant={tenant_id}")
                sentry_sdk.capture_message(
                    f"Invalid date format in check_availability: {date_str}", level="warning"
                )
                return {"status": "error", "message": f"Formato de fecha inválido: {date_str}. Debe ser YYYY-MM-DD."}

            # Check business hours for this day
            day_key = _get_day_key(target_date)
            business_hours = config.get("business_hours", {})
            day_hours = business_hours.get(day_key)

            if not day_hours:
                return {
                    "status": "success",
                    "available_slots": [],
                    "duration": duration,
                    "message": f"El negocio no atiende los {day_key}. No hay horarios disponibles.",
                }

            # Parse business hours
            bh_start = datetime.datetime.strptime(day_hours["start"], "%H:%M").time()
            bh_end = datetime.datetime.strptime(day_hours["end"], "%H:%M").time()

            # Get active resources
            resources = await _get_active_resources(tenant_id)
            if not resources:
                return {
                    "status": "error",
                    "message": "No hay recursos configurados para este negocio. Contacte al administrador.",
                }

            resource_ids = [r["id"] for r in resources]

            # Get all confirmed appointments for this date
            day_start = tz.localize(datetime.datetime.combine(target_date, datetime.time(0, 0)))
            day_end = tz.localize(datetime.datetime.combine(target_date, datetime.time(23, 59, 59)))

            db = await SupabasePooler.get_client()
            appts_res = (
                await db.table("appointments")
                .select("resource_id, start_time, end_time")
                .in_("resource_id", resource_ids)
                .neq("status", "cancelled")
                .gte("start_time", day_start.isoformat())
                .lte("start_time", day_end.isoformat())
                .execute()
            )

            # Build busy ranges per resource
            busy_by_resource = {rid: [] for rid in resource_ids}
            for appt in (appts_res.data or []):
                rid = appt["resource_id"]
                s = datetime.datetime.fromisoformat(appt["start_time"])
                e = datetime.datetime.fromisoformat(appt["end_time"])
                if rid in busy_by_resource:
                    busy_by_resource[rid].append((s, e))

            # Generate slots and check availability
            available_slots = []
            buffer = config.get("buffer_between_minutes", 0)
            current_time = datetime.datetime.combine(target_date, bh_start)

            while current_time.time() < bh_end:
                slot_str = current_time.strftime("%H:%M")
                slot_start = tz.localize(datetime.datetime.combine(target_date, current_time.time()))
                slot_end = slot_start + datetime.timedelta(minutes=duration + buffer)

                # Check if the slot end extends beyond business hours
                slot_end_time_only = (current_time + datetime.timedelta(minutes=duration)).time()
                if slot_end_time_only > bh_end:
                    current_time += datetime.timedelta(minutes=slot_interval)
                    continue

                # A slot is available if ANY resource is free
                for rid in resource_ids:
                    is_busy = False
                    for bs, be in busy_by_resource.get(rid, []):
                        # Check overlap: max(start1, start2) < min(end1, end2)
                        if max(slot_start, bs) < min(slot_end, be):
                            is_busy = True
                            break
                    if not is_busy:
                        available_slots.append(slot_str)
                        break  # At least one resource is free → slot is available

                current_time += datetime.timedelta(minutes=slot_interval)

            msg = f"Se encontraron {len(available_slots)} horarios libres para el {date_str}."
            if not available_slots:
                msg = f"No hay horarios disponibles para el {date_str}."

            return {
                "status": "success",
                "available_slots": available_slots,
                "duration": duration,
                "message": msg,
            }

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | date={date_str} | "
                f"duration={duration_minutes} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_check_availability", {
                "tenant_id": tenant_id,
                "date_str": date_str,
                "duration_minutes": duration_minutes,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ check_availability Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n**Date:** {date_str}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error checking availability: {str(e)}"}

    @staticmethod
    async def book_appointment(
        tenant: TenantContext,
        date_str: str,
        time_str: str,
        duration_minutes: int,
        user_name: str,
        patient_phone: str,
        booked_by: str = "ai_assistant",
        resource_id: str | None = None,
        service_name: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """
        Book an appointment using round-robin resource selection.

        Returns: {"status": "success", "message": str, "box_label": str, "appointment_id": str}

        Logic:
        1. Parse date/time, validate
        2. Get all active resources
        3. For each resource (sorted by sort_order), check if slot is free
        4. INSERT into appointments → if EXCLUDE constraint fires, handle gracefully
        5. Publish system_alert event via event_bus
        """
        _WHERE = "NativeSchedulingService.book_appointment"
        tenant_id = tenant.id if tenant else "unknown"
        try:
            config = await _get_tenant_config(tenant_id)
            tz = pytz.timezone(config.get("timezone", "America/Santiago"))

            # Parse date/time
            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                start_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            except ValueError as ve:
                logger.warning(
                    f"[{_WHERE}] Invalid date/time format: {date_str} {time_str} | tenant={tenant_id}"
                )
                sentry_sdk.capture_message(
                    f"Invalid date/time in book_appointment: {date_str} {time_str}", level="warning"
                )
                return {
                    "status": "error",
                    "message": f"Formato de fecha/hora inválido: {date_str} {time_str}. Use YYYY-MM-DD y HH:MM.",
                }

            start_dt = tz.localize(datetime.datetime.combine(target_date, start_time))
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

            # Validate against business hours
            day_key = _get_day_key(target_date)
            business_hours = config.get("business_hours", {})
            day_hours = business_hours.get(day_key)

            if not day_hours:
                return {
                    "status": "error",
                    "message": f"El negocio no atiende los {day_key}. No se puede agendar.",
                }

            bh_start = datetime.datetime.strptime(day_hours["start"], "%H:%M").time()
            bh_end = datetime.datetime.strptime(day_hours["end"], "%H:%M").time()

            if start_time < bh_start or end_dt.time() > bh_end:
                return {
                    "status": "error",
                    "message": (
                        f"El horario {time_str} está fuera del horario de atención "
                        f"({day_hours['start']} - {day_hours['end']})."
                    ),
                }

            # Get resources + DB client for availability checks
            resources = await _get_active_resources(tenant_id)
            if not resources:
                return {
                    "status": "error",
                    "message": "No hay recursos configurados para este negocio. Contacte al administrador.",
                }

            db = await SupabasePooler.get_client()

            # Resource selection: explicit resource_id from UI, or round-robin
            selected_resource = None
            if resource_id:
                # User explicitly chose a resource from the booking modal
                explicit = next((r for r in resources if r['id'] == resource_id), None)
                if explicit:
                    conflict = (
                        await db.table("appointments")
                        .select("id")
                        .eq("resource_id", resource_id)
                        .neq("status", "cancelled")
                        .lt("start_time", end_dt.isoformat())
                        .gt("end_time", start_dt.isoformat())
                        .limit(1)
                        .execute()
                    )
                    if not conflict.data:
                        selected_resource = explicit
                    else:
                        return {
                            "status": "error",
                            "message": f"{explicit.get('label', explicit['name'])} ya está ocupado en ese horario.",
                        }
                else:
                    logger.warning(
                        f"[{_WHERE}] resource_id={resource_id} not found in active resources | tenant={tenant_id}"
                    )

            # Fallback: round-robin across all resources by sort_order
            if not selected_resource:
                for resource in resources:
                    conflict = (
                        await db.table("appointments")
                        .select("id")
                        .eq("resource_id", resource["id"])
                        .neq("status", "cancelled")
                        .lt("start_time", end_dt.isoformat())
                        .gt("end_time", start_dt.isoformat())
                        .limit(1)
                        .execute()
                    )
                    if not conflict.data:
                        selected_resource = resource
                        break

            if not selected_resource:
                return {
                    "status": "error",
                    "message": "Lo siento, ese horario acaba de ocuparse en todos los recursos disponibles.",
                }

            resource_label = selected_resource.get("label") or selected_resource["name"]

            # Attempt to link to existing contact
            contact_id = None
            try:
                contact_res = (
                    await db.table("contacts")
                    .select("id")
                    .eq("tenant_id", tenant_id)
                    .eq("phone_number", patient_phone)
                    .limit(1)
                    .execute()
                )
                if contact_res.data:
                    contact_id = contact_res.data[0]["id"]
            except Exception as contact_err:
                # Non-critical: log but don't fail the booking
                logger.warning(
                    f"[{_WHERE}] Failed to lookup contact for phone={patient_phone}: {contact_err}"
                )
                sentry_sdk.add_breadcrumb(
                    category="scheduling",
                    message=f"Contact lookup failed for {patient_phone}: {contact_err}",
                    level="warning",
                )

            # INSERT the appointment
            # The EXCLUDE USING gist constraint is the final safety net against double-booking
            try:
                appt_data = {
                    "tenant_id": tenant_id,
                    "resource_id": selected_resource["id"],
                    "contact_id": contact_id,
                    "start_time": start_dt.isoformat(),
                    "end_time": end_dt.isoformat(),
                    "duration_minutes": duration_minutes,
                    "service_name": service_name,
                    "client_name": user_name,
                    "client_phone": patient_phone,
                    "status": "confirmed",
                    "booked_by": booked_by,
                    "notes": notes or (f"Agendado por {booked_by}" + (f" | Servicio: {service_name}" if service_name else "")),
                }
                insert_res = await db.table("appointments").insert(appt_data).execute()

                if not insert_res.data:
                    logger.error(
                        f"[{_WHERE}] INSERT returned no data | tenant={tenant_id} | "
                        f"resource={resource_label} | {date_str} {time_str}"
                    )
                    sentry_sdk.capture_message(
                        f"appointments INSERT returned empty data for tenant {tenant_id}",
                        level="error",
                    )
                    await send_discord_alert(
                        title=f"⚠️ Booking INSERT Empty Response | Tenant {tenant_id}",
                        description=(
                            f"**Where:** `{_WHERE}`\n"
                            f"**Resource:** {resource_label}\n"
                            f"**Slot:** {date_str} {time_str}\n"
                            f"**Env:** {settings.ENVIRONMENT}"
                        ),
                        severity="error",
                    )
                    return {
                        "status": "error",
                        "message": "Error interno al registrar la cita. Intente nuevamente.",
                    }

                appointment_id = insert_res.data[0]["id"]

            except Exception as insert_err:
                err_str = str(insert_err)
                # Check for EXCLUDE constraint violation (double-booking race condition caught by DB)
                if "no_double_booking" in err_str or "exclusion" in err_str.lower():
                    logger.warning(
                        f"[{_WHERE}] EXCLUDE constraint fired (race condition caught) | "
                        f"tenant={tenant_id} | resource={resource_label} | {date_str} {time_str}"
                    )
                    sentry_sdk.add_breadcrumb(
                        category="scheduling",
                        message=f"Double-booking prevented by DB constraint: {resource_label} at {date_str} {time_str}",
                        level="warning",
                    )
                    return {
                        "status": "error",
                        "message": "Lo siento, ese horario se acaba de ocupar. Por favor elige otro horario.",
                    }
                # Any other INSERT error is unexpected
                raise

            logger.info(
                f"✅ [{_WHERE}] Booked {user_name} ({patient_phone}) → {resource_label} "
                f"{date_str} {time_str} | appt_id={appointment_id} | tenant={tenant_id}"
            )

            return {
                "status": "success",
                "message": f"Agendado con éxito en {resource_label}.",
                "box_label": resource_label,
                "appointment_id": appointment_id,
            }

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | {date_str} {time_str} | "
                f"patient={user_name} | phone={patient_phone} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_book", {
                "tenant_id": tenant_id,
                "date_str": date_str,
                "time_str": time_str,
                "user_name": user_name,
                "patient_phone": patient_phone,
                "duration_minutes": duration_minutes,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ book_appointment Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n**Patient:** {user_name} ({patient_phone})\n"
                    f"**Slot:** {date_str} {time_str} ({duration_minutes}min)\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error booking appointment: {str(e)}"}

    @staticmethod
    async def cancel_appointment(
        tenant: TenantContext, date_str: str, time_str: str, patient_phone: str
    ) -> dict:
        """
        Cancel an appointment by matching date/time/phone.

        Sets status='cancelled' + cancelled_at=now(). Does NOT hard-delete.
        Returns: {"status": "success"|"error", "message": str, "details": str, "items": [str]}
        """
        _WHERE = "NativeSchedulingService.cancel_appointment"
        tenant_id = tenant.id if tenant else "unknown"
        try:
            config = await _get_tenant_config(tenant_id)
            tz = pytz.timezone(config.get("timezone", "America/Santiago"))

            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                target_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            except ValueError:
                logger.warning(
                    f"[{_WHERE}] Invalid date/time: {date_str} {time_str} | tenant={tenant_id}"
                )
                sentry_sdk.capture_message(
                    f"Invalid date/time in cancel_appointment: {date_str} {time_str}", level="warning"
                )
                return {
                    "status": "error",
                    "message": f"Formato de fecha/hora inválido: {date_str} {time_str}.",
                }

            # Find matching appointments
            target_start = tz.localize(datetime.datetime.combine(target_date, target_time))
            # Window: exact start time ± 1 minute to handle timezone rounding
            window_start = (target_start - datetime.timedelta(minutes=1)).isoformat()
            window_end = (target_start + datetime.timedelta(minutes=1)).isoformat()

            db = await SupabasePooler.get_client()
            matches = (
                await db.table("appointments")
                .select("id, client_name, client_phone, start_time, end_time, resource_id")
                .eq("tenant_id", tenant_id)
                .eq("status", "confirmed")
                .gte("start_time", window_start)
                .lte("start_time", window_end)
                .execute()
            )

            if not matches.data:
                return {
                    "status": "error",
                    "message": "No encontré ninguna cita en la franja de tiempo indicada.",
                }

            # Filter by phone if provided
            to_cancel = []
            for appt in matches.data:
                if patient_phone and appt["client_phone"] != patient_phone:
                    continue
                to_cancel.append(appt)

            if not to_cancel:
                return {
                    "status": "error",
                    "message": "No encontré ninguna cita asociada a tu celular en la franja de tiempo indicada.",
                }

            # Get resource names for the details
            resource_ids = list(set(a["resource_id"] for a in to_cancel))
            try:
                resource_res = (
                    await db.table("resources")
                    .select("id, name, label")
                    .in_("id", resource_ids)
                    .execute()
                )
                resource_map = {r["id"]: r.get("label") or r["name"] for r in (resource_res.data or [])}
            except Exception as res_err:
                logger.warning(f"[{_WHERE}] Failed to fetch resource names: {res_err}")
                sentry_sdk.add_breadcrumb(
                    category="scheduling",
                    message=f"Resource name lookup failed during cancel: {res_err}",
                    level="warning",
                )
                resource_map = {}

            # Cancel each matching appointment
            summaries = []
            now_iso = datetime.datetime.now(tz).isoformat()
            for appt in to_cancel:
                try:
                    await (
                        db.table("appointments")
                        .update({"status": "cancelled", "cancelled_at": now_iso, "updated_at": now_iso})
                        .eq("id", appt["id"])
                        .execute()
                    )
                    resource_name = resource_map.get(appt["resource_id"], "Recurso")
                    start_fmt = datetime.datetime.fromisoformat(appt["start_time"]).astimezone(tz).strftime("%H:%M")
                    summaries.append(
                        f"Cita ({resource_name}) - {appt['client_name']} a las {start_fmt}"
                    )
                except Exception as cancel_err:
                    logger.error(
                        f"[{_WHERE}] Failed to cancel appt {appt['id']}: {cancel_err}",
                        exc_info=True,
                    )
                    sentry_sdk.set_context("cancel_appointment_item", {
                        "appointment_id": appt["id"],
                        "tenant_id": tenant_id,
                    })
                    sentry_sdk.capture_exception(cancel_err)
                    await send_discord_alert(
                        title=f"❌ Cancel Appointment Item Failed | Tenant {tenant_id}",
                        description=(
                            f"**Where:** `{_WHERE}`\n**Appt ID:** {appt['id']}\n"
                            f"**Env:** {settings.ENVIRONMENT}\n"
                            f"**Error:** ```{str(cancel_err)[:300]}```"
                        ),
                        severity="error",
                        error=cancel_err,
                    )

            if not summaries:
                return {"status": "error", "message": "Hubo un error al cancelar las citas. Intente nuevamente."}

            logger.info(
                f"✅ [{_WHERE}] Cancelled {len(summaries)} appointment(s) for {patient_phone} "
                f"at {date_str} {time_str} | tenant={tenant_id}"
            )

            return {
                "status": "success",
                "message": f"Se cancelaron {len(summaries)} cita(s) exitosamente.",
                "details": "\n".join(summaries),
                "items": summaries,
            }

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | {date_str} {time_str} | "
                f"phone={patient_phone} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_cancel", {
                "tenant_id": tenant_id,
                "date_str": date_str,
                "time_str": time_str,
                "patient_phone": patient_phone,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ cancel_appointment Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n**Phone:** {patient_phone}\n"
                    f"**Slot:** {date_str} {time_str}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error cancelling appointment: {str(e)}"}

    @staticmethod
    async def update_appointment(
        tenant: TenantContext,
        date_str: str,
        time_str: str,
        new_date: str,
        new_time: str,
        patient_phone: str,
        user_name: str,
    ) -> dict:
        """
        Reschedule an appointment: cancel the old one, book a new one.

        This is atomically safe because each step has its own EXCLUDE constraint protection.
        """
        _WHERE = "NativeSchedulingService.update_appointment"
        tenant_id = tenant.id if tenant else "unknown"
        try:
            # Step 1: Cancel the existing appointment
            cancel_res = await NativeSchedulingService.cancel_appointment(
                tenant, date_str, time_str, patient_phone
            )
            if cancel_res.get("status") == "error":
                return {
                    "status": "error",
                    "message": f"No se pudo reagendar. Falló cancelación previa: {cancel_res.get('message')}",
                }

            # Step 2: Book the new slot
            book_res = await NativeSchedulingService.book_appointment(
                tenant, new_date, new_time, 30, user_name, patient_phone
            )
            if book_res.get("status") == "success":
                logger.info(
                    f"✅ [{_WHERE}] Rescheduled {user_name} ({patient_phone}) "
                    f"{date_str} {time_str} → {new_date} {new_time} | tenant={tenant_id}"
                )
                return {
                    "status": "success",
                    "message": "Cita re-agendada exitosamente.",
                }

            # If booking failed, log the situation (original was already cancelled)
            logger.warning(
                f"[{_WHERE}] Cancel succeeded but rebooking failed | tenant={tenant_id} | "
                f"{date_str} {time_str} → {new_date} {new_time} | phone={patient_phone} | "
                f"book_error={book_res.get('message')}"
            )
            sentry_sdk.set_context("scheduling_update_partial", {
                "tenant_id": tenant_id,
                "old_slot": f"{date_str} {time_str}",
                "new_slot": f"{new_date} {new_time}",
                "cancel_status": "success",
                "book_status": "error",
                "book_message": book_res.get("message", ""),
            })
            sentry_sdk.capture_message(
                f"Reschedule partial failure: cancel OK but rebook failed for tenant {tenant_id}",
                level="warning",
            )
            await send_discord_alert(
                title=f"⚠️ Reschedule Partial Failure | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**Cancel:** ✅ succeeded\n"
                    f"**Rebook:** ❌ failed: {book_res.get('message', '')[:200]}\n"
                    f"**Old slot:** {date_str} {time_str}\n"
                    f"**New slot:** {new_date} {new_time}\n"
                    f"**Patient:** {user_name} ({patient_phone})\n"
                    f"**Env:** {settings.ENVIRONMENT}"
                ),
                severity="error",
            )
            return book_res

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | "
                f"{date_str} {time_str} → {new_date} {new_time} | "
                f"patient={user_name} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_update", {
                "tenant_id": tenant_id,
                "date_str": date_str,
                "time_str": time_str,
                "new_date": new_date,
                "new_time": new_time,
                "patient_phone": patient_phone,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ update_appointment Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**Old:** {date_str} {time_str} → **New:** {new_date} {new_time}\n"
                    f"**Patient:** {user_name} ({patient_phone})\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error updating appointment: {str(e)}"}

    @staticmethod
    async def get_appointments(
        tenant: TenantContext, date_str: str, caller_phone: str, caller_role: str
    ) -> dict:
        """
        List appointments for a given date.
        Staff/admin: see all. Cliente: see only own.

        Returns shape matching the old GoogleCalendarClient.list_appointments() contract.
        """
        _WHERE = "NativeSchedulingService.get_appointments"
        tenant_id = tenant.id if tenant else "unknown"
        try:
            config = await _get_tenant_config(tenant_id)
            tz = pytz.timezone(config.get("timezone", "America/Santiago"))

            try:
                target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"[{_WHERE}] Invalid date: {date_str} | tenant={tenant_id}")
                sentry_sdk.capture_message(
                    f"Invalid date in get_appointments: {date_str}", level="warning"
                )
                return {"status": "error", "message": f"Formato de fecha inválido: {date_str}."}

            day_start = tz.localize(datetime.datetime.combine(target_date, datetime.time(0, 0)))
            day_end = tz.localize(datetime.datetime.combine(target_date, datetime.time(23, 59, 59)))

            db = await SupabasePooler.get_client()

            # Build query
            query = (
                db.table("appointments")
                .select("id, resource_id, client_name, client_phone, start_time, end_time, status")
                .eq("tenant_id", tenant_id)
                .eq("status", "confirmed")
                .gte("start_time", day_start.isoformat())
                .lte("start_time", day_end.isoformat())
                .order("start_time")
            )

            appts_res = await query.execute()
            appts = appts_res.data or []

            if not appts:
                return {"status": "success", "message": "No hay citas agendadas en esta fecha para tu perfil."}

            # Get resource names
            resource_ids = list(set(a["resource_id"] for a in appts))
            try:
                resource_res = (
                    await db.table("resources")
                    .select("id, name, label")
                    .in_("id", resource_ids)
                    .execute()
                )
                resource_map = {r["id"]: r.get("label") or r["name"] for r in (resource_res.data or [])}
            except Exception as res_err:
                logger.warning(f"[{_WHERE}] Resource name lookup failed: {res_err}")
                sentry_sdk.add_breadcrumb(
                    category="scheduling",
                    message=f"Resource name lookup failed: {res_err}",
                    level="warning",
                )
                resource_map = {}

            # Format results based on caller role
            formatted = []
            for appt in appts:
                resource_name = resource_map.get(appt["resource_id"], "Recurso")
                start_fmt = datetime.datetime.fromisoformat(appt["start_time"]).astimezone(tz).strftime("%H:%M")
                end_fmt = datetime.datetime.fromisoformat(appt["end_time"]).astimezone(tz).strftime("%H:%M")

                if caller_role in ["admin", "staff"]:
                    formatted.append(
                        f"[{start_fmt} - {end_fmt}] {resource_name}: Cita - {appt['client_name']}"
                    )
                else:
                    # Client only sees their own
                    if caller_phone and appt["client_phone"] == caller_phone:
                        formatted.append(
                            f"[{start_fmt} - {end_fmt}] {resource_name}: Tienes una cita agendada."
                        )

            if not formatted:
                return {"status": "success", "message": "No hay citas agendadas en esta fecha para tu perfil."}

            return {
                "status": "success",
                "message": "Citas encontradas:\n" + "\n".join(sorted(formatted)),
            }

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | date={date_str} | "
                f"caller={caller_phone} | role={caller_role} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_get_appointments", {
                "tenant_id": tenant_id,
                "date_str": date_str,
                "caller_phone": caller_phone,
                "caller_role": caller_role,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ get_appointments Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n**Date:** {date_str}\n"
                    f"**Caller:** {caller_phone} ({caller_role})\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error listing appointments: {str(e)}"}

    @staticmethod
    async def get_structured_events(tenant_id: str, start_iso: str, end_iso: str) -> dict:
        """
        Get events for the frontend calendar view (AgendaView.tsx).

        Returns the EXACT same shape as GoogleCalendarClient.get_structured_events():
        {
            "status": "success",
            "events": [
                {
                    "id": "uuid",
                    "summary": "Cita (Box 1) - Juan",
                    "description": "Paciente: Juan\\nTeléfono: +569...\\nDuración: 30 min",
                    "start": "2026-04-15T10:00:00-04:00",
                    "end": "2026-04-15T10:30:00-04:00",
                    "box": "Box 1",
                    "status": "Confirmado"
                }
            ]
        }
        """
        _WHERE = "NativeSchedulingService.get_structured_events"
        try:
            db = await SupabasePooler.get_client()

            appts_res = (
                await db.table("appointments")
                .select("id, resource_id, client_name, client_phone, start_time, end_time, duration_minutes, status, booked_by")
                .eq("tenant_id", tenant_id)
                .neq("status", "cancelled")
                .gte("start_time", start_iso)
                .lte("start_time", end_iso)
                .order("start_time")
                .execute()
            )

            appts = appts_res.data or []

            # Get resource names
            resource_ids = list(set(a["resource_id"] for a in appts))
            resource_map = {}
            if resource_ids:
                try:
                    resource_res = (
                        await db.table("resources")
                        .select("id, name, label, color")
                        .in_("id", resource_ids)
                        .execute()
                    )
                    resource_map = {
                        r["id"]: {
                            "name": r.get("label") or r["name"],
                            "color": r.get("color", "#6366f1"),
                        }
                        for r in (resource_res.data or [])
                    }
                except Exception as res_err:
                    logger.warning(f"[{_WHERE}] Resource name lookup failed: {res_err}")
                    sentry_sdk.add_breadcrumb(
                        category="scheduling",
                        message=f"Resource lookup failed in get_structured_events: {res_err}",
                        level="warning",
                    )

            # Format into the shape AgendaView.tsx expects
            status_map = {
                "confirmed": "Confirmado",
                "completed": "Completado",
                "no_show": "No asistió",
            }

            events = []
            for appt in appts:
                resource_info = resource_map.get(appt["resource_id"], {"name": "Recurso", "color": "#6366f1"})
                resource_name = resource_info["name"]
                events.append({
                    "id": appt["id"],
                    "summary": f"Cita ({resource_name}) - {appt['client_name']}",
                    "description": (
                        f"Paciente: {appt['client_name']}\n"
                        f"Teléfono: {appt['client_phone']}\n"
                        f"Duración: {appt['duration_minutes']} min\n"
                        f"Agendado por: {appt.get('booked_by', 'ai_assistant')}"
                    ),
                    "start": appt["start_time"],
                    "end": appt["end_time"],
                    "box": resource_name,
                    "color": resource_info["color"],
                    "status": status_map.get(appt["status"], appt["status"]),
                })

            return {"status": "success", "events": events}

        except Exception as e:
            logger.error(
                f"[{_WHERE}] Failed | tenant={tenant_id} | "
                f"range={start_iso} to {end_iso} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("scheduling_structured_events", {
                "tenant_id": tenant_id,
                "start_iso": start_iso,
                "end_iso": end_iso,
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ get_structured_events Failed | Tenant {tenant_id}",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**Range:** {start_iso} → {end_iso}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "events": []}
