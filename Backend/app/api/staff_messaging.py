"""
Staff Messaging API — POST /api/staff/send-message

Sends outbound WhatsApp messages on behalf of human agents (staff/admins).

Flow:
  1. Frontend saves message to Supabase (sender_role=human_agent) — already done
  2. Frontend calls THIS endpoint to deliver it via WhatsApp
  3. Validates the contact BELONGS to the specified tenant (RLS enforcement)
  4. Checks last_message_at to warn about 24h window before making the API call
  5. Calls MetaGraphAPIClient.send_text_message()
  6. If Meta returns 131047 (24h window expired), returns structured error
     with contact info so staff can reach them by other means

Tenant Isolation (RLS):
  - The contact is looked up by BOTH contact_id AND tenant_id.
  - If the contact doesn't belong to the tenant, the request is rejected.
  - This prevents cross-tenant data leakage even if someone forges a request.

Meta 24h Messaging Window:
  - WhatsApp API only allows free-form text messages within 24 hours
    of the customer's last inbound message.
  - After 24h, only pre-approved template messages are allowed (error 131047).
  - We pre-check `last_message_at` in the DB as a soft guard, and handle
    the Meta API 131047 response gracefully if the soft guard misses.
  - Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages
  - Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes (131047)

Observability: Every except block → logger + Sentry + Discord (Rule #5).
"""

import datetime
import sentry_sdk
from fastapi import APIRouter, Body
import httpx

from app.core.config import settings
from app.infrastructure.database.supabase_client import SupabasePooler
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert

router = APIRouter(prefix="/api/staff", tags=["Staff Messaging"])

_WHERE = "staff_messaging"


