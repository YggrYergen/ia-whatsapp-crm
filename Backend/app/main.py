# ================================================================================
# ⚠️  DOCS FIRST: Antes de modificar este archivo o diagnosticar errores,
#     consultar la documentación oficial actualizada de cada servicio:
#     - FastAPI: https://fastapi.tiangolo.com/
#     - Sentry Python: https://docs.sentry.io/platforms/python/integrations/fastapi/
#     - Cloud Run: https://cloud.google.com/run/docs/
#     - Supabase: https://supabase.com/docs
#
# ⚠️  LOGGING: Todo error debe ser capturado por Sentry con traceback completo.
#     Si Sentry no captura un error, es un BUG que se resuelve antes que el error en sí.
#     Cada excepción, timeout, API failure, y tool failure debe llegar a Sentry.
# ================================================================================
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

# Block R: Onboarding API routes (newcomer auto-provisioning + config agent chat)
from app.api.onboarding.provision import router as onboarding_provision_router
from app.api.onboarding.chat_endpoint import router as onboarding_chat_router

# Block R: Sandbox chat — isolated from webhook pipeline, uses Responses API
from app.api.sandbox.chat_endpoint import router as sandbox_chat_router

# Services, Resources, and Scheduling Config CRUD APIs
from app.api.services_api import router as services_router
from app.api.resources_api import router as resources_router
from app.api.scheduling_config_api import router as scheduling_config_router

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
    # ============================================================
    # Sentry SDK Init — Per official docs:
    # https://docs.sentry.io/platforms/python/integrations/fastapi/
    #
    # FastAPI integration auto-enables when sentry-sdk is installed.
    # No need to manually add FastApiIntegration unless customizing options.
    # ============================================================
    _sentry_dsn = settings.SENTRY_DSN or "https://b5b7a769848286fcfcc7f367a970c34f@o4511179991416832.ingest.us.sentry.io/4511184254402560"
    sentry_sdk.init(
        dsn=_sentry_dsn,
        # Per docs: send_default_pii=True to attach request headers, IP, etc.
        send_default_pii=True,
        # traces_sample_rate=1.0 captures 100% of transactions for tracing.
        # Keep at 1.0 during stabilization, reduce in production later.
        # Ref: https://docs.sentry.io/platforms/python/configuration/options/#traces-sample-rate
        traces_sample_rate=1.0,
        # Enable structured logs sent to Sentry (new feature)
        enable_logs=True,
        # Environment tag for filtering events in Sentry dashboard
        environment=settings.ENVIRONMENT,
    )
    logger.info(f"Sentry initialized | DSN={'configured' if settings.SENTRY_DSN else 'fallback'} | env={settings.ENVIRONMENT}")
    
    # Notice ORJSONResponse globally set
    app = FastAPI(
        title="WhatsApp AI CRM Refactor (Screaming Infrastructure)",
        version="0.3.0",
        lifespan=lifespan,
        default_response_class=ORJSONResponse
    )

    # ============================================================
    # Block E1: Webhook Signature Verification Middleware
    #
    # Intercepts POST /webhook and verifies X-Hub-Signature-256
    # BEFORE FastAPI processes the request body.
    # All other routes are unaffected.
    #
    # Ref: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#event-notifications
    # ============================================================
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request as StarletteRequest
    from starlette.responses import JSONResponse as StarletteJSONResponse
    from app.core.security import verify_webhook_signature

    class WebhookSignatureMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: StarletteRequest, call_next):
            # Only verify POST /webhook (the actual Meta webhook endpoint)
            if request.method == "POST" and request.url.path == "/webhook":
                try:
                    raw_body = await request.body()
                    signature = request.headers.get("X-Hub-Signature-256")
                    is_valid = await verify_webhook_signature(raw_body, signature)
                    if not is_valid:
                        return StarletteJSONResponse(
                            status_code=401,
                            content={"status": "error", "message": "Invalid webhook signature"}
                        )
                except Exception as e:
                    logger.error(f"❌ [SECURITY] Signature middleware crash: {e}")
                    sentry_sdk.capture_exception(e)
                    await send_discord_alert(
                        title="❌ Webhook Signature Middleware Crash",
                        description=f"Middleware raised exception: {str(e)[:300]}",
                        severity="error", error=e
                    )
                    # Fail OPEN in case of middleware crash (don't block legitimate traffic)
                    # This is a conscious trade-off: availability > security during middleware bugs
                    pass

            return await call_next(request)

    app.add_middleware(WebhookSignatureMiddleware)

    allowed_origins = [
        "https://dash.tuasistentevirtual.cl",
        "https://ohno.tuasistentevirtual.cl",  # Block R: Private frontend for onboarding
        "https://ia-whatsapp-crm.tomasgemes.workers.dev",
        os.getenv("FRONTEND_URL", ""),
    ]
    # Filter out empty strings
    allowed_origins = [o for o in allowed_origins if o]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        allow_credentials=True,
        # Block F1: Allow correlation ID header from frontend requests
        # Ref: https://github.com/snok/asgi-correlation-id#fastapi
        expose_headers=["X-Request-ID"],
    )

    # ============================================================
    # Block F2: Sentry Tags Middleware
    # Sets tenant_id + correlation_id as Sentry tags on EVERY request.
    # This makes it trivial to filter all Sentry events by tenant or request.
    #
    # Ref: https://docs.sentry.io/platforms/python/integrations/fastapi/
    # ============================================================
    from asgi_correlation_id import correlation_id as cid_ctx

    class SentryTagsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: StarletteRequest, call_next):
            # Set correlation ID tag on every request
            request_id = cid_ctx.get() or "-"
            sentry_sdk.set_tag("correlation_id", request_id)

            # Try to extract tenant_id from the request path or state
            # This will be populated after the webhook handler parses the payload
            # For now, set a default that gets overwritten in the use case
            sentry_sdk.set_tag("request_path", request.url.path)

            response = await call_next(request)
            return response

    app.add_middleware(SentryTagsMiddleware)

    # ============================================================
    # Block F1: Correlation ID Middleware
    # Generates a unique ID for each request. Stored in context var,
    # accessible via `from asgi_correlation_id import correlation_id`.
    # Auto-integrates with Sentry (sets transaction_id).
    #
    # MUST be the outermost middleware (added last) so the ID is
    # available to all downstream middleware and handlers.
    #
    # Ref: https://github.com/snok/asgi-correlation-id
    # ============================================================
    from asgi_correlation_id import CorrelationIdMiddleware

    app.add_middleware(CorrelationIdMiddleware)

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
    
    # Block R: Onboarding routes
    app.include_router(onboarding_provision_router)
    app.include_router(onboarding_chat_router)
    
    # Block R: Sandbox chat — isolated, uses Responses API
    app.include_router(sandbox_chat_router)

    # Services, Resources, and Scheduling Config CRUD APIs
    app.include_router(services_router)
    app.include_router(resources_router)
    app.include_router(scheduling_config_router)

    @app.api_route("/api/debug-ping", methods=["GET", "HEAD"])
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
        from supabase import create_async_client
        # Use service role or anon key from settings
        db = await create_async_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        
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
            tenant_data.setdefault('llm_model', 'gpt-5.4-mini')
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
            sentry_sdk.capture_exception(e)
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
            sentry_sdk.capture_exception(e)
            # If table still not found, we log it clearly
            return ORJSONResponse(status_code=500, content={"status": "error", "message": str(e)})

    @app.get("/api/calendar/events")
    async def api_get_calendar_events(start_iso: str, end_iso: str, tenant_id: str = "d8376510-911e-42ef-9f3b-e018d9f10915"):
        """Fetch structured calendar events for the frontend AgendaView.
        
        Now uses NativeSchedulingService (Supabase) instead of GoogleCalendarClient.
        Ref: native_calendar_plan.md §5 — Frontend proxy routes: keep API shape, swap backend.
        """
        try:
            from app.modules.scheduling.native_service import NativeSchedulingService
            return await NativeSchedulingService.get_structured_events(tenant_id, start_iso, end_iso)
        except Exception as e:
            logger.error(f"Calendar events error: {e}", exc_info=True)
            sentry_sdk.capture_exception(e)
            from app.infrastructure.telemetry.discord_notifier import send_discord_alert
            await send_discord_alert(
                title=f"❌ /api/calendar/events Failed | Tenant {tenant_id}",
                description=f"**Range:** {start_iso} → {end_iso}\n**Error:** ```{str(e)[:300]}```",
                severity="error",
                error=e,
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Error interno al obtener eventos del calendario."})

    @app.post("/api/calendar/book")
    async def api_book_calendar_event(payload: dict = Body(...)):
        """Book a calendar event from the frontend manual booking modal.
        
        Now uses NativeSchedulingService (Supabase) instead of GoogleCalendarClient.
        EXCLUDE USING gist constraint prevents double-booking at DB level.
        """
        tenant_id = payload.get("tenant_id", "d8376510-911e-42ef-9f3b-e018d9f10915")
        try:
            from app.infrastructure.database.supabase_client import SupabasePooler
            db = await SupabasePooler.get_client()
            tenant_res = await db.table("tenants").select("*").eq("id", tenant_id).execute()
            if not tenant_res.data:
                return {"status": "error", "message": "Tenant not found"}
            from app.core.models import TenantContext
            tenant = TenantContext(**tenant_res.data[0])
            from app.modules.scheduling.native_service import NativeSchedulingService
            result = await NativeSchedulingService.book_appointment(
                tenant,
                date_str=payload.get("date_str"),
                time_str=payload.get("time_str"),
                duration_minutes=payload.get("duration", 30),
                user_name=payload.get("patient_name", "Reserva Manual UI"),
                patient_phone=payload.get("phone", "+5600000000"),
                booked_by="manual_ui",
            )
            return result
        except Exception as e:
            logger.error(f"Calendar book error: {e}", exc_info=True)
            sentry_sdk.capture_exception(e)
            from app.infrastructure.telemetry.discord_notifier import send_discord_alert
            await send_discord_alert(
                title=f"❌ /api/calendar/book Failed | Tenant {tenant_id}",
                description=f"**Payload:** {str(payload)[:300]}\n**Error:** ```{str(e)[:300]}```",
                severity="error",
                error=e,
            )
            return ORJSONResponse(status_code=500, content={"status": "error", "message": "Error interno al agendar cita."})

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
        
        # Sentry: capture explicitly since our custom handler intercepts before auto-capture
        # Ref: https://docs.sentry.io/platforms/python/integrations/fastapi/#issue-reporting
        sentry_sdk.capture_exception(exc)
            
        # Send to Discord for devs
        from app.infrastructure.telemetry.discord_notifier import send_discord_alert
        await send_discord_alert(
            title="AppBaseException: Domain Logic Error",
            description=f"Path: `{request.url.path}`",
            error=exc,
            severity="warning"
        )
            
        return ORJSONResponse(status_code=500, content={"message": "Error de lógica de dominio.", "code": "DOMAIN_ERROR"})

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        full_trace = traceback.format_exc()
        logger.error(f"FATAL UNHANDLED EXCEPTION: {str(exc)}\n{full_trace}")
        
        # Sentry: capture explicitly since our custom handler intercepts before auto-capture
        # Ref: https://docs.sentry.io/platforms/python/integrations/fastapi/#issue-reporting
        sentry_sdk.capture_exception(exc)
            
        # Send to Discord for devs
        from app.infrastructure.telemetry.discord_notifier import send_discord_alert
        await send_discord_alert(
            title="FATAL: Unhandled Exception",
            description=f"Path: `{request.url.path}` | Method: `{request.method}`",
            error=exc,
            severity="error"
        )
            
        return ORJSONResponse(status_code=500, content={"message": "Error interno del servidor.", "code": "INTERNAL_ERROR"})

    return app

app = create_app()
