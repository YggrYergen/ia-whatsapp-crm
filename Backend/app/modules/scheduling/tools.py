from typing import Dict, Any
import json
import asyncio
import sentry_sdk
from app.modules.intelligence.tools.base import AITool
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
from app.modules.scheduling.services import SchedulingService

class CheckAvailabilityTool(AITool):
    name = "get_merged_availability"
    description = "Busca disponibilidad en Google Calendar (Round-Robin Boxes) para una fecha (YYYY-MM-DD)."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                        "duration_minutes": {"type": ["integer", "null"], "description": "Duración de la cita en minutos (30 o 60). Null = 30 min por defecto."}
                    },
                    "required": ["date_str", "duration_minutes"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        date_str = kwargs.get("date_str")
        duration_minutes = kwargs.get("duration_minutes", 30)
        try:
            res = await SchedulingService.check_availability(tenant, date_str, duration_minutes)
            return json.dumps(res)
        except Exception as e:
            tenant_id = tenant.id if tenant else "unknown"
            logger.error(f"[CheckAvailabilityTool] Failed for tenant={tenant_id}, date={date_str}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "date_str": date_str, "duration": duration_minutes})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ CheckAvailabilityTool Failed | Tenant {tenant_id}",
                description=f"date={date_str}, duration={duration_minutes}min\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error checking availability: {str(e)}"})

class CheckMyAppointmentsTool(AITool):
    name = "get_my_appointments"
    description = "Consulta qué citas hay agendadas en un día específico. Muestra las citas personales del usuario, o toda la agenda si tiene rol de staff."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Fecha a consultar YYYY-MM-DD"}
                    },
                    "required": ["date_str"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        caller_phone = kwargs.get("caller_phone", "")
        caller_role = kwargs.get("caller_role", "cliente")
        date_str = kwargs.get("date_str")
        try:
            res = await SchedulingService.get_appointments(tenant, date_str, caller_phone, caller_role)
            return json.dumps(res)
        except Exception as e:
            tenant_id = tenant.id if tenant else "unknown"
            logger.error(f"[CheckMyAppointmentsTool] Failed for tenant={tenant_id}, date={date_str}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "date_str": date_str, "caller_phone": caller_phone})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ CheckMyAppointmentsTool Failed | Tenant {tenant_id}",
                description=f"date={date_str}, phone={caller_phone}\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error listing appointments: {str(e)}"})

class BookAppointmentTool(AITool):
    name = "book_round_robin"
    description = (
        "Agenda una cita rotando entre boxes. Requiere fecha, hora, nombre del servicio, nombre y teléfono. "
        "La duración se resuelve automáticamente según el servicio. Si no se especifica servicio, "
        "se usa la duración por defecto del negocio."
    )
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                        "time_str": {"type": "string", "description": "HH:MM"},
                        "service_name": {"type": ["string", "null"], "description": "Nombre del servicio (ej: 'Sesión de Diagnóstico', 'Tratamiento CelluDetox Pack'). Null si el cliente no especifica."},
                        "duration_minutes": {"type": ["integer", "null"], "description": "Duración en minutos. Null = se resuelve automáticamente del servicio o configuración."},
                        "user_name": {"type": "string", "description": "Nombre del paciente"},
                        "phone": {"type": "string", "description": "Teléfono del paciente"}
                    },
                    "required": ["date_str", "time_str", "service_name", "duration_minutes", "user_name", "phone"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        date_str = kwargs.get("date_str")
        time_str = kwargs.get("time_str")
        user_name = kwargs.get("user_name", "Desconocido")
        phone = kwargs.get("phone", "unknown")
        service_name = kwargs.get("service_name")
        duration = kwargs.get("duration_minutes")
        
        tenant_id = tenant.id if tenant else "unknown"
        
        # Auto-resolve duration from service_name if not explicitly provided
        # This ensures appointments always get the correct duration for their service
        if service_name and not duration:
            try:
                from app.infrastructure.database.supabase_client import SupabasePooler
                db = await SupabasePooler.get_client()
                svc_res = await (
                    db.table("tenant_services")
                    .select("duration_minutes, name")
                    .eq("tenant_id", tenant_id)
                    .ilike("name", f"%{service_name}%")
                    .eq("is_active", True)
                    .limit(1)
                    .execute()
                )
                if svc_res.data:
                    duration = svc_res.data[0].get("duration_minutes", 30)
                    # Use the canonical service name from DB
                    service_name = svc_res.data[0].get("name", service_name)
                    logger.info(
                        f"[BookAppointmentTool] Auto-resolved service='{service_name}' → "
                        f"duration={duration}min | tenant={tenant_id}"
                    )
                else:
                    logger.warning(
                        f"[BookAppointmentTool] Service '{service_name}' not found for "
                        f"tenant={tenant_id}, using default duration"
                    )
                    sentry_sdk.add_breadcrumb(
                        category="scheduling",
                        message=f"Service '{service_name}' not found, using default",
                        level="warning",
                    )
            except Exception as svc_err:
                logger.warning(f"[BookAppointmentTool] Service lookup failed: {svc_err}")
                sentry_sdk.add_breadcrumb(
                    category="scheduling", message=f"Service lookup failed: {svc_err}",
                    level="warning",
                )
        
        # Final fallback: use default from scheduling_config or 30
        if not duration:
            duration = 30
        
        try:
            res = await SchedulingService.book_appointment(
                tenant, date_str, time_str, duration, user_name, phone,
                service_name=service_name
            )
            return json.dumps(res)
        except Exception as e:
            logger.error(f"[BookAppointmentTool] Failed for tenant={tenant_id}, {date_str} {time_str}, patient={user_name}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "date_str": date_str, "time_str": time_str, "user_name": user_name, "phone": phone, "service_name": service_name, "duration": duration})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ BookAppointmentTool Failed | Tenant {tenant_id}",
                description=f"date={date_str} {time_str}, patient={user_name}, phone={phone}, service={service_name}\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error booking appointment: {str(e)}"})

