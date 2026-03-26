import psycopg2

# Correct pooler connection string format for Supabase
# HOST: aws-0-us-east-1.pooler.supabase.com
# USER: postgres.nemrjlimrnrusodivtoa
# PASS: Synapse!Synapse!
# DB: postgres

import os
from dotenv import load_dotenv
load_dotenv()
conn_string = os.getenv("SUPABASE_POOLER_URL")

def run_fix():
    try:
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected. Fixing publications...")
        
        sql = """
        -- 1. Drop the custom one that doesn't work with standard Realtime
        DROP PUBLICATION IF EXISTS supabase_realtime_messages_publication;
        
        -- 2. Ensure supabase_realtime exists
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
                CREATE PUBLICATION supabase_realtime;
            END IF;
        END
        $$;

        -- 3. Add tables to the correct one
        -- We use dynamic SQL to avoid errors if they are already there
        ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;
        ALTER PUBLICATION supabase_realtime ADD TABLE public.contacts;
        """
        
        # Split and execute to see where it fails
        commands = [
            "DROP PUBLICATION IF EXISTS supabase_realtime_messages_publication;",
            "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN CREATE PUBLICATION supabase_realtime; END IF; END $$;",
            "ALTER PUBLICATION supabase_realtime ADD TABLE public.messages;",
            "ALTER PUBLICATION supabase_realtime ADD TABLE public.contacts;"
        ]
        
        for cmd in commands:
            try:
                cursor.execute(cmd)
                print(f"Executed: {cmd[:50]}...")
            except Exception as e:
                print(f"Skipped/Error on {cmd[:20]}: {e}")
                conn.rollback()
        
        print("Done.")
        conn.close()
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    run_fix()
