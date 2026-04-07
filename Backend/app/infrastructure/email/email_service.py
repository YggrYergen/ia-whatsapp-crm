import os
import httpx
import logging

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = "alertas@tuasistentevirtual.cl"  # Verified domain requested by user
TO_EMAILS = ["tomasgemes@gmail.com", "instagramelectrimax@gmail.com"] # Default business staff recipients

async def send_business_email_alert(subject: str, html_body: str):
    """
    Sends an email alert to the business staff using Resend API.
    """
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured. Skipping email alert.")
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
        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.resend.com/emails", json=payload, headers=headers, timeout=5.0)
            if res.status_code >= 400:
                logger.error(f"Failed to send email alert via Resend: {res.text}")
            else:
                logger.info(f"Email alert sent successfully: {subject}")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
