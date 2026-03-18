import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
# Get the first tenant
tenant = sb.table("tenants").select("*").limit(1).execute().data[0]
phone = "56955555555"

# Trigger process_whatsapp_message manually!
from main import process_whatsapp_message

async def run_test():
    try:
        await process_whatsapp_message(
            phone_number=phone,
            content="Hola, ¿estás funcionando?",
            ws_phone_id=tenant.get("ws_phone_id", "TEST")
        )
        print("Test finished successfully.")
    except Exception as e:
        print(f"FAILED WITH EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

asyncio.run(run_test())
