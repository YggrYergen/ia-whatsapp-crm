import asyncio
import os
import sys
import json
import dotenv
sys.path.append(os.path.join(os.getcwd(), 'Backend'))
from llm_router import GPT5MiniStrategy
from supabase import create_client

dotenv.load_dotenv(os.path.join(os.getcwd(), 'Backend', '.env'))

async def run():
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    # Fetch contact id for 56912345678
    contact = supabase.table('contacts').select('*').eq('phone_number', '56912345678').single().execute()
    contact_id = contact.data['id']
    history_res = supabase.table('messages').select('*').eq('contact_id', contact_id).order('timestamp', desc=True).limit(5).execute()
    history = sorted(history_res.data, key=lambda x: x['timestamp'])
    
    # print history strictly
    print('Sending history with', len(history), 'messages')
    for h in history: print(f"{h['sender_role']}: {h['content'][:30]}")
    
    st = GPT5MiniStrategy(os.getenv('OPENAI_API_KEY'), 'gpt-5-mini')
    sys_p = 'Sys'
    
    import time
    start = time.time()
    res = await st.generate_response(sys_p, history, 'hola!')
    print('RESULT in', int(time.time() - start), 'seconds:', res)

if __name__ == "__main__":
    asyncio.run(run())
