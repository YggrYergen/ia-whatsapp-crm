import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

import os
from dotenv import load_dotenv
load_dotenv()
conn_string = os.getenv("SUPABASE_DB_URL")

def run_fix():
    print(f"Connecting to: {conn_string}")
    conn = psycopg2.connect(conn_string)
    conn.autocommit = True
    cursor = conn.cursor()

    sql = """
    -- Drop existing authenticated policies
    DROP POLICY IF EXISTS "Users can view their own tenant" ON public.tenants;
    DROP POLICY IF EXISTS "Users can update their own tenant" ON public.tenants;
    DROP POLICY IF EXISTS "Users can view own contacts" ON public.contacts;
    DROP POLICY IF EXISTS "Users can update own contacts" ON public.contacts;
    DROP POLICY IF EXISTS "Users can insert own contacts" ON public.contacts;
    DROP POLICY IF EXISTS "Users can view own messages" ON public.messages;
    DROP POLICY IF EXISTS "Users can insert own messages" ON public.messages;

    -- Create public policies for local testing (No Auth required)
    CREATE POLICY "Allow public read tenants" ON public.tenants FOR SELECT USING (true);
    CREATE POLICY "Allow public update tenants" ON public.tenants FOR UPDATE USING (true);
    
    CREATE POLICY "Allow public read contacts" ON public.contacts FOR SELECT USING (true);
    CREATE POLICY "Allow public insert contacts" ON public.contacts FOR INSERT WITH CHECK (true);
    CREATE POLICY "Allow public update contacts" ON public.contacts FOR UPDATE USING (true);

    CREATE POLICY "Allow public read messages" ON public.messages FOR SELECT USING (true);
    CREATE POLICY "Allow public insert messages" ON public.messages FOR INSERT WITH CHECK (true);
    
    -- Fix schema trigger to use correct function
    """

    cursor.execute(sql)
    print("RLS Policies updated for public anonymous access successfully.")
    conn.close()

if __name__ == "__main__":
    run_fix()
