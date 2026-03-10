import asyncio
import os
import sys
import json
import dotenv
sys.path.append(os.path.join(os.getcwd(), 'Backend'))
from llm_router import GPT5MiniStrategy
from calendar_service import CALENDAR_TOOLS_OPENAI

dotenv.load_dotenv('Backend/.env')

async def run():
    st = GPT5MiniStrategy(os.getenv('OPENAI_API_KEY'), 'gpt-5-mini')
    sys_p = 'Eres un asistente'
    usr_m = 'qué horas libres hay mañana'
    
    formatted_input = [{'role': 'system', 'content': [{'type': 'input_text', 'text': sys_p}]},
                       {'role': 'user', 'content': [{'type': 'input_text', 'text': usr_m}]}]
    
    flattened_tools = []
    for t in CALENDAR_TOOLS_OPENAI:
        if t['type'] == 'function':
            flattened_tools.append({
                'type': 'function',
                'name': t['function']['name'],
                'description': t['function']['description'],
                'parameters': t['function']['parameters']
            })
            
    response_session = await st.client.responses.create(
        model=st.model,
        input=formatted_input,
        background=True,
        tools=flattened_tools,
        tool_choice='auto'
    )
    
    # 1. Wait for first response
    while True:
        res = await st.client.responses.retrieve(response_session.id)
        if res.status == 'completed':
            break
        await asyncio.sleep(1)
        
    print("First response complete.")
    for item in res.output:
        print(item.type)
        formatted_input.append(item.model_dump(exclude_unset=True))
        
        # Simulate tool output
        if item.type == 'function_call':
            formatted_input.append({
                "role": "tool",
                "tool_call_id": getattr(item, 'call_id', None),
                "content": [{"type": "input_text", "text": '{"status": "success", "available_slots": ["10:00", "11:00"]}'}]
            })
            
    print("Sending second response with tool output...")
    try:
        response_session2 = await st.client.responses.create(
            model=st.model,
            input=formatted_input,
            background=True,
            tools=flattened_tools,
            tool_choice='auto'
        )
        while True:
            res2 = await st.client.responses.retrieve(response_session2.id)
            if res2.status == 'completed':
                break
            await asyncio.sleep(1)
            
        print("Second response complete!")
        for item in res2.output:
            if getattr(item, 'role', None) == 'assistant':
                print("Final answer:", item)
    except Exception as e:
        print("Error sending tool output:", e)

if __name__ == "__main__":
    asyncio.run(run())
