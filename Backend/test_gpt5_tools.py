import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'Backend'))

import llm_router
from logger import logger

async def test_gpt5_tools():
    load_dotenv("Backend/.env")
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("Error: No OPENAI_API_KEY found.")
        return

    print("--- Testing GPT-5 Mini Protocol with Tools ---")
    strategy = llm_router.GPT5MiniStrategy(api_key, "gpt-5-mini")
    
    system_prompt = "Eres un asistente de clínica."
    history = []
    user_message = "¿Qué horas libres tienes para mañana en el calendario?"
    
    try:
        response = await strategy.generate_response(system_prompt, history, user_message)
        print(f"Final Response: {response}")
    except Exception as e:
        print(f"Critical Failure: {e}")

if __name__ == "__main__":
    asyncio.run(test_gpt5_tools())
