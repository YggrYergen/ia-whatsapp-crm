import os
import json
import datetime
import pytz
from app.infrastructure.telemetry.logger_service import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
BOX1_ID = '934af5bfb378ec7c1dd531aeb5095246f4cd2fd42ad5a77f715ff6f102d5c884@group.calendar.google.com'
BOX2_ID = 'c18d3c64564d57a86f04b2810573620b676e62ecfc62f130b4e5848d746a157e@group.calendar.google.com'
SERVICE_ACCOUNT_FILE = r'D:\WebDev\IA\Backend\credentials\casavitacure-crm-1b7950d2fa11.json'
TIMEZONE = "America/Santiago"

class GoogleCalendarClient:
    @staticmethod
    def get_service():
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)

    @staticmethod
    def get_merged_availability(date_str: str, duration_minutes: int = 30) -> dict:
        try:
            service = GoogleCalendarClient.get_service()
            local_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            time_min = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(9, 0))).isoformat()
            time_max = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(19, 0))).isoformat()
            
            body = {"timeMin": time_min, "timeMax": time_max, "items": [{"id": BOX1_ID}, {"id": BOX2_ID}]}
            freebusy_res = service.freebusy().query(body=body).execute()
            
            busy_box1 = freebusy_res['calendars'][BOX1_ID]['busy']
            busy_box2 = freebusy_res['calendars'][BOX2_ID]['busy']
            
            def parse_busy(busy_list):
                return [(datetime.datetime.fromisoformat(i['start'].replace('Z', '+00:00')), datetime.datetime.fromisoformat(i['end'].replace('Z', '+00:00'))) for i in busy_list]

            ranges1 = parse_busy(busy_box1)
            ranges2 = parse_busy(busy_box2)
            
            all_slots = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00"]
            available_slots = []
            
            for slot in all_slots:
                slot_time = datetime.datetime.strptime(slot, "%H:%M").time()
                slot_start = local_tz.localize(datetime.datetime.combine(target_date, slot_time))
                slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
                
                def is_busy(s, e, r):
                    for bs, be in r:
                        if max(s, bs) < min(e, be): return True
                    return False

                if not is_busy(slot_start, slot_end, ranges1) or not is_busy(slot_start, slot_end, ranges2):
                    available_slots.append(slot)
            
            return {
                "status": "success", "available_slots": available_slots, "duration": duration_minutes,
                "message": f"Se encontraron {len(available_slots)} horarios libres."
            }
        except Exception as e:
            logger.exception("Error checking merged availability in GCalendar API")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def book_round_robin(date_str: str, time_str: str, duration_minutes: int, user_name: str, phone: str) -> dict:
        try:
            service = GoogleCalendarClient.get_service()
            local_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            start_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            start_dt = local_tz.localize(datetime.datetime.combine(target_date, start_time))
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
            
            body = {"timeMin": start_dt.isoformat(), "timeMax": end_dt.isoformat(), "items": [{"id": BOX1_ID}, {"id": BOX2_ID}]}
            fb_res = service.freebusy().query(body=body).execute()
            
            target_calendar_id = None
            if not fb_res['calendars'][BOX1_ID]['busy']: target_calendar_id, box_label = BOX1_ID, "Box 1"
            elif not fb_res['calendars'][BOX2_ID]['busy']: target_calendar_id, box_label = BOX2_ID, "Box 2"
            else: return {"status": "error", "message": "Lo siento, ese horario acaba de ocuparse (Colisión en Box 1 y Box 2)."}
                
            event = {
                'summary': f'Cita ({box_label}) - {user_name}',
                'description': f'Paciente: {user_name}\nTeléfono: {phone}\nDuración: {duration_minutes} min\nAgendado por Synapse AI CRM',
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': TIMEZONE},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': TIMEZONE},
                'colorId': '1' if box_label == "Box 1" else '2',
            }
            res = service.events().insert(calendarId=target_calendar_id, body=event).execute()
            return {"status": "success", "message": f"Agendado con éxito en {box_label}.", "event_link": res.get('htmlLink'), "box_label": box_label}
        except Exception as e:
            logger.exception("Error in book_round_robin executing Google API Call")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def delete_appointment(date_str: str, time_str: str, phone: str) -> dict:
        try:
            service = GoogleCalendarClient.get_service()
            local_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            orig_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            
            start_search = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(0, 0, 0))).isoformat()
            end_search = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(23, 59, 59))).isoformat()
            
            event_to_del_list = []
            
            for c_id in [BOX1_ID, BOX2_ID]:
                evs = service.events().list(calendarId=c_id, timeMin=start_search, timeMax=end_search, singleEvents=True).execute().get('items', [])
                
                for ev in evs:
                    # 1. Validar coincidencia de teléfono
                    if phone and (phone not in ev.get('description', '')): 
                        continue
                    
                    # 2. ALTO ESTÁNDAR: Validar coincidencia de hora para evitar borrar citas equivocadas
                    ev_start_str = ev['start'].get('dateTime', ev['start'].get('date'))
                    ev_start_dt = datetime.datetime.fromisoformat(ev_start_str).astimezone(local_tz)
                    
                    if ev_start_dt.time().hour != orig_time.hour or ev_start_dt.time().minute != orig_time.minute:
                        continue
                        
                    # Múltiple acumulación (si hay citas al mismo tiempo en ambos boxes y se aprueba el match por rol/admin).
                    event_to_del_list.append((ev, c_id))
                    
            if not event_to_del_list: 
                return {"status": "error", "message": "No encontré ninguna cita asociada a tu celular en la franja de tiempo indicada."}
                
            summaries = []
            for ev, cal_use in event_to_del_list:
                service.events().delete(calendarId=cal_use, eventId=ev['id']).execute()
                summ = ev.get('summary', 'Sin Título')
                desc = ev.get('description', 'Sin Detalles')
                summaries.append(f"{summ} | Notas: {desc}")
                
            return {
                "status": "success", 
                "message": f"Se eliminaron {len(event_to_del_list)} citas directamente del Calendario de Google con éxito.",
                "details": " \n".join(summaries),
                "items": summaries
            }
        except Exception as e:
            logger.exception("Error deleting appointment executing Google API Call")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def list_appointments(date_str: str, caller_phone: str, caller_role: str) -> dict:
        try:
            service = GoogleCalendarClient.get_service()
            local_tz = pytz.timezone(TIMEZONE)
            target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            start_search = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(0, 0, 0))).isoformat()
            end_search = local_tz.localize(datetime.datetime.combine(target_date, datetime.time(23, 59, 59))).isoformat()
            
            appointments = []
            
            for c_id, box_label in [(BOX1_ID, "Box 1"), (BOX2_ID, "Box 2")]:
                evs = service.events().list(calendarId=c_id, timeMin=start_search, timeMax=end_search, singleEvents=True, orderBy='startTime').execute().get('items', [])
                for ev in evs:
                    summary = ev.get('summary', 'Cita reservada')
                    desc = ev.get('description', '')
                    start_time = datetime.datetime.fromisoformat(ev['start'].get('dateTime', ev['start'].get('date'))).astimezone(local_tz).strftime("%H:%M")
                    end_time = datetime.datetime.fromisoformat(ev['end'].get('dateTime', ev['end'].get('date'))).astimezone(local_tz).strftime("%H:%M")
                    
                    if caller_role in ['admin', 'staff']:
                        appointments.append(f"[{start_time} - {end_time}] {box_label}: {summary}")
                    else:
                        if caller_phone and caller_phone in desc:
                            appointments.append(f"[{start_time} - {end_time}] {box_label}: Tienes una cita agendada.")
                            
            if not appointments:
                return {"status": "success", "message": "No hay citas agendadas en esta fecha para tu perfil."}
                
            return {
                "status": "success",
                "message": "Citas encontradas:\n" + "\n".join(sorted(appointments))
            }
        except Exception as e:
            logger.exception("Error listing appointments in GCalendar API")
            return {"status": "error", "message": str(e)}
