import asyncio
import os
from supabase import create_client
from dotenv import load_dotenv

# Re-loading environment
load_dotenv(dotenv_path='d:/WebDev/IA/Backend/.env')

URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def run_sql():
    print(f"Connecting to {URL}...")
    db = create_client(URL, SERVICE_KEY)
    
    with open('d:/WebDev/IA/Backend/sql/recreate_feedback_table.sql', 'r') as f:
        sql = f.read()
        
    print("Executing SQL...")
    # Using the 'rpc' exec_sql we created earlier (assuming it exists)
    try:
        res = db.rpc('exec_sql', {'query': sql}).execute()
        print("Success!")
        print(res.data)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_sql())
