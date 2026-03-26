from typing import Dict, Any
import json
from app.modules.intelligence.tools.base import AITool
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
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                        "duration_minutes": {"type": "integer", "description": "Duración de la cita (30 o 60 min)"}
                    },
                    "required": ["date_str"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        date_str = kwargs.get("date_str")
        duration_minutes = kwargs.get("duration_minutes", 30)
        res = await SchedulingService.check_availability(tenant, date_str, duration_minutes)
        return json.dumps(res)

class CheckMyAppointmentsTool(AITool):
    name = "get_my_appointments"
    description = "Consulta qué citas hay agendadas en un día específico. Muestra las citas personales del usuario, o toda la agenda si tiene rol de staff."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "Fecha a consultar YYYY-MM-DD"}
                    },
                    "required": ["date_str"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        caller_phone = kwargs.get("caller_phone", "")
        caller_role = kwargs.get("caller_role", "cliente")
        res = await SchedulingService.get_appointments(tenant, kwargs.get("date_str"), caller_phone, caller_role)
        return json.dumps(res)

class BookAppointmentTool(AITool):
    name = "book_round_robin"
    description = "Agenda una cita rotando entre boxes. Requiere fecha, hora, duración, nombre y teléfono."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                        "time_str": {"type": "string", "description": "HH:MM"},
                        "duration_minutes": {"type": "integer", "description": "30 o 60"},
                        "user_name": {"type": "string", "description": "Nombre del paciente"},
                        "phone": {"type": "string", "description": "Teléfono del paciente"}
                    },
                    "required": ["date_str", "time_str", "duration_minutes", "user_name", "phone"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        res = await SchedulingService.book_appointment(tenant, kwargs.get("date_str"), kwargs.get("time_str"), kwargs.get("duration_minutes", 30), kwargs.get("user_name", "Desconocido"), kwargs.get("phone", "unknown"))
        return json.dumps(res)

class UpdateAppointmentTool(AITool):
    name = "update_appointment"
    description = "Modifica y re-agenda una cita existente."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string"}, "time_str": {"type": "string"},
                        "new_date": {"type": "string"}, "new_time": {"type": "string"},
                        "phone": {"type": "string"}, "user_name": {"type": "string"}
                    },
                    "required": ["date_str", "time_str", "new_date", "new_time", "phone", "user_name"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        res = await SchedulingService.update_appointment(tenant, kwargs.get("date_str"), kwargs.get("time_str"), kwargs.get("new_date"), kwargs.get("new_time"), kwargs.get("phone"), kwargs.get("user_name"))
        return json.dumps(res)

class DeleteAppointmentTool(AITool):
    name = "delete_appointment"
    description = "Cancela una cita existente asociada al celular. Se requiere fecha y hora exacta."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date_str": {"type": "string", "description": "YYYY-MM-DD"}, 
                        "time_str": {"type": "string", "description": "HH:MM"}, 
                        "phone": {"type": "string", "description": "Solo utilízalo si un agente del staff te pide borrar la cita de un tercero."}
                    },
                    "required": ["date_str", "time_str"] 
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        caller_phone = kwargs.get("caller_phone", "")
        caller_role = kwargs.get("caller_role", "cliente")
        time_str = kwargs.get("time_str", "00:00")
        
        # ZERO-TRUST + RBAC (Role-Based Access Control)
        if caller_role in ["admin", "staff"]:
            target_phone = kwargs.get("phone", "")
        else:
            target_phone = caller_phone
            
        res = await SchedulingService.cancel_appointment(tenant, kwargs.get("date_str"), time_str, target_phone)
        return json.dumps(res)

class EscalateHumanTool(AITool):
    name = "escalate_to_human"
    description = "Pausa atención automática y notifica a un humano."
    def get_schema(self, provider: str) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {"type": "string"}, "patient_phone": {"type": "string"}
                    },
                    "required": ["reason"]
                }
            }
        }
    async def execute(self, **kwargs) -> str:
        tenant = kwargs.get("tenant_context")
        patient_phone = kwargs.get("patient_phone", "unknown")
        
        # Opcional: Auto-apagar bot a nivel BD al mutear.
        if tenant:
            from app.infrastructure.database.supabase_client import SupabasePooler
            try:
                db = SupabasePooler.get_client()
                db.table("contacts").update({"bot_active": False}).eq("phone_number", patient_phone).execute()
            except Exception as e:
                pass
                
        res = await SchedulingService.request_human_escalation(tenant, patient_phone, kwargs.get("reason", "Usuario requiere ayuda extrema humana"))
        return json.dumps(res)
