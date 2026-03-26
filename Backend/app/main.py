import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.exceptions import AppBaseException
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.core.event_bus import event_bus

from app.modules.communication.routers import router as webhook_router

from app.modules.intelligence.router import LLMFactory
from app.infrastructure.llm_providers.openai_adapter import OpenAIStrategy
from app.infrastructure.llm_providers.gemini_adapter import GeminiStrategy
from app.modules.intelligence.tool_registry import tool_registry
from app.infrastructure.database.supabase_client import SupabasePooler
from app.modules.scheduling.tools import CheckAvailabilityTool, BookAppointmentTool, UpdateAppointmentTool, DeleteAppointmentTool, EscalateHumanTool, CheckMyAppointmentsTool

@asynccontextmanager
async def lifespan(app_ctx: FastAPI):
    # App Factory Native Startup Routines 
    logger.info("Initializing EventBus processor in isolated detached ContextManager")
    asyncio.create_task(event_bus.start_processing())
    
    def on_triage(data: dict):
        logger.warning(f"Extracted background triage logic execution! Payload dict ID target {data.get('tenant_id')}")
        
    async def on_system_alert(data: dict):
        logger.warning(f"🚨 SYSTEM ALERT TRIGGERED -> Contacting Staff {data.get('staff_number', '56999999999')}")
        db = SupabasePooler.get_client()
        staff_number = data.get("staff_number", "+56999999999")
        tenant_id = data.get("tenant_id")
        reason = data.get("reason", "Solicita asistencia")
        patient_phone = data.get("patient_phone", "Desconocido")
        
        c_res = await asyncio.to_thread(
            lambda: db.table("contacts").select("id").eq("phone_number", staff_number).eq("tenant_id", tenant_id).execute()
        )
        contact_id = None
        if c_res.data:
            contact_id = c_res.data[0]["id"]
        else:
            n_res = await asyncio.to_thread(
                lambda: db.table("contacts").insert({
                    "tenant_id": tenant_id,
                    "phone_number": staff_number,
                    "name": "Alertas Sistema 🚨",
                    "bot_active": False
                }).execute()
            )
            if n_res.data:
                contact_id = n_res.data[0]["id"]
                
        if contact_id:
            try:
                res = await asyncio.to_thread(
                    lambda: db.table("messages").insert({
                        "contact_id": contact_id,
                        "tenant_id": tenant_id,
                        "sender_role": "system_alert",
                        "content": f"🚨 ALERTA DE STAFF: El lead / paciente {patient_phone} solicitó atención de un ejecutivo humano.\nMotivo AI: {reason}"
                    }).execute()
                )
                logger.info(f"System Alert Message pushed visually to Frontend! DB Response: {res.data}")
            except Exception as e:
                logger.error(f"Fallo al insertar alerta en Supabase. ¿Quizás falta actualizar constraint 'sender_role' para permitir 'system_alert'? Detalle: {e}")
        
    event_bus.subscribe("triage_alert", on_triage)
    event_bus.subscribe("system_alert", on_system_alert)
    
    yield
    
    # App Factory Native Teardowns freeing Kernel IO
    logger.info("Deallocating Global Memory IO states")
    client = MetaGraphAPIClient._http_client
    if client:
        await client.aclose()


def create_app() -> FastAPI:
    # Notice ORJSONResponse globally set
    app = FastAPI(
        title="WhatsApp AI CRM Refactor (Screaming Infrastructure)",
        version="0.3.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse
    )

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    logger.info("Strap-loading LLM Abstract Strategies")
    LLMFactory.register_strategy("openai", OpenAIStrategy)
    LLMFactory.register_strategy("gemini", GeminiStrategy)

    logger.info("Firming AITool registrations statically")
    tool_registry.register(CheckAvailabilityTool())
    tool_registry.register(BookAppointmentTool())
    tool_registry.register(UpdateAppointmentTool())
    tool_registry.register(DeleteAppointmentTool())
    tool_registry.register(EscalateHumanTool())
    tool_registry.register(CheckMyAppointmentsTool())

    app.include_router(webhook_router)

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException):
        logger.error(f"Screaming Domain Core issue identified: {str(exc)}")
        return ORJSONResponse(status_code=200, content={"message": "Suppressed Internal Base Ex", "error": str(exc)})

    return app

app = create_app()
