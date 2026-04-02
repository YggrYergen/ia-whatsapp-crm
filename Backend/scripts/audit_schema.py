import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

# Load env from Backend folder
load_dotenv(dotenv_path="d:/WebDev/IA/Backend/.env")

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    exit(1)

supabase = create_client(url, key)

def check_table(table_name):
    print(f"\nChecking table: {table_name}")
    try:
        # Petición a la tabla para ver si responde
        res = supabase.table(table_name).select("*").limit(1).execute()
        if hasattr(res, 'data') and res.data:
            print(f"Columns: {list(res.data[0].keys())}")
        else:
            print(f"Table {table_name} accessed but empty.")
    except Exception as e:
        print(f"Error accessing {table_name}: {e}")

tables = ["tenants", "contacts", "alerts", "appointments"]
for t in tables:
    check_table(t)