@router.post("/send-message")
async def send_staff_message(payload: dict = Body(...)):
    """Send a WhatsApp message from staff to a customer.
    
    Expected payload:
      {
        "tenant_id": "uuid",
        "contact_id": "uuid",
        "phone": "56912345678",
        "message": "Hola, te escribimos desde..."
      }
    
    The message is already persisted in Supabase by the frontend.
    This endpoint only handles the WhatsApp delivery.
    
    Returns:
      200 on success: {"status": "sent", ...}
      200 with status=error on business logic failure (24h window, etc.)
    """
    _where = f"{_WHERE}.send_staff_message"
    
    tenant_id = payload.get("tenant_id", "")
    contact_id = payload.get("contact_id", "")
    phone = payload.get("phone", "")
    message = payload.get("message", "")
    
    _ctx = (
        f"tenant={tenant_id} | contact={contact_id} | "
        f"to={phone} | len={len(message)} | env={settings.ENVIRONMENT}"
    )
    
    # ── Input validation ──
    if not tenant_id or not phone or not message:
        return {
            "status": "error",
            "error_code": "MISSING_FIELDS",
            "message": "tenant_id, phone y message son obligatorios."
        }
    
    logger.info(f"📤 [{_where}] Staff send request | {_ctx}")
    
    try:
        db = await SupabasePooler.get_client()
        
        # ── 1. RLS: Verify contact belongs to this tenant ──
        # This prevents cross-tenant leakage even if someone forges a request.
        if contact_id:
            contact_check = await (
                db.table("contacts")
                .select("id, phone_number, name, last_message_at")
                .eq("id", contact_id)
                .eq("tenant_id", tenant_id)
                .execute()
            )
            if not contact_check.data:
                _msg = (
                    f"[{_where}] RLS VIOLATION: contact_id={contact_id} "
                    f"does NOT belong to tenant={tenant_id}"
                )
                logger.error(_msg)
                sentry_sdk.capture_message(_msg, level="error")
                await send_discord_alert(
                    title="🔒 RLS Violation — Staff Send Blocked",
                    description=(
                        f"**Where:** `{_where}`\n"
                        f"**Contact:** {contact_id}\n"
                        f"**Tenant:** {tenant_id}\n"
                        f"**Phone:** {phone}"
                    ),
                    severity="error"
                )
                return {
                    "status": "error",
                    "error_code": "CONTACT_NOT_FOUND",
                    "message": "Contacto no encontrado para este tenant."
                }
            
            contact_data = contact_check.data[0]
            last_msg = contact_data.get("last_message_at")
            
            # ── 2. Soft guard: check 24h window ──
            # Meta error 131047: "Re-engage using an approved template"
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
            if last_msg:
                try:
                    last_msg_dt = datetime.datetime.fromisoformat(last_msg.replace("Z", "+00:00"))
                    now = datetime.datetime.now(datetime.timezone.utc)
                    hours_since = (now - last_msg_dt).total_seconds() / 3600
                    
                    if hours_since > 24:
                        _msg = (
                            f"⏰ [{_where}] 24h window expired | "
                            f"last_msg={last_msg} ({hours_since:.1f}h ago) | {_ctx}"
                        )
                        logger.warning(_msg)
                        return {
                            "status": "error",
                            "error_code": "WINDOW_EXPIRED",
                            "message": (
                                f"⏰ La ventana de 24h expiró. "
                                f"El último mensaje del cliente fue hace {hours_since:.0f} horas. "
                                f"WhatsApp no permite mensajes de texto libre después de 24h. "
                                f"Puedes contactar directamente al cliente:"
                            ),
                            "contact_info": {
                                "name": contact_data.get("name", "Sin nombre"),
                                "phone": contact_data.get("phone_number", phone),
                            },
                            "hours_since_last_message": round(hours_since, 1),
                        }
                except (ValueError, TypeError) as parse_err:
                    # Non-blocking: if we can't parse the date, proceed and let Meta decide
                    logger.warning(
                        f"[{_where}] Could not parse last_message_at={last_msg}: {parse_err}"
                    )
        
        # ── 3. Look up tenant WhatsApp credentials ──
        tenant_res = await (
            db.table("tenants")
            .select("ws_phone_id, ws_token, name")
            .eq("id", tenant_id)
            .execute()
        )
        
        if not tenant_res.data:
            _msg = f"[{_where}] Tenant not found: {tenant_id}"
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            return {
                "status": "error",
                "error_code": "TENANT_NOT_FOUND",
                "message": "Tenant no encontrado."
            }
        
        tenant = tenant_res.data[0]
        ws_phone_id = tenant.get("ws_phone_id")
        ws_token = tenant.get("ws_token")
        
        if not ws_phone_id or not ws_token:
            _msg = (
                f"[{_where}] Tenant {tenant_id} ({tenant.get('name')}) "
                f"missing WhatsApp credentials | "
                f"ws_phone_id={bool(ws_phone_id)} ws_token={bool(ws_token)}"
            )
            logger.error(_msg)
            sentry_sdk.capture_message(_msg, level="error")
            await send_discord_alert(
                title="⚠️ Staff Send Failed — Missing WA Credentials",
                description=(
                    f"**Tenant:** {tenant.get('name')} (`{tenant_id}`)\n"
                    f"**To:** {phone}"
                ),
                severity="warning"
            )
            return {
                "status": "error",
                "error_code": "WA_NOT_CONFIGURED",
                "message": "WhatsApp no está configurado para este tenant."
            }
        
        # ── 4. Send via Meta Graph API ──
        try:
            response = await MetaGraphAPIClient.send_text_message(
                phone_number_id=ws_phone_id,
                to=phone,
                text=message,
                token=ws_token
            )
            
            logger.info(
                f"✅ [{_where}] Staff message delivered | {_ctx} | "
                f"wa_response={str(response)[:200]}"
            )
            return {"status": "sent", "wa_response": response}
            
        except httpx.HTTPStatusError as http_err:
            # Parse Meta error code from response body
            error_body = http_err.response.text
            status_code = http_err.response.status_code
            
            _msg = (
                f"[{_where}] Meta API error {status_code} | {_ctx} | "
                f"body={error_body[:400]}"
            )
            logger.error(_msg)
            
            # Check for 131047: 24-hour window expired
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/support/error-codes
            if "131047" in error_body:
                logger.warning(
                    f"⏰ [{_where}] Meta 131047 — 24h window closed | {_ctx}"
                )
                # Fetch contact info for the error response
                contact_name = "Cliente"
                contact_phone = phone
                if contact_id:
                    try:
                        cinfo = await (
                            db.table("contacts")
                            .select("name, phone_number")
                            .eq("id", contact_id)
                            .eq("tenant_id", tenant_id)
                            .execute()
                        )
                        if cinfo.data:
                            contact_name = cinfo.data[0].get("name", "Cliente")
                            contact_phone = cinfo.data[0].get("phone_number", phone)
                    except Exception:
                        pass  # Non-blocking: use defaults
                
                return {
                    "status": "error",
                    "error_code": "WINDOW_EXPIRED",
                    "message": (
                        f"⏰ La ventana de 24h de WhatsApp expiró. "
                        f"No es posible enviar mensajes de texto libre a este contacto. "
                        f"Contacta directamente:"
                    ),
                    "contact_info": {
                        "name": contact_name,
                        "phone": contact_phone,
                    },
                }
            
            # Check for 131026: not a WhatsApp number
            if "131026" in error_body:
                return {
                    "status": "error",
                    "error_code": "NOT_WA_NUMBER",
                    "message": (
                        f"El número {phone} no está registrado en WhatsApp "
                        f"o no acepta mensajes de empresas."
                    ),
                }
            
            # Generic Meta API error
            sentry_sdk.set_context("meta_graph_staff_send", {
                "tenant_id": tenant_id,
                "phone": phone,
                "status_code": status_code,
                "error_body": error_body[:500],
            })
            sentry_sdk.capture_exception(http_err)
            await send_discord_alert(
                title=f"💥 Staff Send — Meta API Error {status_code}",
                description=(
                    f"**Where:** `{_where}`\n"
                    f"**Tenant:** {tenant.get('name')}\n"
                    f"**To:** {phone}\n"
                    f"**Error:** ```{error_body[:300]}```"
                ),
                severity="error"
            )
            return {
                "status": "error",
                "error_code": "META_API_ERROR",
                "message": f"Error de WhatsApp ({status_code}): {error_body[:200]}",
            }
    
    except Exception as exc:
        _msg = f"[{_where}] Unexpected failure | {_ctx} | error={str(exc)[:300]}"
        logger.error(_msg, exc_info=True)
        sentry_sdk.capture_exception(exc)
        await send_discord_alert(
            title="💥 Staff Send — Unexpected Error",
            description=(
                f"**Where:** `{_where}`\n"
                f"**To:** {phone}\n"
                f"**Error:** {str(exc)[:300]}"
            ),
            severity="error"
        )
        return {
            "status": "error",
            "error_code": "INTERNAL_ERROR",
            "message": f"Error interno: {str(exc)[:200]}"
        }
