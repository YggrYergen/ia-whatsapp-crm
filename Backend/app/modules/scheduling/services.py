from app.infrastructure.telemetry.logger_service import logger
from app.core.models import TenantContext
from app.core.event_bus import event_bus
from app.infrastructure.calendar.google_client import GoogleCalendarClient

class SchedulingService:
    @staticmethod
    async def check_availability(tenant: TenantContext, date_str: str, duration_minutes: int) -> dict:
        logger.info(f"Checking Google Calendar availability for {date_str}")
        return await GoogleCalendarClient.get_merged_availability(tenant, date_str, duration_minutes)

    @staticmethod
    async def book_appointment(tenant: TenantContext, date_str: str, time_str: str, duration_minutes: int, user_name: str, patient_phone: str) -> dict:
        logger.info(f"Booking {patient_phone} at {date_str} {time_str}")
        res = await GoogleCalendarClient.book_round_robin(tenant, date_str, time_str, duration_minutes, user_name, patient_phone)
        if res.get("status") == "success":
            payload = {
                "tenant_id": tenant.id,
                "patient_phone": patient_phone,
                "reason": f"NUEVA CITA AGENDADA: El paciente {user_name} agendó para el {date_str} a las {time_str} en {res.get('box_label')}.",
                "staff_number": "+56999999999"
            }
            await event_bus.publish("system_alert", payload)
        return res

    @staticmethod
    async def update_appointment(tenant: TenantContext, date_str: str, time_str: str, new_date: str, new_time: str, patient_phone: str, user_name: str) -> dict:
        del_res = await GoogleCalendarClient.delete_appointment(tenant, date_str, time_str, patient_phone)
        if del_res.get("status") == "error":
            return {"status": "error", "message": f"No se pudo reagendar. Falló cancelación previa: {del_res.get('message')}"}
        
        book_res = await GoogleCalendarClient.book_round_robin(tenant, new_date, new_time, 30, user_name, patient_phone)
        if book_res.get("status") == "success":
            payload = {
                "tenant_id": tenant.id,
                "patient_phone": patient_phone,
                "reason": f"CITA RE-AGENDADA: El paciente {user_name} movió su bloque del {date_str} {time_str} para el {new_date} a las {new_time}.",
                "staff_number": "+56999999999"
            }
            await event_bus.publish("system_alert", payload)
            return {"status": "success", "message": "Cita re-agendada exitosamente en el calendario oficial."}
        return book_res

    @staticmethod
    async def cancel_appointment(tenant: TenantContext, date_str: str, time_str: str, patient_phone: str) -> dict:
        logger.info(f"Cancelling appointment for {patient_phone} at {date_str} {time_str}")
        res = await GoogleCalendarClient.delete_appointment(tenant, date_str, time_str, patient_phone)
        if res.get("status") == "success":
            items = res.get("items", [])
            if not items:
                items = [res.get("details", "")]
                
            for item_desc in items:
                payload = {
                    "tenant_id": tenant.id,
                    "patient_phone": patient_phone,
                    "reason": f"CITA CANCELADA del {date_str} a las {time_str}.\nDetalle: {item_desc}",
                    "staff_number": "+56999999999"
                }
                await event_bus.publish("system_alert", payload)
        return res

    @staticmethod
    async def request_human_escalation(tenant: TenantContext, patient_phone: str, reason: str) -> dict:
        logger.info(f"Escalation requested for {patient_phone}: {reason}")
        payload = {
            "tenant_id": tenant.id,
            "patient_phone": patient_phone,
            "staff_number": "+56999999999",
            "reason": reason
        }
        await event_bus.publish("system_alert", payload)
        return {"status": "success", "message": "El Staff ya ha recibido tu mensaje de alerta en su bandeja de urgencias. Un agente humano se sumará a la intervención pronto."}

    @staticmethod
    async def get_appointments(tenant: TenantContext, date_str: str, caller_phone: str, caller_role: str) -> dict:
        logger.info(f"Listing appointments for {date_str} (Role: {caller_role})")
        return await GoogleCalendarClient.list_appointments(tenant, date_str, caller_phone, caller_role)
