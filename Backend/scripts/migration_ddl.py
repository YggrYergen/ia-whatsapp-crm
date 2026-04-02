import os
from supabase import create_client
from dotenv import load_dotenv

# Use full path to .env
load_dotenv(dotenv_path='d:/WebDev/IA/Backend/.env')
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not url or not key:
    print("Error: Env vars missing")
    exit(1)

supabase = create_client(url, key)

def run_ddl_migration():
    print("--- Executing Scripted Migrations ---")
    
    # SQL to be executed manually in Supabase SQL Editor
    sql_manual = """
    ALTER TABLE tenants ADD COLUMN IF NOT EXISTS calendar_ids JSONB DEFAULT '[]'::jsonb;
    CREATE TABLE IF NOT EXISTS test_feedback (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id UUID REFERENCES tenants(id),
        session_id TEXT,
        messages JSONB,
        created_at TIMESTAMPTZ DEFAULT now()
    );
    ALTER TABLE contacts ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'cliente';
    ALTER TABLE contacts ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'lead';
    ALTER TABLE contacts ADD COLUMN IF NOT EXISTS bot_active BOOLEAN DEFAULT true;
    ALTER TABLE contacts ADD COLUMN IF NOT EXISTS is_processing_llm BOOLEAN DEFAULT false;
    ALTER TABLE contacts ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
    """
    
    print("MIGRATION NOTE: Manually ensure the following SQL is run in Supabase SQL Editor:")
    print(sql_manual)

if __name__ == "__main__":
    run_ddl_migration()
