import asyncio
import os
import dotenv
from supabase import create_client

# Cargar variables del backend
dotenv.load_dotenv(os.path.join(os.getcwd(), 'Backend', '.env'))

async def run():
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    # Obtener el contacto de prueba
    contact = supabase.table('contacts').select('*').eq('phone_number', '56912345678').execute()
    if not contact.data:
        print("No se encontró el contacto de prueba.")
        return
        
    c_id = contact.data[0]['id']
    print(f"DEBUG: Contact ID: {c_id}")
    
    # Consultar los últimos 10 mensajes para ver si hay 'memoria tóxica'
    res = supabase.table('messages').select('*').eq('contact_id', c_id).order('timestamp', desc=True).limit(10).execute()
    
    print("\n--- ÚLTIMOS 10 MENSAJES EN DB ---")
    for m in reversed(res.data):
        print(f"[{m['timestamp']}] {m['sender_role']}: {m['content']}")

if __name__ == "__main__":
    asyncio.run(run())
