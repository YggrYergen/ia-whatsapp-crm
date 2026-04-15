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
#     CALENDAR TOOLS (5): Return realistic simulated responses.
#       → When the new calendar backend is ready, swap implementations.
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
        # ── SIMULATED CALENDAR TOOLS ──────────────────────────
        if tool_name == "get_merged_availability":
            return _simulate_availability(arguments)
        
        elif tool_name == "book_round_robin":
            return _simulate_booking(arguments)
        
        elif tool_name == "update_appointment":
            return _simulate_update(arguments)
        
        elif tool_name == "delete_appointment":
            return _simulate_delete(arguments)
        
        elif tool_name == "get_my_appointments":
            return _simulate_list_appointments(arguments)
        
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
# SIMULATED CALENDAR TOOLS
# These return realistic responses that look exactly like the
# production GoogleCalendarClient responses, but are generated
# deterministically (no external API calls).
#
# When the new calendar backend is ready (Sprint 2+), replace
# these with real implementations.
# ─────────────────────────────────────────────────────────────

def _simulate_availability(args: Dict[str, Any]) -> str:
    """Simulates get_merged_availability — returns realistic time slots."""
    date_str = args.get("date_str", "")
    duration = args.get("duration_minutes") or 30
    
    # Generate a realistic set of available slots
    # Vary by date to feel "real" (different days have different availability)
    all_slots = [
        "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
        "12:00", "14:00", "14:30", "15:00", "15:30", "16:00",
        "16:30", "17:00", "17:30"
    ]
    
    # Use the date string as a seed for deterministic but varied results
    seed = sum(ord(c) for c in date_str) if date_str else 42
    rng = random.Random(seed)
    
    # Pick 4-8 slots as "available" (realistically, not all slots are free)
    num_available = rng.randint(4, 8)
    available = sorted(rng.sample(all_slots, min(num_available, len(all_slots))))
    
    return json.dumps({
        "status": "success",
        "available_slots": available,
        "duration": duration,
        "message": f"Se encontraron {len(available)} horarios disponibles para el {date_str}."
    })


def _simulate_booking(args: Dict[str, Any]) -> str:
    """Simulates book_round_robin — returns a successful booking confirmation."""
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    user_name = args.get("user_name", "Cliente")
    phone = args.get("phone", "")
    duration = args.get("duration_minutes", 30)
    
    # Simulate which "team/unit" gets assigned (round-robin feel)
    seed = sum(ord(c) for c in f"{date_str}{time_str}") if date_str else 1
    unit_num = (seed % 3) + 1
    unit_label = f"Equipo {unit_num}"
    
    return json.dumps({
        "status": "success",
        "message": f"Cita agendada con éxito. {user_name} tiene una cita el {date_str} a las {time_str} ({duration} min) asignada a {unit_label}.",
        "box_label": unit_label,
        "event_link": None  # Simulated — no real calendar link
    })


def _simulate_update(args: Dict[str, Any]) -> str:
    """Simulates update_appointment — returns a successful reschedule."""
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    new_date = args.get("new_date", "")
    new_time = args.get("new_time", "")
    user_name = args.get("user_name", "Cliente")
    
    return json.dumps({
        "status": "success",
        "message": f"Cita re-agendada exitosamente. La cita de {user_name} se movió del {date_str} {time_str} al {new_date} a las {new_time}."
    })


def _simulate_delete(args: Dict[str, Any]) -> str:
    """Simulates delete_appointment — returns a successful cancellation."""
    date_str = args.get("date_str", "")
    time_str = args.get("time_str", "")
    
    return json.dumps({
        "status": "success",
        "message": f"La cita del {date_str} a las {time_str} ha sido cancelada exitosamente.",
        "items": [f"Cita cancelada: {date_str} a las {time_str}"]
    })


def _simulate_list_appointments(args: Dict[str, Any]) -> str:
    """Simulates get_my_appointments — returns a realistic appointment list."""
    date_str = args.get("date_str", "")
    
    # Use date as seed for deterministic results
    seed = sum(ord(c) for c in date_str) if date_str else 42
    rng = random.Random(seed)
    
    num_appointments = rng.randint(0, 3)
    
    if num_appointments == 0:
        return json.dumps({
            "status": "success",
            "message": f"No hay citas agendadas para el {date_str}."
        })
    
    times = sorted(rng.sample(["09:00", "10:30", "11:00", "14:00", "15:30", "16:00"], min(num_appointments, 6)))
    names = rng.sample(["Juan Pérez", "María González", "Carlos López", "Ana Rodríguez", "Pedro Silva"], min(num_appointments, 5))
    
    appointments = []
    for i, (t, name) in enumerate(zip(times, names)):
        end_h = int(t.split(":")[0])
        end_m = int(t.split(":")[1]) + 30
        if end_m >= 60:
            end_h += 1
            end_m -= 60
        end_time = f"{end_h:02d}:{end_m:02d}"
        unit = f"Equipo {(i % 3) + 1}"
        appointments.append(f"[{t} - {end_time}] {unit}: Cita - {name}")
    
    return json.dumps({
        "status": "success",
        "message": "Citas encontradas:\n" + "\n".join(appointments)
    })


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
