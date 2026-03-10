import os
import psycopg2
from dotenv import load_dotenv

load_dotenv("Backend/.env")

conn_string = "postgresql://postgres:Synapse!Synapse!@db.nemrjlimrnrusodivtoa.supabase.co:5432/postgres"

def check_db_config():
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        print("--- Checking Publications ---")
        cursor.execute("SELECT pubname FROM pg_publication;")
        pubs = cursor.fetchall()
        for p in pubs:
            print(f"Publication: {p[0]}")
            cursor.execute(f"SELECT schemaname, tablename FROM pg_publication_tables WHERE pubname = '{p[0]}';")
            tables = cursor.fetchall()
            for t in tables:
                print(f"  Table: {t[0]}.{t[1]}")

        print("\n--- Checking RLS Policies on 'messages' ---")
        cursor.execute("SELECT polname, polcmd, polqual, polwithcheck FROM pg_policy WHERE polrelid = 'public.messages'::regclass;")
        policies = cursor.fetchall()
        for p in policies:
            print(f"Policy: {p[0]} | Cmd: {p[1]} | Qual: {p[2]} | WithCheck: {p[3]}")

        print("\n--- Checking if RLS is enabled ---")
        cursor.execute("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.messages'::regclass;")
        rls_enabled = cursor.fetchone()[0]
        print(f"RLS enabled on messages: { rls_enabled }")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db_config()
