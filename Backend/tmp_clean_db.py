import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.infrastructure.database.supabase_client import SupabasePooler
import asyncio

def clean_staff_accounts():
    db = SupabasePooler.get_client()
    print("Sweeping legacy staff alert accounts...")
    res1 = db.table("contacts").delete().eq("phone_number", "56999999999").execute()
    res2 = db.table("contacts").delete().eq("phone_number", "+56999999999").execute()
    print(f"Sweep complete. \nLegacy 1: {res1.data}\nLegacy 2: {res2.data}")

if __name__ == "__main__":
    clean_staff_accounts()
