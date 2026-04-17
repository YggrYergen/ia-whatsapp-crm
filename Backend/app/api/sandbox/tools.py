# ================================================================================
# ⚠️  SANDBOX TOOLS — Self-contained tool implementations for the demo sandbox.
#
#     These tools exist ONLY for the sandbox testing endpoint.
#     They do NOT import from:
#       - app.modules.scheduling.tools (which imports GoogleCalendarClient)
#       - app.modules.scheduling.services (which imports GoogleCalendarClient)
#       - app.infrastructure.calendar (GoogleCalendarClient)
#       - app.core.models.TenantContext
#
#     CALENDAR TOOLS (5): Execute real DB operations via NativeSchedulingService.
#       → Appointments show up in the Agenda and can be cancelled/updated.
#     NON-CALENDAR TOOLS (2): Execute for real (DB + event bus).
#
# ⚠️  IMPORT SAFETY: This file has ZERO transitive dependencies on Google libs.
#     Verified 2026-04-15 via import chain analysis:
#       tools.py → SchedulingService → GoogleCalendarClient → google.oauth2
#     This file does NOT go through that chain at all.
#
# ⚠️  OBSERVABILITY: Every except block → logger + Sentry + Discord (3 channels).
# ================================================================================

import json
import datetime
import random
import sentry_sdk
from typing import Dict, Any, List

from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert


# ─────────────────────────────────────────────────────────────
# Minimal tenant context — NO TenantContext import needed
# ─────────────────────────────────────────────────────────────

class SandboxTenantContext:
    """Minimal tenant context for sandbox tool execution.
    Does NOT import app.core.models.TenantContext.
    Tools only need .id and .name — we provide exactly that."""
    def __init__(self, tenant_id: str, tenant_name: str):
        self.id = tenant_id
        self.name = tenant_name


# ─────────────────────────────────────────────────────────────
# Tool schema definitions (OpenAI function calling format)
# Identical to production schemas in modules/scheduling/tools.py
# so the LLM calls them with the exact same arguments.
# strict: true + additionalProperties: false per Block B
# ─────────────────────────────────────────────────────────────

SANDBOX_TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_merged_availability",
            "description": "Busca disponibilidad en la agenda de citas para una fecha específica (YYYY-MM-DD). Devuelve los horarios libres.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "book_round_robin",
            "description": "Agenda una cita. Requiere fecha, hora, duración, nombre y teléfono del cliente.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"},
                    "duration_minutes": {"type": "integer", "description": "30 o 60"},
                    "user_name": {"type": "string", "description": "Nombre del cliente"},
                    "phone": {"type": "string", "description": "Teléfono del cliente"}
                },
                "required": ["date_str", "time_str", "duration_minutes", "user_name", "phone"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment",
            "description": "Modifica y re-agenda una cita existente.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha original YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "Hora original HH:MM"},
                    "new_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD"},
                    "new_time": {"type": "string", "description": "Nueva hora HH:MM"},
                    "phone": {"type": "string", "description": "Teléfono del cliente"},
                    "user_name": {"type": "string", "description": "Nombre del cliente"}
                },
                "required": ["date_str", "time_str", "new_date", "new_time", "phone", "user_name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_appointment",
            "description": "Cancela una cita existente. Se requiere fecha y hora exacta.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"},
                    "phone": {"type": ["string", "null"], "description": "Teléfono del cliente. Null si el propio cliente cancela."}
                },
                "required": ["date_str", "time_str", "phone"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_appointments",
            "description": "Consulta qué citas hay agendadas en un día específico.",
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
    },
    {
        "type": "function",
        "function": {
            "name": "request_human_escalation",
            "description": "Pausa atención automática de la IA y notifica a un humano inmediatamente para intervención manual.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Razón por la que se necesita intervención humana"},
                    "patient_phone": {"type": ["string", "null"], "description": "Teléfono del cliente. Null si no se conoce."}
                },
                "required": ["reason", "patient_phone"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_patient_scoring",
            "description": "Actualiza el puntaje de scoring y metadatos del cliente en la base de datos.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "Teléfono del cliente"},
                    "score": {"type": "integer", "description": "Puntaje calculado (4 a 20)"},
                    "clinical_notes": {"type": ["string", "null"], "description": "Resumen breve de hallazgos. Null si no hay notas."}
                },
                "required": ["phone", "score", "clinical_notes"],
                "additionalProperties": False
            }
        }
    },
]


