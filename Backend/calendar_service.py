import os
import json
import datetime
import pytz
from logger import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
# IDs de los calendarios para Round-Robin
BOX1_ID = '934af5bfb378ec7c1dd531aeb5095246f4cd2fd42ad5a77f715ff6f102d5c884@group.calendar.google.com'
BOX2_ID = 'c18d3c64564d57a86f04b2810573620b676e62ecfc62f130b4e5848d746a157e@group.calendar.google.com'

SERVICE_ACCOUNT_FILE = r'D:\WebDev\IA\backend\casavitacure-crm-1b7950d2fa11.json'
TIMEZONE = "America/Santiago"

def get_calendar_service():
    """Builds and returns the Google Calendar service using the Service Account."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_merged_availability(date_str: str, duration_minutes: int = 30) -> str:
    """
    Busca disponibilidad real en ambos boxes (Box 1 y Box 2) simultáneamente.
    Retorna los slots donde al menos uno de los dos esté libre.
    """
    logger.info(f"Checking Merged Availability (RR) for {date_str} ({duration_minutes} min)")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        # Parseo de fecha
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Limites del día: 09:00 AM a 18:30 PM (para permitir bloques de 30-60m)
        time_min = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(9, 0))).isoformat()
        time_max = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(19, 0))).isoformat()
        
        # Consultar FreeBusy
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": BOX1_ID}, {"id": BOX2_ID}]
        }
        
        freebusy_res = service.freebusy().query(body=body).execute()
        
        # Extraer ocupados de cada calendario
        busy_box1 = freebusy_res['calendars'][BOX1_ID]['busy']
        busy_box2 = freebusy_res['calendars'][BOX2_ID]['busy']
        
        # Helper para convertir rangos FreeBusy a datetimes
        def parse_busy(busy_list):
            ranges = []
            for item in busy_list:
                start = datetime.datetime.fromisoformat(item['start'].replace('Z', '+00:00'))
                end = datetime.datetime.fromisoformat(item['end'].replace('Z', '+00:00'))
                ranges.append((start, end))
            return ranges

        ranges1 = parse_busy(busy_box1)
        ranges2 = parse_busy(busy_box2)
        
        # Generar slots potenciales
        all_slots = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00"
        ]
        
        available_slots = []
        
        for slot in all_slots:
            slot_time = datetime.datetime.strptime(slot, "%H:%M").time()
            slot_start = local_tz.localize(datetime.datetime.combine(target_date, slot_time))
            slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
            
            # Check overlap in both
            def is_busy(start, end, ranges):
                for b_start, b_end in ranges:
                    if max(start, b_start) < min(end, b_end):
                        return True
                return False

            box1_busy = is_busy(slot_start, slot_end, ranges1)
            box2_busy = is_busy(slot_start, slot_end, ranges2)
            
            # Si al menos uno está libre, lo agregamos
            if not box1_busy or not box2_busy:
                available_slots.append(slot)
        
        return json.dumps({
            "status": "success",
            "available_slots": available_slots,
            "duration": duration_minutes,
            "message": f"Se encontraron {len(available_slots)} horarios disponibles para {duration_minutes} min."
        })

    except Exception as e:
        logger.exception(f"Error checking merged availability: {str(e)}")
        return json.dumps({"status": "error", "message": str(e)})

def book_round_robin(date_str: str, time_str: str, duration_minutes: int, user_name: str, phone: str) -> str:
    """
    Agendamiento Round-Robin: Box 1 primero, si no Box 2.
    """
    logger.info(f"Booking RR for {user_name} on {date_str} at {time_str} ({duration_minutes} min)")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        start_dt = local_tz.localize(datetime.datetime.combine(target_date, start_time))
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        
        # Consultar disponibilidad de los dos boxes exactos para este bloque
        body = {
            "timeMin": start_dt.isoformat(),
            "timeMax": end_dt.isoformat(),
            "items": [{"id": BOX1_ID}, {"id": BOX2_ID}]
        }
        fb_res = service.freebusy().query(body=body).execute()
        
        # Decidir destino
        target_calendar_id = None
        if not fb_res['calendars'][BOX1_ID]['busy']:
            target_calendar_id = BOX1_ID
            box_label = "Box 1"
        elif not fb_res['calendars'][BOX2_ID]['busy']:
            target_calendar_id = BOX2_ID
            box_label = "Box 2"
        else:
            return json.dumps({"status": "error", "message": "Lo siento, ese horario acaba de ocuparse en ambos boxes."})
            
        # Crear evento
        event = {
            'summary': f'Cita ({box_label}) - {user_name}',
            'description': f'Paciente: {user_name}\nTeléfono: {phone}\nDuración: {duration_minutes} min\nAgendado por Synapse AI 🤖',
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': TIMEZONE},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': TIMEZONE},
            'colorId': '1' if box_label == "Box 1" else '2',
        }
        
        res = service.events().insert(calendarId=target_calendar_id, body=event).execute()
        
        # NOTIFICACIÓN AL STAFF (Feedback v2)
        try:
            from whatsapp_service import send_whatsapp_message
            STAFF_NUMBER = os.getenv("STAFF_NOTIFICATION_NUMBER", "56999999999") # Fallback a simulación
            W_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
            W_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
            
            notif_body = (
                f"📅 *NUEVA CITA AGENDADA*\n\n"
                f"👤 Paciente: {user_name}\n"
                f"📞 Tel: {phone}\n"
                f"⏰ {date_str} a las {time_str}\n"
                f"🏢 Ubicación: {box_label}\n\n"
                f"🔗 Link: {res.get('htmlLink')}"
            )
            
            import asyncio
            asyncio.create_task(send_whatsapp_message(STAFF_NUMBER, notif_body, W_ID, W_TOKEN))
        except Exception as ex:
            logger.error(f"Error notifying staff: {str(ex)}")

        return json.dumps({
            "status": "success",
            "message": f"¡Confirmado! Agendado en {box_label} para el {date_str} a las {time_str}.",
            "event_link": res.get('htmlLink')
        })
        
    except Exception as e:
        logger.exception(f"Error in book_round_robin: {str(e)}")
        return json.dumps({"status": "error", "message": str(e)})

# Mantener compatibilidad con funciones viejas mapeándolas a RR logic si es útil
def get_calendar_availability(date_str: str) -> str:
    return get_merged_availability(date_str, 30)

def book_appointment(date_str: str, time_str: str, user_name: str, phone: str) -> str:
    return book_round_robin(date_str, time_str, 30, user_name, phone)

def update_appointment(date_str: str, time_str: str, new_date: str, new_time: str, phone: str, user_name: str) -> str:
    """Modifica una cita existente. Requiere nombre y rut/phone para validación."""
    logger.info(f"Updating appointment from {date_str} {time_str} to {new_date} {new_time} for {phone}")
    
    # 1. Cancelar la cita asegurando la identidad
    del_res = json.loads(delete_appointment(date_str, time_str, phone))
    if del_res.get("status") == "error":
        return json.dumps({"status": "error", "message": f"No se pudo modificar porque falló la cancelación de la original: {del_res.get('message')}"})
        
    # 2. Agendar en la nueva fecha con Round Robin
    book_res = json.loads(book_round_robin(new_date, new_time, 30, user_name, phone))
    if book_res.get("status") == "error":
        return json.dumps({"status": "error", "message": f"Se canceló la anterior pero falló la nueva: {book_res.get('message')}"})
        
    return json.dumps({"status": "success", "message": f"Cita modificada al {new_date} a las {new_time} exitsamente."})

def delete_appointment(date_str: str, time_str: str, phone: str) -> str:
    """Elimina una cita buscando por fecha, hora y verificando celular."""
    logger.info(f"Deleting appointment on {date_str} at {time_str} for phone {phone}")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        orig_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        start_search = local_tz.localize(datetime.datetime.combine(target_date, orig_time)).isoformat()
        end_search = (local_tz.localize(datetime.datetime.combine(target_date, orig_time)) + datetime.timedelta(minutes=5)).isoformat()
        
        calendars = [BOX1_ID, BOX2_ID]
        event_to_del = None
        cal_to_use = None
        
        for c_id in calendars:
            if not c_id: continue
            evs = service.events().list(calendarId=c_id, timeMin=start_search, timeMax=end_search, singleEvents=True).execute().get('items', [])
            if evs:
                ev = evs[0]
                desc = ev.get('description', '')
                # Validar identidad
                if phone and (phone not in desc):
                    logger.warning(f"Security: Intentó borrar cita de otra persona. {phone} not in desc.")
                    continue
                event_to_del = ev
                cal_to_use = c_id
                break
                
        if not event_to_del:
            return json.dumps({"status": "error", "message": "No encontré ninguna cita asociada a tu celular en ese horario para eliminar."})
            
        service.events().delete(calendarId=cal_to_use, eventId=event_to_del['id']).execute()
        return json.dumps({"status": "success", "message": f"La cita del {date_str} a las {time_str} ha sido eliminada correctamente."})
    except Exception as e:
        logger.exception(f"Error deleting from calendar: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error al eliminar: {str(e)}"})

def escalate_to_human(reason: str) -> str:
    # Lógica enviada al interceptor de llm_router.py
    return json.dumps({"status": "success", "message": "Avisa al paciente que pausaste el bot y un humano se pondrá en contacto pronto."})

AVAILABLE_FUNCTIONS = {
    "get_calendar_availability": get_calendar_availability,
    "get_merged_availability": get_merged_availability,
    "book_appointment": book_appointment,
    "book_round_robin": book_round_robin,
    "update_appointment": update_appointment,
    "delete_appointment": delete_appointment,
    "escalate_to_human": escalate_to_human,
}

CALENDAR_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "get_merged_availability",
            "description": "Busca disponibilidad en Google Calendar (Round-Robin Boxes) para una fecha (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                    "duration_minutes": {"type": "integer", "description": "Duración de la cita (30 o 60 min)"}
                },
                "required": ["date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_round_robin",
            "description": "Agenda una cita rotando entre boxes. Requiere fecha, hora, duración, nombre y teléfono.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"},
                    "duration_minutes": {"type": "integer", "description": "30 o 60"},
                    "user_name": {"type": "string", "description": "Nombre del paciente"},
                    "phone": {"type": "string", "description": "Teléfono"}
                },
                "required": ["date_str", "time_str", "duration_minutes", "user_name", "phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment",
            "description": "Modifica y re-agenda una cita existente. Debes conocer la fecha/hora original, la nueva y los datos del paciente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha original YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "Hora original HH:MM"},
                    "new_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD"},
                    "new_time": {"type": "string", "description": "Nueva hora HH:MM"},
                    "phone": {"type": "string", "description": "Celular del paciente para verificación"},
                    "user_name": {"type": "string", "description": "Nombre del paciente"}
                },
                "required": ["date_str", "time_str", "new_date", "new_time", "phone", "user_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_appointment",
            "description": "Cancela/elimina una cita existente asociada al celular del solicitante.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "Hora HH:MM"},
                    "phone": {"type": "string", "description": "Celular del paciente para seguridad"}
                },
                "required": ["date_str", "time_str", "phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Pausa tu atención automática y notifica de urgencia a un humano del Staff cuando el usuario solicita hablar con alguien real o hay una situación sensible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Razón breve de la derivación urgente (ej: 'El usuario exige atención humana', 'Queja grave')"}
                },
                "required": ["reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "derivar_evaluacion_medica",
            "description": "Deriva al paciente a una evaluación médica presencial si el puntaje del triaje es 12 o mayor, o si presenta banderas de advertencia. Se debe proveer el score calculado y un resumen de los síntomas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "score": {"type": "integer", "description": "Puntaje calculado del cuestionario de triaje"},
                    "resumen_sintomas": {"type": "string", "description": "Resumen clínico de los síntomas y motivo de derivación"}
                },
                "required": ["score", "resumen_sintomas"]
            }
        }
    }
]
