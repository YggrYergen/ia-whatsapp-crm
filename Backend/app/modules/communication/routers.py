from fastapi import APIRouter, Depends, BackgroundTasks, Body
from supabase import Client
from app.infrastructure.database.supabase_client import get_db
from app.core.security import verify_whatsapp_webhook
from app.api.dependencies import get_tenant_context_from_payload
from app.modules.communication.use_cases import ProcessMessageUseCase
from app.infrastructure.telemetry.logger_service import logger

router = APIRouter(prefix="/webhook", tags=["Webhook Handlers"])

@router.get("")
async def verify_webhook(challenge: int = Depends(verify_whatsapp_webhook)):
    return challenge

@router.post("")
async def handle_whatsapp_webhook(
    background_tasks: BackgroundTasks,
    payload: dict = Body(...),
    db: Client = Depends(get_db)
):
    logger.debug("Received incoming WebHook iteration.")
    
    # 2. Invoke dependencies bypassing request flow limitations.
    tenant = await get_tenant_context_from_payload(payload, db)
    
    # 3. Offload Logic gracefully.
    background_tasks.add_task(ProcessMessageUseCase.execute, payload=payload, tenant=tenant, db=db)
    return {"status": "enqueued", "tenant_id": tenant.id}