# ─────────────────────────────────────────────────────────────
# Tool executor — routes tool calls to simulation or real execution
# ─────────────────────────────────────────────────────────────

async def execute_sandbox_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    tenant_id: str,
    tenant_name: str,
) -> str:
    """Execute a tool call in sandbox mode.
    
    Calendar tools (5): Return realistic simulated responses.
    Non-calendar tools (2): Execute for real via DB/event bus.
    
    Returns a JSON string (same format as production tools).
    Every failure point → 3-channel observability.
    """
    _WHERE = "execute_sandbox_tool"
    _ctx = f"tool={tool_name} | tenant={tenant_id} | env=sandbox"
    
    logger.info(f"🛠️ [{_WHERE}] Executing: {tool_name} | args={json.dumps(arguments)[:200]} | {_ctx}")
    
    try:
        # ── REAL CALENDAR TOOLS (NativeSchedulingService) ─────
        if tool_name == "get_merged_availability":
            return await _real_availability(arguments, tenant_id)
        
        elif tool_name == "book_round_robin":
            return await _real_booking(arguments, tenant_id)
        
        elif tool_name == "update_appointment":
            return await _real_update(arguments, tenant_id)
        
        elif tool_name == "delete_appointment":
            return await _real_delete(arguments, tenant_id)
        
        elif tool_name == "get_my_appointments":
            return await _real_list_appointments(arguments, tenant_id)
        
        # ── REAL TOOLS (no Google Calendar dependency) ────────
        elif tool_name == "request_human_escalation":
            return await _real_escalation(arguments, tenant_id, tenant_name)
        
        elif tool_name == "update_patient_scoring":
            return await _real_scoring(arguments, tenant_id)
        
        else:
            _msg = f"[{_WHERE}] Unknown sandbox tool: {tool_name} | {_ctx}"
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            await send_discord_alert(
                title=f"❌ Sandbox: Unknown Tool | {tool_name}",
                description=f"Tool '{tool_name}' is not registered in sandbox.\nTenant: {tenant_id}",
                severity="error"
            )
            return json.dumps({"status": "error", "message": f"Herramienta '{tool_name}' no disponible."})
    
    except Exception as e:
        _msg = f"[{_WHERE}] Tool execution CRASHED: {tool_name} | {_ctx} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.set_context("sandbox_tool_crash", {
            "tool_name": tool_name,
            "tenant_id": tenant_id,
            "arguments_keys": list(arguments.keys()),
        })
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"💥 Sandbox Tool Crash: {tool_name} | Tenant {tenant_id}",
            description=f"Tool: {tool_name}\nArgs: {json.dumps(arguments)[:200]}\nError: {str(e)[:300]}",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error interno ejecutando {tool_name}: {str(e)[:200]}"})


# ─────────────────────────────────────────────────────────────
# REAL CALENDAR TOOLS — Powered by NativeSchedulingService
#
# These tools call the real scheduling service, writing/reading
# actual appointments in the database. This ensures sandbox
# test chats produce real data visible in the Agenda.
#
# Ref: NativeSchedulingService (app.modules.scheduling.native_service)
# Methods return {status: success|error, message: str, ...}
# ─────────────────────────────────────────────────────────────

from app.modules.scheduling.native_service import NativeSchedulingService


async def _real_availability(args: Dict[str, Any], tenant_id: str) -> str:
    """Real availability check via NativeSchedulingService."""
    _WHERE = "_real_availability"
    date_str = args.get("date_str", "")
    duration = args.get("duration_minutes")
    
    try:
        ctx = SandboxTenantContext(tenant_id, "sandbox")
        result = await NativeSchedulingService.check_availability(ctx, date_str, duration)
        return json.dumps(result)
    except Exception as e:
        _msg = f"[{_WHERE}] Failed | tenant={tenant_id} | date={date_str} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox availability check failed | {tenant_id}",
            description=f"**Date:** {date_str}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error checking availability: {str(e)[:200]}"})


