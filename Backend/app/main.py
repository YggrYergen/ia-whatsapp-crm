import os
import asyncio


from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.infrastructure.telemetry.discord_notifier import send_discord_alert

from app.core.config import settings
from app.core.exceptions import AppBaseException
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.core.event_bus import event_bus
import sentry_sdk

from app.modules.communication.routers import router as webhook_router
from app.modules.integrations.google_oauth_router import router as google_oauth_router

from app.modules.intelligence.router import LLMFactory
from app.infrastructure.llm_providers.openai_adapter import OpenAIStrategy
from app.infrastructure.llm_providers.gemini_adapter import GeminiStrategy
from app.infrastructure.llm_providers.mock_adapter import MockStrategy
from app.modules.intelligence.tool_registry import tool_registry
from app.infrastructure.database.supabase_client import SupabasePooler
from app.modules.scheduling.tools import CheckAvailabilityTool, BookAppointmentTool, UpdateAppointmentTool, DeleteAppointmentTool, EscalateHumanTool, CheckMyAppointmentsTool, UpdatePatientScoringTool

@asynccontextmanager
async def lifespan(app_ctx: FastAPI):
    # App Factory Native Startup Routines 
    asyncio.create_task(event_bus.start_processing())
    
    from app.core.proactive_worker import proactive_worker
    asyncio.create_task(proactive_worker.start())
    
    def on_triage(data: dict):
        logger.warning(f"Extracted background triage logic execution! Payload dict ID target {data.get('tenant_id')}")
        
    async def on_system_alert(data: dict):
        logger.warning(f"🚨 SYSTEM ALERT TRIGGERED -> {data.get('reason')}")
        db = await SupabasePooler.get_client()
        tenant_id = data.get("tenant_id")
        reason = data.get("reason", "Solicita asistencia")
        patient_phone = data.get("patient_phone")
        
        # 1. Buscar el ID del contacto real
        contact_id = None
        if patient_phone:
            c_res = await db.table("contacts").select("id").eq("phone_number", patient_phone).eq("tenant_id", tenant_id).execute()
            if c_res.data:
                contact_id = c_res.data[0]["id"]
        
        # 2. Insertar SOLO en la tabla de alertas pura (No más mensajes falsos)
        try:
            alert_payload = {
                "tenant_id": tenant_id,
                "contact_id": contact_id, 
                "message": reason,
                "type": "escalation",
                "is_resolved": False
            }
            res = await db.table("alerts").insert(alert_payload).execute()
            logger.info("🚨 ALERTA GUARDADA EN BD. Frontend notificado vía WebSockets.")
            
            # 3. Notificar vía Discord (Devs)
            from app.infrastructure.telemetry.discord_notifier import send_discord_alert
            asyncio.create_task(send_discord_alert(
                title=f"🚨 ESCALACIÓN: {reason}",
                description=f"Paciente: `{patient_phone or 'Desconocido'}`\nTenant: `{tenant_id}`",
                severity="warning"
            ))

            # 4. Notificar vía Email al negocio usando Resend (background)
            from app.infrastructure.email.email_service import send_business_email_alert
            html_body = f"<h2>Nueva Alerta del CRM</h2><p><strong>Razón:</strong> {reason}</p><p><strong>Paciente:</strong> {patient_phone or 'Desconocido'}</p><p>Inicia sesión en el CRM para revisar.</p>"
            asyncio.create_task(send_business_email_alert("ALERTA CRM: Handoff Requerido / Asistencia", html_body))

        except Exception as e:
            logger.error(f"Fallo al insertar en tabla 'alerts'. Detalles: {e}")
            from app.infrastructure.telemetry.discord_notifier import send_discord_alert
            asyncio.create_task(send_discord_alert(
                title="Error en on_system_alert",
                description="No se pudo procesar la alerta o notificación.",
                error=e
            ))
        
    event_bus.subscribe("triage_alert", on_triage)
    event_bus.subscribe("system_alert", on_system_alert)
    
    yield
    
    # App Factory Native Teardowns freeing Kernel IO
    logger.info("Deallocating Global Memory IO states")
    client = MetaGraphAPIClient._http_client
    if client:
        await client.aclose()
        
    from app.core.proactive_worker import proactive_worker
    proactive_worker.stop()


