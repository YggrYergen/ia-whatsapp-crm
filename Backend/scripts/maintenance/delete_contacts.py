import os
from supabase import create_client

from dotenv import load_dotenv
load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table('contacts').delete().neq('name', 'Lead de Prueba (Tú)').execute()
print("Deleted other contacts:", res.data)