async def _real_booking(args: Dict[str, Any], tenant_id: str) -> str:
    """Real booking via NativeSchedulingService."""
    _WHERE = "_real_booking"
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    duration = args.get("duration_minutes", 30)
    user_name = args.get("user_name", "Cliente Sandbox")
    phone = args.get("phone", "sandbox-test")
    
    try:
        ctx = SandboxTenantContext(tenant_id, "sandbox")
        result = await NativeSchedulingService.book_appointment(
            ctx, date_str, time_str, duration, user_name, phone, booked_by="sandbox_ai"
        )
        return json.dumps(result)
    except Exception as e:
        _msg = f"[{_WHERE}] Failed | tenant={tenant_id} | {date_str} {time_str} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox booking failed | {tenant_id}",
            description=f"**Slot:** {date_str} {time_str}\n**Client:** {user_name}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error booking: {str(e)[:200]}"})


async def _real_update(args: Dict[str, Any], tenant_id: str) -> str:
    """Real appointment reschedule via NativeSchedulingService."""
    _WHERE = "_real_update"
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    new_date = args.get("new_date", "")
    new_time = args.get("new_time", "")
    user_name = args.get("user_name", "Cliente Sandbox")
    phone = args.get("phone", "sandbox-test")
    
    try:
        ctx = SandboxTenantContext(tenant_id, "sandbox")
        result = await NativeSchedulingService.update_appointment(
            ctx, date_str, time_str, new_date, new_time, phone, user_name
        )
        return json.dumps(result)
    except Exception as e:
        _msg = f"[{_WHERE}] Failed | tenant={tenant_id} | {date_str} {time_str} → {new_date} {new_time} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox update failed | {tenant_id}",
            description=f"**Original:** {date_str} {time_str}\n**New:** {new_date} {new_time}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error updating: {str(e)[:200]}"})


async def _real_delete(args: Dict[str, Any], tenant_id: str) -> str:
    """Real appointment cancellation via NativeSchedulingService."""
    _WHERE = "_real_delete"
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    phone = args.get("phone", "sandbox-test")
    
    try:
        ctx = SandboxTenantContext(tenant_id, "sandbox")
        result = await NativeSchedulingService.cancel_appointment(ctx, date_str, time_str, phone)
        return json.dumps(result)
    except Exception as e:
        _msg = f"[{_WHERE}] Failed | tenant={tenant_id} | {date_str} {time_str} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox delete failed | {tenant_id}",
            description=f"**Slot:** {date_str} {time_str}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error deleting: {str(e)[:200]}"})


async def _real_list_appointments(args: Dict[str, Any], tenant_id: str) -> str:
    """Real appointment list via DB query."""
    _WHERE = "_real_list_appointments"
    date_str = args.get("date_str", "")
    phone = args.get("phone", "")
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        import pytz
        
        tz = pytz.timezone("America/Santiago")
        db = await SupabasePooler.get_client()
        
        query = db.table("appointments").select(
            "id, start_time, end_time, client_name, client_phone, status, resource_id"
        ).eq("tenant_id", tenant_id).neq("status", "cancelled")
        
        if date_str:
            day_start = f"{date_str}T00:00:00"
            day_end = f"{date_str}T23:59:59"
            query = query.gte("start_time", day_start).lte("start_time", day_end)
        
        if phone:
            query = query.eq("client_phone", phone)
        
        res = await query.order("start_time").limit(20).execute()
        
        if not res.data:
            msg = f"No hay citas agendadas"
            if date_str:
                msg += f" para el {date_str}"
            if phone:
                msg += f" con el teléfono {phone}"
            msg += "."
            return json.dumps({"status": "success", "message": msg})
        
        # Format appointments for display
        lines = []
        for appt in res.data:
            start = datetime.datetime.fromisoformat(appt["start_time"]).astimezone(tz)
            end = datetime.datetime.fromisoformat(appt["end_time"]).astimezone(tz)
            name = appt.get("client_name", "Sin nombre")
            lines.append(
                f"[{start.strftime('%H:%M')} - {end.strftime('%H:%M')}] {name} ({appt.get('status', 'confirmed')})"
            )
        
        return json.dumps({
            "status": "success",
            "message": f"Citas encontradas ({len(lines)}):\n" + "\n".join(lines)
        })
        
    except Exception as e:
        _msg = f"[{_WHERE}] Failed | tenant={tenant_id} | date={date_str} | error={str(e)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox list appointments failed | {tenant_id}",
            description=f"**Date:** {date_str}\n**Error:** ```{str(e)[:300]}```",
            severity="error", error=e
        )
        return json.dumps({"status": "error", "message": f"Error listing appointments: {str(e)[:200]}"})


