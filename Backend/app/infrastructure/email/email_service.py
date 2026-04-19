import os
import httpx
import logging
import sentry_sdk
from app.infrastructure.telemetry.discord_notifier import send_discord_alert

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = "alertas@tuasistentevirtual.cl"  # Verified domain requested by user
TO_EMAILS = ["tomasgemes@gmail.com", "instagramelectrimax@gmail.com"] # Default business staff recipients

# ============================================================
# Singleton httpx client for Resend API calls.
# Same rationale as discord_notifier.py: prevents socket
# exhaustion during network cascading failures.
# Ref: README §8 Design Patterns → Singleton pattern
# ============================================================
_resend_http_client: httpx.AsyncClient | None = None

def _get_resend_client() -> httpx.AsyncClient:
    global _resend_http_client
    if _resend_http_client is None:
        _resend_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0)
        )
    return _resend_http_client

async def send_business_email_alert(subject: str, html_body: str):
    """
    Sends an email alert to the business staff using Resend API.
    """
    if not RESEND_API_KEY:
        msg = "RESEND_API_KEY not configured. Skipping email alert."
        logger.warning(msg)
        sentry_sdk.capture_message(msg, level="warning")
        return

    payload = {
        "from": f"Sistema CRM <{FROM_EMAIL}>",
        "to": TO_EMAILS,
        "subject": subject,
        "html": html_body
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        client = _get_resend_client()
        res = await client.post("https://api.resend.com/emails", json=payload, headers=headers)
        if res.status_code >= 400:
            msg = f"Failed to send email alert via Resend: {res.text}"
            logger.error(msg)
            sentry_sdk.capture_message(msg, level="error")
            await send_discord_alert(
                title="❌ Email Alert Send Failed (HTTP Error)",
                description=f"Subject: {subject}\nStatus: {res.status_code}\nBody: {res.text[:300]}",
                severity="error"
            )
        else:
            logger.info(f"Email alert sent successfully: {subject}")
    except Exception as e:
        # Rule 9: every except → logger + sentry + discord
        logger.error(f"Failed to send email alert: {repr(e)}")
        sentry_sdk.capture_exception(e)
        await send_discord_alert(
            title="❌ Email Alert Network Failure",
            description=f"Subject: {subject}\nError: {repr(e)[:300]}",
            severity="error", error=e
        )
