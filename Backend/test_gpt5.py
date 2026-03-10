import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'Backend'))

import llm_router
from logger import logger

async def test_gpt5_protocol():
    load_dotenv("Backend/.env")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: No OPENAI_API_KEY found.")
        return

    print("--- Testing GPT-5 Mini Protocol ---")
    strategy = llm_router.GPT5MiniStrategy(api_key, "gpt-5-mini")
    
    system_prompt = "Eres un asistente de prueba. Responde con la palabra 'Protocolo OK' si puedes leerme."
    history = []
    user_message = "Hola, ¿puedes leerme?"
    
    try:
        response = await strategy.generate_response(system_prompt, history, user_message)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Critical Failure: {e}")

if __name__ == "__main__":
    asyncio.run(test_gpt5_protocol())