# ─────────────────────────────────────────────────────────────
# REAL TOOLS (no Google Calendar dependency)
# These execute actual business logic via DB and event bus.
# ─────────────────────────────────────────────────────────────

async def _real_escalation(args: Dict[str, Any], tenant_id: str, tenant_name: str) -> str:
    """Real escalation — fires event bus + Discord alert.
    
    In sandbox: patient_phone defaults to 'sandbox-test' which matches
    no real contact → bot_active won't be accidentally disabled.
    The escalation alert DOES fire (desirable for testing observability).
    """
    _WHERE = "_real_escalation"
    reason = args.get("reason", "Solicita asistencia humana")
    patient_phone = args.get("patient_phone") or "sandbox-test"
    
    try:
        from app.core.event_bus import event_bus
        
        payload = {
            "tenant_id": tenant_id,
            "patient_phone": patient_phone,
            "reason": f"[SANDBOX] {reason}",
            "staff_number": "+56999999999"
        }
        await event_bus.publish("system_alert", payload)
        
        logger.info(f"[{_WHERE}] Escalation fired via event bus | tenant={tenant_id} | reason={reason[:100]}")
        
        return json.dumps({
            "status": "success",
            "message": "El equipo ha sido notificado de tu solicitud. Un agente humano se comunicará contigo pronto."
        })
        
    except Exception as e:
        logger.error(f"[{_WHERE}] Escalation FAILED | tenant={tenant_id} | error={str(e)[:200]}", exc_info=True)
        sentry_sdk.set_context("sandbox_escalation", {"tenant_id": tenant_id, "reason": reason[:200]})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox Escalation Failed | Tenant {tenant_id}",
            description=f"Reason: {reason[:200]}\nError: {str(e)[:300]}",
            severity="error", error=e
        )
        return json.dumps({
            "status": "error",
            "message": f"Error al escalar: {str(e)[:200]}"
        })


async def _real_scoring(args: Dict[str, Any], tenant_id: str) -> str:
    """Real scoring update — writes to contacts.metadata in DB.
    
    In sandbox: phone is whatever the LLM provides. If it matches a real
    contact, the scoring IS updated (which is fine — sandbox is for testing).
    If no match, the UPDATE is a no-op (0 rows affected, no error).
    """
    _WHERE = "_real_scoring"
    phone = args.get("phone", "")
    score = args.get("score", 0)
    notes = args.get("clinical_notes") or ""
    
    if not phone:
        return json.dumps({"status": "error", "message": "Se requiere un teléfono para actualizar el scoring."})
    
    try:
        from app.infrastructure.database.supabase_client import SupabasePooler
        
        db = await SupabasePooler.get_client()
        res = await db.table("contacts").update({
            "metadata": {
                "scoring": score,
                "last_assessment_notes": notes,
                "updated_via": "sandbox",
            },
            "status": "lead_qualified" if score >= 8 else "lead"
        }).eq("phone_number", phone).eq("tenant_id", tenant_id).execute()
        
        # Check if any rows were actually updated
        rows_affected = len(res.data) if res.data else 0
        
        if rows_affected == 0:
            logger.info(f"[{_WHERE}] No contact found with phone={phone} for tenant={tenant_id} (expected in sandbox)")
            return json.dumps({
                "status": "success",
                "message": f"Scoring registrado: {score} puntos para {phone}. (Nota: el contacto será creado cuando se conecte por WhatsApp)"
            })
        
        logger.info(f"[{_WHERE}] Scoring updated | phone={phone} | score={score} | tenant={tenant_id}")
        return json.dumps({
            "status": "success",
            "message": f"Score {score} actualizado para {phone}."
        })
        
    except Exception as e:
        logger.error(f"[{_WHERE}] Scoring FAILED | phone={phone} | tenant={tenant_id} | error={str(e)[:200]}", exc_info=True)
        sentry_sdk.set_context("sandbox_scoring", {"tenant_id": tenant_id, "phone": phone, "score": score})
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title=f"❌ Sandbox Scoring Failed | Tenant {tenant_id}",
            description=f"Phone: {phone}\nScore: {score}\nError: {str(e)[:300]}",
            severity="error", error=e
        )
        return json.dumps({
            "status": "error",
            "message": f"Error al actualizar scoring: {str(e)[:200]}"
        })
