import os
import json
from typing import Optional
from fastapi import FastAPI, Request, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

from logger import logger
from llm_router import LLMFactory
from whatsapp_service import send_whatsapp_message

from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(title="AI WhatsApp CRM Multi-tenant")

# Habilitar CORS para permitir peticiones desde el simulador en localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En producción cambiar esto a la URL de Cloudflare Pages
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Admin setup (bypasses RLS)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# External API Keys (Can also be stored per-tenant in DB)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class WebhookPayload(BaseModel):
    # Simplified Meta Webhook structure
    object: str
    entry: list

@app.get("/webhook")
async def verify_webhook(request: Request):
    # Meta Webhook Verification
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(payload: dict, background_tasks: BackgroundTasks):
    """
    Entry point for WhatsApp/Meta messages. 
    Returns 200 OK immediately and processes in background.
    """
    logger.info("Received Webhook Payload")
    
    # Quick validation of Meta structure
    try:
        changes = payload["entry"][0]["changes"][0]["value"]
        if "messages" not in changes:
            return {"status": "ignored"}
            
        message_data = changes["messages"][0]
        metadata = changes["metadata"]
        
        phone_number = message_data["from"]
        content = message_data.get("text", {}).get("body", "")
        ws_phone_id = metadata["phone_number_id"]
        
        if not content:
            return {"status": "unsupported_content"}

        # Enqueue processing
        background_tasks.add_task(process_whatsapp_message, ws_phone_id, phone_number, content)
        
        return {"status": "enqueued"}
        
    except (KeyError, IndexError) as e:
        logger.error(f"Invalid Payload structure: {str(e)}")
        return {"status": "error", "detail": "Invalid structure"}

async def process_whatsapp_message(ws_phone_id: str, phone_number: str, content: str):
    """
    Main background logic: 
    1. Identify Tenant
    2. Check HITL (bot_active)
    3. Save User Message
    4. Call LLM (if active)
    5. Save Assistant Message
    6. Send back to WhatsApp
    """
    try:
        # 1. Identify Tenant
        tenant_res = supabase.table("tenants").select("*").eq("ws_phone_id", ws_phone_id).single().execute()
        tenant = tenant_res.data
        if not tenant:
            logger.error(f"No tenant found for Phone ID: {ws_phone_id}")
            return

        # 2. Identify/Create Contact
        contact_res = supabase.table("contacts").select("*").eq("tenant_id", tenant["id"]).eq("phone_number", phone_number).execute()
        if not contact_res.data:
            contact = supabase.table("contacts").insert({
                "tenant_id": tenant["id"],
                "phone_number": phone_number,
                "name": "WhatsApp User"
            }).execute().data[0]
        else:
            contact = contact_res.data[0]

        # 3. Save User Message
        supabase.table("messages").insert({
            "contact_id": contact["id"],
            "tenant_id": tenant["id"],
            "sender_role": "user",
            "content": content
        }).execute()

        # Update last_message timestamp
        supabase.table("contacts").update({"last_message_at": "now()"}).eq("id", contact["id"]).execute()

        # 4. Check HITL
        if not contact["bot_active"]:
            logger.info(f"Bot inactive for {phone_number}. Skipping LLM.")
            return

        # --- MOTOR DE MEMORIA (CONTEXTO) ---
        # Como el LLM es stateless, inyectamos los últimos 10 mensajes del historial de Supabase.
        # Esto permite que la IA recuerde nombres, fechas y el hilo de la conversación.
        history_res = supabase.table("messages").select("*").eq("contact_id", contact["id"]).order("timestamp", desc=True).limit(10).execute()
        history = sorted(history_res.data, key=lambda x: x["timestamp"])

        if os.getenv("MOCK_LLM") == "true":
            # Si estamos en modo de prueba y no hay API keys reales
            import asyncio
            await asyncio.sleep(1) # Simular letencia
            ai_response = f"¡Hola! (Modo de prueba local usando {tenant['llm_provider']} - {tenant['llm_model']}). Recibí tu mensaje: '{content}'."
        else:
            # Decide key to use (per tenant or global)
            api_key = OPENAI_API_KEY if tenant["llm_provider"] == "openai" else GEMINI_API_KEY
            
            strategy = LLMFactory.get_strategy(tenant["llm_provider"], tenant["llm_model"], api_key)
            ai_response = await strategy.generate_response(
                tenant["system_prompt"], 
                history, 
                content, 
                phone_number, 
                contact_id=contact["id"], 
                tenant_id=tenant["id"],
                user_role=contact.get("role", "cliente")
            )

        # 6. Save Assistant Response
        supabase.table("messages").insert({
            "contact_id": contact["id"],
            "tenant_id": tenant["id"],
            "sender_role": "assistant",
            "content": ai_response
        }).execute()

        # 7. Send to WhatsApp (Meta API Call)
        logger.info(f"Response prepared for {phone_number}: {ai_response[:50]}...")
        if tenant.get("ws_token") and tenant.get("ws_token") != "PLACEHOLDER_TOKEN":
            await send_whatsapp_message(
                phone_number=phone_number,
                text=ai_response,
                phone_number_id=tenant["ws_phone_id"],
                token=tenant["ws_token"]
            )
        else:
            logger.info("Skipped Meta API call because tenant uses a PLACEHOLDER_TOKEN.")

    except Exception as e:
        logger.exception(f"Error processing message: {str(e)}")

# --- PUBLIC ENDPOINTS (For CasaVitaCure Website) ---

@app.get("/api/public/availability")
async def public_availability(date: str):
    """
    Endpoint público para el sitio web. Fuerza bloques de 30 mins.
    """
    from calendar_service import get_merged_availability
    # Forzamos 30 minutos ya que el público solo agenda evaluaciones
    res = get_merged_availability(date, duration_minutes=30)
    return json.loads(res)

@app.post("/api/public/book")
async def public_book(payload: dict):
    """
    Endpoint público para agendar desde el sitio web.
    """
    from calendar_service import book_round_robin
    date_str = payload.get("date")
    time_str = payload.get("time")
    user_name = payload.get("name")
    phone = payload.get("phone")
    
    if not all([date_str, time_str, user_name, phone]):
        raise HTTPException(status_code=400, detail="Missing fields")
        
    # Forzamos 30 minutos
    res = book_round_robin(date_str, time_str, 30, user_name, phone)
    return json.loads(res)

@app.get("/health")
def health():
    return {"status": "ok", "environment": os.getenv("ENVIRONMENT", "development")}
