# ================================================================================
# ⚠️  DOCS FIRST: Meta Webhook Signature Verification
#     Ref: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
#     Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
#
# ⚠️  OBSERVABILITY: Every error path reports to Sentry + Discord (§6).
# ================================================================================
import hmac
import hashlib

import sentry_sdk
from fastapi import Query, HTTPException

from app.core.config import settings
from app.infrastructure.telemetry.logger_service import logger
from app.infrastructure.telemetry.discord_notifier import send_discord_alert


# ============================================================
# E1: WhatsApp GET /webhook — Hub challenge verification
# This is the initial subscription handshake, NOT payload security.
# Ref: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#verification-requests
# ============================================================
async def verify_whatsapp_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    """Dependency to verify Meta Webhook validation requests upon subscribing."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp Webhook verification successful.")
        return int(hub_challenge)
    
    logger.warning("WhatsApp Webhook verification failed due to invalid token or mode.")
    sentry_sdk.capture_message(
        "WhatsApp webhook verification failed — invalid token or mode",
        level="warning"
    )
    await send_discord_alert(
        title="⚠️ Webhook Verification Failed",
        description=f"hub.mode={hub_mode}, hub.verify_token={'[REDACTED]' if hub_verify_token else 'MISSING'}",
        severity="warning"
    )
    raise HTTPException(status_code=403, detail="Verification failed")


# ============================================================
# E1: Webhook Payload Signature Verification (HMAC-SHA256)
#
# Meta sends X-Hub-Signature-256 header on every POST to /webhook.
# Format: "sha256=<hex_digest>"
# Key: META_APP_SECRET (App Secret from Meta Dashboard)
# Message: raw request body bytes (before JSON parsing)
#
# Ref: https://developers.facebook.com/docs/graph-api/webhooks/getting-started#event-notifications
# CRITICAL: Must use hmac.compare_digest() for timing-safe comparison
# ============================================================
async def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Verify the X-Hub-Signature-256 header from Meta webhooks.
    
    Returns True if signature is valid.
    Returns False if invalid (caller should reject with 401).
    
    If META_APP_SECRET is not configured, logs a warning and returns True (soft mode).
    """
    app_secret = (settings.META_APP_SECRET or "").strip()
    
    # Soft mode: if secret not configured, skip verification with a warning
    if not app_secret:
        logger.warning(
            "⚠️ [SECURITY] META_APP_SECRET not configured — webhook signature verification SKIPPED. "
            "This is a SECURITY RISK in production."
        )
        return True
    
    # Missing header = definitely not from Meta
    if not signature_header:
        logger.warning("⚠️ [SECURITY] Missing X-Hub-Signature-256 header")
        sentry_sdk.capture_message(
            "Webhook received without X-Hub-Signature-256 header",
            level="warning"
        )
        await send_discord_alert(
            title="🔒 Webhook Missing Signature",
            description="POST /webhook received without X-Hub-Signature-256 header. Possible spoofed request.",
            severity="warning"
        )
        return False
    
    # Parse "sha256=<hex>" format
    if not signature_header.startswith("sha256="):
        logger.warning(f"⚠️ [SECURITY] Malformed signature header: {signature_header[:50]}")
        sentry_sdk.capture_message(
            f"Malformed X-Hub-Signature-256 format: {signature_header[:50]}",
            level="warning"
        )
        await send_discord_alert(
            title="🔒 Malformed Webhook Signature",
            description=f"Header value doesn't start with 'sha256=': {signature_header[:50]}",
            severity="warning"
        )
        return False
    
    provided_sig = signature_header[7:]  # Strip "sha256="
    
    # Compute expected HMAC-SHA256
    try:
        expected_sig = hmac.new(
            app_secret.encode("utf-8"),
            raw_body,
            hashlib.sha256
        ).hexdigest()
    except Exception as e:
        logger.error(f"❌ [SECURITY] HMAC computation failed: {e}")
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="❌ HMAC Computation Failed",
            description=f"Failed to compute HMAC-SHA256 for webhook verification: {str(e)[:300]}",
            severity="error", error=e
        )
        return False
    
    # Timing-safe comparison (prevents timing attacks)
    # Ref: https://docs.python.org/3/library/hmac.html#hmac.compare_digest
    is_valid = hmac.compare_digest(expected_sig, provided_sig)
    
    if not is_valid:
        logger.warning("🔒 [SECURITY] INVALID webhook signature — request rejected")
        sentry_sdk.set_context("webhook_signature", {
            "provided_sig_prefix": provided_sig[:16] + "...",
            "expected_sig_prefix": expected_sig[:16] + "...",
            "body_length": len(raw_body),
        })
        sentry_sdk.capture_message(
            "Webhook signature mismatch — possible spoofed request",
            level="warning"
        )
        await send_discord_alert(
            title="🔒 INVALID Webhook Signature",
            description=(
                "X-Hub-Signature-256 does NOT match expected HMAC-SHA256.\n"
                "This could be a spoofed request or a misconfigured META_APP_SECRET.\n"
                f"Body length: {len(raw_body)} bytes"
            ),
            severity="warning"
        )
    
    return is_valid