class UpdateAppointmentTool(AITool):
    name = "update_appointment"
    description = "Modifica y re-agenda una cita existente."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Fecha original YYYY-MM-DD"},
                        "time_str": {"type": "string", "description": "Hora original HH:MM"},
                        "new_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD"},
                        "new_time": {"type": "string", "description": "Nueva hora HH:MM"},
                        "phone": {"type": "string", "description": "Teléfono del paciente"},
                        "user_name": {"type": "string", "description": "Nombre del paciente"}
                    },
                    "required": ["date_str", "time_str", "new_date", "new_time", "phone", "user_name"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        date_str = kwargs.get("date_str")
        time_str = kwargs.get("time_str")
        new_date = kwargs.get("new_date")
        new_time = kwargs.get("new_time")
        phone = kwargs.get("phone")
        user_name = kwargs.get("user_name")
        try:
            res = await SchedulingService.update_appointment(tenant, date_str, time_str, new_date, new_time, phone, user_name)
            return json.dumps(res)
        except Exception as e:
            tenant_id = tenant.id if tenant else "unknown"
            logger.error(f"[UpdateAppointmentTool] Failed for tenant={tenant_id}, {date_str} {time_str} → {new_date} {new_time}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "date_str": date_str, "time_str": time_str, "new_date": new_date, "new_time": new_time, "phone": phone})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ UpdateAppointmentTool Failed | Tenant {tenant_id}",
                description=f"{date_str} {time_str} → {new_date} {new_time}, phone={phone}\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error updating appointment: {str(e)}"})

class DeleteAppointmentTool(AITool):
    name = "delete_appointment"
    description = "Cancela una cita existente asociada al celular. Se requiere fecha y hora exacta."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "YYYY-MM-DD"}, 
                        "time_str": {"type": "string", "description": "HH:MM"}, 
                        "phone": {"type": ["string", "null"], "description": "Teléfono de un tercero. Solo si un agente staff pide borrar la cita de otro. Null si el cliente borra su propia cita."}
                    },
                    "required": ["date_str", "time_str", "phone"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        caller_phone = kwargs.get("caller_phone", "")
        caller_role = kwargs.get("caller_role", "cliente")
        time_str = kwargs.get("time_str", "00:00")
        date_str = kwargs.get("date_str")
        
        # ZERO-TRUST + RBAC (Role-Based Access Control)
        if caller_role in ["admin", "staff"]:
            target_phone = kwargs.get("phone", "")
        else:
            target_phone = caller_phone
        
        try:
            res = await SchedulingService.cancel_appointment(tenant, date_str, time_str, target_phone)
            return json.dumps(res)
        except Exception as e:
            tenant_id = tenant.id if tenant else "unknown"
            logger.error(f"[DeleteAppointmentTool] Failed for tenant={tenant_id}, {date_str} {time_str}, phone={target_phone}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "date_str": date_str, "time_str": time_str, "target_phone": target_phone, "caller_role": caller_role})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ DeleteAppointmentTool Failed | Tenant {tenant_id}",
                description=f"date={date_str} {time_str}, phone={target_phone}, role={caller_role}\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error cancelling appointment: {str(e)}"})

