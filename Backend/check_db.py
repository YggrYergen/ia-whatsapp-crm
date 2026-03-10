import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(".env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table("messages").select("*").order("timestamp", desc=True).limit(10).execute()
print("Recent messages:")
for m in res.data:
    print(m["timestamp"], "|", m["sender_role"], "|", m["content"])
