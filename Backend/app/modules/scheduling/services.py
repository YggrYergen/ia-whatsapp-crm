"""
Scheduling Service — Orchestration layer between tools and the scheduling backend.

Previously delegated to GoogleCalendarClient. Now delegates to NativeSchedulingService
(pure Supabase queries, no Google Calendar dependency).

Observability: Each method has its own error handling in the underlying service.
This layer adds event_bus notifications for successful operations (staff alerts).
Every except block here reports through 3 channels: logger + Sentry + Discord.
"""

import sentry_sdk
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.core.config import settings
from app.core.models import TenantContext
from app.core.event_bus import event_bus
from app.modules.scheduling.native_service import NativeSchedulingService


class SchedulingService:
    @staticmethod
    async def check_availability(tenant: TenantContext, date_str: str, duration_minutes: int) -> dict:
        logger.info(f"Checking native availability for {date_str}")
        return await NativeSchedulingService.check_availability(tenant, date_str, duration_minutes)

    @staticmethod
    async def book_appointment(tenant: TenantContext, date_str: str, time_str: str, duration_minutes: int, user_name: str, patient_phone: str) -> dict:
        logger.info(f"Booking {patient_phone} at {date_str} {time_str}")
        res = await NativeSchedulingService.book_appointment(tenant, date_str, time_str, duration_minutes, user_name, patient_phone)
        if res.get("status") == "success":
            try:
                payload = {
                    "tenant_id": tenant.id,
                    "patient_phone": patient_phone,
                    "reason": f"NUEVA CITA AGENDADA: El paciente {user_name} agendó para el {date_str} a las {time_str} en {res.get('box_label')}.",
                    "staff_number": "+56999999999"
                }
                await event_bus.publish("system_alert", payload)
            except Exception as evt_err:
                # Non-critical: event_bus failure shouldn't block the booking success
                logger.error(
                    f"[SchedulingService.book_appointment] event_bus publish failed: {evt_err}",
                    exc_info=True,
                )
                sentry_sdk.set_context("event_bus_publish", {
                    "tenant_id": tenant.id,
                    "event_type": "system_alert",
                    "trigger": "book_appointment",
                })
                sentry_sdk.capture_exception(evt_err)
                await send_discord_alert(
                    title=f"⚠️ Event Bus Publish Failed | book_appointment | Tenant {tenant.id}",
                    description=(
                        f"**Booking succeeded** but staff notification failed.\n"
                        f"**Patient:** {user_name} ({patient_phone})\n"
                        f"**Slot:** {date_str} {time_str}\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**Error:** ```{str(evt_err)[:300]}```"
                    ),
                    severity="error",
                    error=evt_err,
                )
        return res

    @staticmethod
    async def update_appointment(tenant: TenantContext, date_str: str, time_str: str, new_date: str, new_time: str, patient_phone: str, user_name: str) -> dict:
        res = await NativeSchedulingService.update_appointment(tenant, date_str, time_str, new_date, new_time, patient_phone, user_name)
        if res.get("status") == "success":
            try:
                payload = {
                    "tenant_id": tenant.id,
                    "patient_phone": patient_phone,
                    "reason": f"CITA RE-AGENDADA: El paciente {user_name} movió su bloque del {date_str} {time_str} para el {new_date} a las {new_time}.",
                    "staff_number": "+56999999999"
                }
                await event_bus.publish("system_alert", payload)
            except Exception as evt_err:
                logger.error(
                    f"[SchedulingService.update_appointment] event_bus publish failed: {evt_err}",
                    exc_info=True,
                )
                sentry_sdk.set_context("event_bus_publish", {
                    "tenant_id": tenant.id,
                    "event_type": "system_alert",
                    "trigger": "update_appointment",
                })
                sentry_sdk.capture_exception(evt_err)
                await send_discord_alert(
                    title=f"⚠️ Event Bus Publish Failed | update_appointment | Tenant {tenant.id}",
                    description=(
                        f"**Reschedule succeeded** but staff notification failed.\n"
                        f"**Patient:** {user_name} ({patient_phone})\n"
                        f"**Old:** {date_str} {time_str} → **New:** {new_date} {new_time}\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**Error:** ```{str(evt_err)[:300]}```"
                    ),
                    severity="error",
                    error=evt_err,
                )
        return res

    @staticmethod
    async def cancel_appointment(tenant: TenantContext, date_str: str, time_str: str, patient_phone: str) -> dict:
        logger.info(f"Cancelling appointment for {patient_phone} at {date_str} {time_str}")
        res = await NativeSchedulingService.cancel_appointment(tenant, date_str, time_str, patient_phone)
        if res.get("status") == "success":
            items = res.get("items", [])
            if not items:
                items = [res.get("details", "")]

            for item_desc in items:
                try:
                    payload = {
                        "tenant_id": tenant.id,
                        "patient_phone": patient_phone,
                        "reason": f"CITA CANCELADA del {date_str} a las {time_str}.\nDetalle: {item_desc}",
                        "staff_number": "+56999999999"
                    }
                    await event_bus.publish("system_alert", payload)
                except Exception as evt_err:
                    logger.error(
                        f"[SchedulingService.cancel_appointment] event_bus publish failed: {evt_err}",
                        exc_info=True,
                    )
                    sentry_sdk.set_context("event_bus_publish", {
                        "tenant_id": tenant.id,
                        "event_type": "system_alert",
                        "trigger": "cancel_appointment",
                    })
                    sentry_sdk.capture_exception(evt_err)
                    await send_discord_alert(
                        title=f"⚠️ Event Bus Publish Failed | cancel_appointment | Tenant {tenant.id}",
                        description=(
                            f"**Cancel succeeded** but staff notification failed.\n"
                            f"**Patient phone:** {patient_phone}\n"
                            f"**Slot:** {date_str} {time_str}\n"
                            f"**Env:** {settings.ENVIRONMENT}\n"
                            f"**Error:** ```{str(evt_err)[:300]}```"
                        ),
                        severity="error",
                        error=evt_err,
                    )
        return res

    @staticmethod
    async def request_human_escalation(tenant: TenantContext, patient_phone: str, reason: str) -> dict:
        """Human escalation — publish event to alert staff. Not calendar-related."""
        _WHERE = "SchedulingService.request_human_escalation"
        logger.info(f"Escalation requested for {patient_phone}: {reason}")
        try:
            payload = {
                "tenant_id": tenant.id,
                "patient_phone": patient_phone,
                "staff_number": "+56999999999",
                "reason": reason
            }
            await event_bus.publish("system_alert", payload)
            return {
                "status": "success",
                "message": "El Staff ya ha recibido tu mensaje de alerta en su bandeja de urgencias. Un agente humano se sumará a la intervención pronto."
            }
        except Exception as e:
            logger.error(
                f"[{_WHERE}] event_bus publish failed | phone={patient_phone} | error={str(e)[:300]}",
                exc_info=True,
            )
            sentry_sdk.set_context("escalation_publish", {
                "tenant_id": tenant.id,
                "patient_phone": patient_phone,
                "reason": reason[:100],
                "environment": settings.ENVIRONMENT,
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ Escalation Event Publish Failed | {patient_phone}",
                description=(
                    f"**Where:** `{_WHERE}`\n"
                    f"**Phone:** {patient_phone}\n"
                    f"**Reason:** {reason[:200]}\n"
                    f"**Env:** {settings.ENVIRONMENT}\n"
                    f"**Error:** ```{str(e)[:300]}```"
                ),
                severity="error",
                error=e,
            )
            return {"status": "error", "message": f"Error during escalation: {str(e)}"}

    @staticmethod
    async def get_appointments(tenant: TenantContext, date_str: str, caller_phone: str, caller_role: str) -> dict:
        logger.info(f"Listing appointments for {date_str} (Role: {caller_role})")
        return await NativeSchedulingService.get_appointments(tenant, date_str, caller_phone, caller_role)
