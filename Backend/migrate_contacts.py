import psycopg2
import os

DB_URL = "postgresql://postgres:Synapse!Synapse!@db.nemrjlimrnrusodivtoa.supabase.co:5432/postgres"

def migrate():
    print("Connecting to database for migration...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # Check if column exists
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='contacts' AND column_name='role';")
        if cur.fetchone():
            print("Column 'role' already exists in 'contacts' table.")
        else:
            print("Adding 'role' column to 'contacts' table...")
            cur.execute("ALTER TABLE public.contacts ADD COLUMN role TEXT DEFAULT 'cliente' CHECK (role IN ('cliente', 'staff', 'admin'));")
            print("Migration successful.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