def create_app() -> FastAPI:
    # Configuración inteligente de Sentry tal cual su instructivo
    sentry_sdk.init(
        dsn=getattr(settings, "SENTRY_DSN", "https://b5b7a769848286fcfcc7f367a970c34f@o4511179991416832.ingest.us.sentry.io/4511184254402560"),
        send_default_pii=True,
        enable_logs=True,
    )
    
    # Notice ORJSONResponse globally set
    app = FastAPI(
        title="WhatsApp AI CRM Refactor (Screaming Infrastructure)",
        version="0.3.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info("Strap-loading LLM Abstract Strategies")
    if settings.MOCK_LLM:
        logger.warning("MOCK_LLM is enabled. Bypassing real providers.")
        LLMFactory.register_strategy("openai", MockStrategy)
        LLMFactory.register_strategy("gemini", MockStrategy)
    else:
        LLMFactory.register_strategy("openai", OpenAIStrategy)
        LLMFactory.register_strategy("gemini", GeminiStrategy)

    logger.info("Firming AITool registrations statically")
    tool_registry.register(CheckAvailabilityTool())
    tool_registry.register(BookAppointmentTool())
    tool_registry.register(UpdateAppointmentTool())
    tool_registry.register(DeleteAppointmentTool())
    tool_registry.register(EscalateHumanTool())
    tool_registry.register(CheckMyAppointmentsTool())
    tool_registry.register(UpdatePatientScoringTool())

    app.include_router(webhook_router)
    app.include_router(google_oauth_router)

    @app.get("/api/debug-ping")
    async def debug_ping():
        return {"status": "ok", "message": "Backend is alive!"}

    @app.get("/api/debug-exception")
    async def debug_exception():
        raise Exception("🚨 This is a Sentry test exception from Javiera CRM!")

    @app.post("/api/simulate")
    async def simulate_webhook(background_tasks: BackgroundTasks, payload: dict = Body(...)):
        # Simulates a WhatsApp payload to trigger the ProcessMessageUseCase
        phone = payload.get("phone") or payload.get("phone_number", "56912345678")
        message = payload.get("message") or payload.get("message_text", "Hola")
        tenant_id = payload.get("tenantId") or payload.get("tenant_id")
        
        logger.info(f"🚀 [SIM] Start: Phone={phone}, Message='{message}', Tenant={tenant_id}")
        
        from app.core.config import settings
        from supabase import create_client
        # Use service role or anon key from settings
        db = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
        try:
            # Direct tenant lookup
            res = await db.table("tenants").select("*").eq("id", tenant_id).execute()
            
            if not res.data:
                logger.error(f"❌ [SIM] Tenant {tenant_id} NOT found")
                return {"status": "error", "message": "Tenant not found"}
            
            # Ensure required fields are present for TenantContext
            from app.core.models import TenantContext
            tenant_data = res.data[0]
            tenant_data.setdefault('llm_provider', 'openai')
            tenant_data.setdefault('llm_model', 'gpt-4o-mini')
            tenant_data.setdefault('system_prompt', 'Eres Javiera...')
            tenant_data.setdefault('ws_phone_id', '123456789')
            tenant_data.setdefault('ws_token', 'mock_token')
            tenant = TenantContext(**tenant_data)
            
            # Mock a payload
            mock_payload = {
                "entry": [{
                    "changes": [{
                        "value": {
                            "messages": [{
                                "from": phone,
                                "text": {"body": message}
                            }]
                        }
                    }]
                }],
                "is_simulation": True
            }
            
            logger.info(f"Simulating message for tenant {tenant_id}: {message}")
            from app.modules.communication.use_cases import ProcessMessageUseCase
            logger.info("🔄 [SIM] Executing Background Task...")
            
            # Execute in background to respond 200 OK immediately
            await ProcessMessageUseCase.execute(
                mock_payload,
                tenant,
                db
            )
            
            return {"status": "success", "detail": "Simulation queued"}
        except Exception as e:
            logger.error(f"🔥 [SIM] Crash: {str(e)}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.post("/api/test-feedback")
    async def save_test_feedback(payload: dict = Body(...)):
        """Bypass Supabase REST Cache by using service role via Python Client."""
        logger.info(f"📩 [FEEDBACK] Received payload for tenant {payload.get('tenant_id')}")
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        
        try:
            res = await db.table("test_feedback").insert({
                    "tenant_id": payload.get("tenant_id"),
                    "patient_phone": payload.get("patient_phone"),
                    "history": payload.get("history"),
                    "notes": payload.get("notes"),
                    "tester_email": payload.get("tester_email", "tomasgemes@gmail.com")
                }).execute()
            logger.info("✅ [FEEDBACK] Saved successfully via Backend Proxy.")
            return {"status": "success", "data": res.data}
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Failed to save: {str(e)}")
            # If table still not found, we log it clearly
            # If table still not found, we log it clearly
            return ORJSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    @app.get("/api/calendar/events")
    async def api_get_calendar_events(start_iso: str, end_iso: str, tenant_id: str = "d8376510-911e-42ef-9f3b-e018d9f10915"):
        try:
            from app.infrastructure.database.supabase_client import SupabasePooler
            db = await SupabasePooler.get_client()
            tenant_res = await db.table("tenants").select("*").eq("id", tenant_id).execute()
            if not tenant_res.data:
                return {"status": "error", "message": "Tenant not found"}
            from app.core.models import TenantContext
            tenant = TenantContext(**tenant_res.data[0])
            from app.infrastructure.calendar.google_client import GoogleCalendarClient
            return await GoogleCalendarClient.get_structured_events(tenant, start_iso, end_iso)
        except Exception as e:
            import traceback
            return ORJSONResponse(status_code=500, content={"status": "fatal", "message": str(e), "trace": traceback.format_exc()})

    @app.post("/api/calendar/book")
    async def api_book_calendar_event(payload: dict = Body(...)):
        tenant_id = payload.get("tenant_id", "d8376510-911e-42ef-9f3b-e018d9f10915")
        from app.infrastructure.database.supabase_client import SupabasePooler
        db = await SupabasePooler.get_client()
        tenant_res = await db.table("tenants").select("*").eq("id", tenant_id).execute()
        if not tenant_res.data:
            return {"status": "error", "message": "Tenant not found"}
        from app.core.models import TenantContext
        tenant = TenantContext(**tenant_res.data[0])
        from app.infrastructure.calendar.google_client import GoogleCalendarClient
        result = await GoogleCalendarClient.book_round_robin(
            tenant,
            date_str=payload.get("date_str"),
            time_str=payload.get("time_str"),
            duration_minutes=payload.get("duration", 30),
            user_name=payload.get("patient_name", "Reserva Manual UI"),
            phone=payload.get("phone", "+5600000000")
        )
        return result

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException):
        from app.core.exceptions import TenantNotFoundError
        if isinstance(exc, TenantNotFoundError):
            logger.warning(f"Ignored/Error reading tenant context: {exc}")
            return ORJSONResponse(status_code=200, content={"status": "ignored", "message": str(exc)})
            
        import traceback
        err_msg = f"Screaming Domain Core issue identified: {str(exc)}"
        full_trace = traceback.format_exc()
        logger.error(f"{err_msg}\n{full_trace}")
        

            
        # Send to Discord for devs
        from app.infrastructure.telemetry.discord_notifier import send_discord_alert
        await send_discord_alert(
            title="AppBaseException: Domain Logic Error",
            description=f"Path: `{request.url.path}`",
            error=exc,
            severity="warning"
        )
            
        return ORJSONResponse(status_code=500, content={"message": "Domain Logic Error", "error": str(exc), "traceback": full_trace})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        full_trace = traceback.format_exc()
        logger.error(f"FATAL UNHANDLED EXCEPTION: {str(exc)}\n{full_trace}")
        

            
        # Send to Discord for devs
        from app.infrastructure.telemetry.discord_notifier import send_discord_alert
        await send_discord_alert(
            title="FATAL: Unhandled Exception",
            description=f"Path: `{request.url.path}` | Method: `{request.method}`",
            error=exc,
            severity="error"
        )
            
        return ORJSONResponse(status_code=500, content={"message": "Internal Server Error", "error": str(exc), "traceback": full_trace})

    return app

app = create_app()