class EscalateHumanTool(AITool):
    name = "request_human_escalation"
    description = "Pausa atención automática de la IA y notifica a un humano inmediatamente para intervención manual."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string", "description": "Razón por la que se necesita intervención humana"},
                        "patient_phone": {"type": ["string", "null"], "description": "Teléfono del paciente. Null si no se conoce."}
                    },
                    "required": ["reason", "patient_phone"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        patient_phone = kwargs.get("caller_phone", "unknown")
        reason = kwargs.get("reason", "Usuario requiere ayuda extrema humana")
        
        if tenant:
            from app.infrastructure.database.supabase_client import SupabasePooler
            try:
                db = await SupabasePooler.get_client()
                # Use caller_phone to ensure we mute the correct person
                await db.table("contacts").update({"bot_active": False}).eq("phone_number", patient_phone).eq("tenant_id", tenant.id).execute()
            except Exception as e:
                logger.error(f"[EscalateTool] Failed to mute bot for {patient_phone}: {e}")
                sentry_sdk.capture_exception(e)
                await send_discord_alert(
                    title=f"❌ EscalateTool: Bot Mute Failed | {patient_phone}",
                    description=f"Failed to set bot_active=False for {patient_phone}: {str(e)[:300]}",
                    severity="error",
                    error=e
                )
        
        try:
            res = await SchedulingService.request_human_escalation(tenant, patient_phone, reason)
            return json.dumps(res)
        except Exception as e:
            tenant_id = tenant.id if tenant else "unknown"
            logger.error(f"[EscalateTool] Escalation service failed for {patient_phone}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant_id, "patient_phone": patient_phone, "reason": reason[:100]})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ EscalateTool: Escalation Failed | {patient_phone}",
                description=f"phone={patient_phone}, reason={reason[:200]}\nError: {str(e)[:300]}",
                severity="error", error=e
            )
            return json.dumps({"status": "error", "message": f"Error during escalation: {str(e)}"})

class UpdatePatientScoringTool(AITool):
    name = "update_patient_scoring"
    description = "Actualiza el puntaje de Scoring CelluDetox (4-20) y metadatos clínicos del paciente en la base de datos."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string", "description": "Teléfono del paciente"},
                        "score": {"type": "integer", "description": "Puntaje calculado (4 a 20)"},
                        "clinical_notes": {"type": ["string", "null"], "description": "Resumen breve de hallazgos clínicos. Null si no hay notas."}
                    },
                    "required": ["phone", "score", "clinical_notes"],
                    "additionalProperties": False
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        phone = kwargs.get("phone")
        score = kwargs.get("score")
        notes = kwargs.get("clinical_notes", "")
        
        if not tenant:
            logger.warning(f"[ScoringTool] Called without tenant context for phone={phone}")
            sentry_sdk.capture_message(f"ScoringTool called without tenant context, phone={phone}", level="warning")
            return json.dumps({"status": "error", "message": "No tenant context"})
        
        from app.infrastructure.database.supabase_client import SupabasePooler
        try:
            db = await SupabasePooler.get_client()
            # Update metadata jsonb field
            res = await db.table("contacts").update({
                "metadata": {
                    "celludetox_score": score,
                    "last_assessment_notes": notes,
                    "updated_at": "now"
                },
                "status": "lead_qualified" if score >= 8 else "lead"
            }).eq("phone_number", phone).eq("tenant_id", tenant.id).execute()
            return json.dumps({"status": "success", "message": f"Score {score} actualizado para {phone}"})
        except Exception as e:
            logger.error(f"[ScoringTool] Failed to update score for {phone}: {e}")
            sentry_sdk.set_context("tool_execution", {"tool": self.name, "tenant_id": tenant.id, "phone": phone, "score": score})
            sentry_sdk.capture_exception(e)
            await send_discord_alert(
                title=f"❌ ScoringTool: Update Failed | {phone}",
                description=f"phone={phone}, score={score}, tenant={tenant.id}\nError: {str(e)[:300]}",
                severity="error",
                error=e
            )
            return json.dumps({"status": "error", "message": str(e)})

