import os
import json
import datetime
import pytz
from logger import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = 'agenda.casavitacure@gmail.com'
SERVICE_ACCOUNT_FILE = r'D:\WebDev\IA\backend\casavitacure-crm-1b7950d2fa11.json'
TIMEZONE = "America/Santiago"

def get_calendar_service():
    """Builds and returns the Google Calendar service using the Service Account."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_calendar_availability(date_str: str) -> str:
    """
    Busca disponibilidad real en Google Calendar para una fecha específica.
    Ventana: 09:00 a 18:00 en bloques de 30 minutos.
    """
    logger.info(f"Checking Google Calendar availability for {date_str}")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        # Parsing de la fecha objetivo
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Limites del día: 09:00 AM a 18:00 PM
        time_min = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(9, 0))).isoformat()
        time_max = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(18, 0))).isoformat()
        
        # Solicitar los eventos de este día ocupados
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Opciones de horario base en la clínica
        all_slots = [
            "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
            "12:00", "12:30", "13:00", "13:30", "14:00", "14:30",
            "15:00", "15:30", "16:00", "16:30", "17:00", "17:30"
        ]
        
        busy_slots = set()
        
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            # Si el evento dura todo el día, no tiene hora (es solo "YYYY-MM-DD")
            if 'T' not in start:
                return json.dumps({
                    "status": "success",
                    "available_slots": [],
                    "message": "Día completo ocupado en el calendario."
                })
                
            start_dt = datetime.datetime.fromisoformat(start)
            end_dt = datetime.datetime.fromisoformat(end)
            
            # Detectar colisiones de nuestros "slots" de 30 mins contra los eventos reales
            for slot in all_slots:
                slot_time = datetime.datetime.strptime(slot, "%H:%M").time()
                slot_start_dt = local_tz.localize(datetime.datetime.combine(target_date, slot_time))
                slot_end_dt = slot_start_dt + datetime.timedelta(minutes=30)
                
                # Check overlap: Max(starts) < Min(ends)
                if max(start_dt, slot_start_dt) < min(end_dt, slot_end_dt):
                    busy_slots.add(slot)
                    
        # Calcular los disponibles
        available_slots = sorted(list(set(all_slots) - busy_slots))
        
        return json.dumps({
            "status": "success", 
            "available_slots": available_slots,
            "message": f"Se han encontrado {len(available_slots)} horas libres." if available_slots else "Agenda llena en esa fecha."
        })
        
    except Exception as e:
        logger.exception(f"Error checking calendar availability: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": "Hubo un error interno revisando la agenda en tiempo real (Google Api Error)."
        })

def book_appointment(date_str: str, time_str: str, user_name: str, phone: str) -> str:
    """
    Agenda (inserta) un evento de 30 minutos directo al Google Calendar de la clínica.
    """
    logger.info(f"Booking real appointment for {user_name} on {date_str} at {time_str}")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        start_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        
        start_dt = local_tz.localize(datetime.datetime.combine(target_date, start_time))
        # Duración de cada cita: 30 Minutos (ajustable)
        end_dt = start_dt + datetime.timedelta(minutes=30) 
        
        event = {
          'summary': f'Cita - {user_name}',
          'description': f'Paciente: {user_name}\nWhatsApp de contacto: {phone}\nAgendado automáticamente por: Synapse AI CRM 🤖',
          'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': TIMEZONE,
          },
          'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': TIMEZONE,
          },
          'colorId': '1', # Azul lavanda en el UI
          'reminders': {
            'useDefault': True,
          },
        }

        event_result = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        
        # El paciente quedó guardado maravillosamente
        return json.dumps({
            "status": "success",
            "event_link": event_result.get('htmlLink'),
            "message": f"¡Cita confirmada! Ha quedado bloqueada la hora para {user_name} el día {date_str} a las {time_str} en tu Calendario de Google."
        })
        
    except Exception as e:
        logger.exception(f"Error booking in calendar: {str(e)}")
        return json.dumps({
            "status": "error",
            "message": "No es posible agendar. Podría ser un error de permisos o un choque temporal. Por favor notifícalo a la clínica."
        })

def update_appointment(date_str: str, time_str: str, new_date: str = None, new_time: str = None) -> str:
    """
    Modifica una cita existente. Primero busca el evento en la fecha/hora original y luego lo mueve.
    """
    logger.info(f"Updating appointment from {date_str} {time_str} to {new_date} {new_time}")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        # 1. Buscar el evento original
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        orig_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        start_search = local_tz.localize(datetime.datetime.combine(target_date, orig_time)).isoformat()
        end_search = (local_tz.localize(datetime.datetime.combine(target_date, orig_time)) + datetime.timedelta(minutes=5)).isoformat()
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_search,
            timeMax=end_search,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            return json.dumps({"status": "error", "message": "No encontré ninguna cita en ese horario para modificar."})
        
        event = events[0]
        
        # 2. Actualizar tiempos si se proveen
        if new_date or new_time:
            final_date = new_date if new_date else date_str
            final_time = new_time if new_time else time_str
            
            new_target_date = datetime.datetime.strptime(final_date, "%Y-%m-%d").date()
            new_start_time = datetime.datetime.strptime(final_time, "%H:%M").time()
            new_start_dt = local_tz.localize(datetime.datetime.combine(new_target_date, new_start_time))
            new_end_dt = new_start_dt + datetime.timedelta(minutes=30)
            
            event['start'] = {'dateTime': new_start_dt.isoformat(), 'timeZone': TIMEZONE}
            event['end'] = {'dateTime': new_end_dt.isoformat(), 'timeZone': TIMEZONE}
        
        updated_event = service.events().update(calendarId=CALENDAR_ID, eventId=event['id'], body=event).execute()
        
        return json.dumps({
            "status": "success",
            "message": f"¡Cita modificada exitosamente! Ahora está para el {new_date or date_str} a las {new_time or time_str}."
        })
        
    except Exception as e:
        logger.exception(f"Error updating calendar: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error al intentar modificar: {str(e)}"})

def delete_appointment(date_str: str, time_str: str) -> str:
    """
    Elimina una cita buscando por fecha y hora.
    """
    logger.info(f"Deleting appointment on {date_str} at {time_str}")
    try:
        service = get_calendar_service()
        local_tz = pytz.timezone(TIMEZONE)
        
        target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        orig_time = datetime.datetime.strptime(time_str, "%H:%M").time()
        start_search = local_tz.localize(datetime.datetime.combine(target_date, orig_time)).isoformat()
        end_search = (local_tz.localize(datetime.datetime.combine(target_date, orig_time)) + datetime.timedelta(minutes=5)).isoformat()
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_search,
            timeMax=end_search,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            return json.dumps({"status": "error", "message": "No encontré ninguna cita en ese horario para eliminar."})
        
        service.events().delete(calendarId=CALENDAR_ID, eventId=events[0]['id']).execute()
        
        return json.dumps({
            "status": "success",
            "message": f"La cita del {date_str} a las {time_str} ha sido eliminada correctamente."
        })
        
    except Exception as e:
        logger.exception(f"Error deleting from calendar: {str(e)}")
        return json.dumps({"status": "error", "message": f"Error al eliminar: {str(e)}"})

AVAILABLE_FUNCTIONS = {
    "get_calendar_availability": get_calendar_availability,
    "book_appointment": book_appointment,
    "update_appointment": update_appointment,
    "delete_appointment": delete_appointment,
}

CALENDAR_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "get_calendar_availability",
            "description": "Busca disponibilidad en Google Calendar para una fecha (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"}
                },
                "required": ["date_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Agenda una cita. Requiere fecha, hora, nombre y teléfono.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "HH:MM"},
                    "user_name": {"type": "string", "description": "Nombre del paciente"},
                    "phone": {"type": "string", "description": "Teléfono"}
                },
                "required": ["date_str", "time_str", "user_name", "phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_appointment",
            "description": "Modifica una cita existente. Debes conocer la fecha/hora original y opcionalmente la nueva fecha/hora.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha original YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "Hora original HH:MM"},
                    "new_date": {"type": "string", "description": "Nueva fecha YYYY-MM-DD (opcional)"},
                    "new_time": {"type": "string", "description": "Nueva hora HH:MM (opcional)"}
                },
                "required": ["date_str", "time_str"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_appointment",
            "description": "Elimina una cita existente por su fecha y hora.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_str": {"type": "string", "description": "Fecha YYYY-MM-DD"},
                    "time_str": {"type": "string", "description": "Hora HH:MM"}
                },
                "required": ["date_str", "time_str"]
            }
        }
    }
]
