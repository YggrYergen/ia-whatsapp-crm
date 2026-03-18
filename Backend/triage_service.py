import os
import json
from supabase import create_client, Client
from logger import logger

def handle_derivation(contact_id: str, tenant_id: str, score: int, resumen_sintomas: str) -> str:
    """
    Maneja la lógica de derivación a evaluación médica.
    1. Pausa el bot_active para el contacto actual.
    2. Envía un mensaje interno de alerta al número +56999999999.
    """
    try:
        score = int(score) if str(score).isdigit() else score
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            return json.dumps({"status": "error", "message": "Missing DB credentials"})
            
        supabase: Client = create_client(url, key)
        
        # 1. Update bot_active = False for this contact
        supabase.table("contacts").update({"bot_active": False}).eq("id", contact_id).execute()
        
        # 2. Add alert to specific contact +56999999999
        alert_phone = "+56999999999"
        contact_res = supabase.table("contacts").select("*").eq("tenant_id", tenant_id).eq("phone_number", alert_phone).execute()
        if not contact_res.data:
            alert_contact = supabase.table("contacts").insert({
                "tenant_id": tenant_id,
                "phone_number": alert_phone,
                "name": "Alertas Sistema 🚨",
                "bot_active": False,
                "status": "lead"
            }).execute().data[0]
        else:
            alert_contact = contact_res.data[0]
            
        # Get patient details for the alert message
        patient_res = supabase.table("contacts").select("*").eq("id", contact_id).execute()
        patient_name = patient_res.data[0].get('name') or patient_res.data[0]['phone_number'] if patient_res.data else "Desconocido"
            
        alert_msg = f"🚨 ALERTA DE DERIVACIÓN 🚨\nPaciente: {patient_name}\nScore de Triaje: {score}\nResumen: {resumen_sintomas}\n\nEl bot ha sido interrumpido para este chat. Requiere intervención humana."
        
        supabase.table("messages").insert({
            "contact_id": alert_contact["id"],
            "tenant_id": tenant_id,
            "sender_role": "system_alert", # Assuming the frontend will just see this as another message type or we can use 'user' so it appears on left side
            "content": alert_msg
        }).execute()

        return json.dumps({
            "status": "success", 
            "message": "Derivación notificada al equipo con éxito. Has pausado tu rol automático. El agente humano ya fue notificado y se hará cargo de ahora en adelante."
        })
    except Exception as e:
        logger.exception(f"Error handling derivation: {e}")
        return json.dumps({"status": "error", "message": "Fallo al procesar la derivación en DB."})
