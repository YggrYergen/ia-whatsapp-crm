import os
import httpx
import traceback
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# ============================================================
# Environment auto-detection for Discord alerts.
# When ENVIRONMENT != "production", ALL alerts are prefixed
# with [🔧 DESARROLLO] so it's impossible to confuse dev
# alerts with production alerts in Discord.
# Ref: controlled by ENVIRONMENT env var in Cloud Run.
# ============================================================
_IS_PRODUCTION = (getattr(settings, "ENVIRONMENT", "development") == "production")
_ENV_PREFIX = "" if _IS_PRODUCTION else "[🔧 DESARROLLO] "
_ENV_LABEL = "production" if _IS_PRODUCTION else "desarrollo"

async def send_discord_alert(title: str, description: str, error: Exception = None, severity: str = "error"):
    """
    Sends an alert to Discord using Webhooks.
    Severity can be 'error', 'warning', 'info'
    
    In non-production environments, all titles are auto-prefixed
    with [🔧 DESARROLLO] for immediate visual distinction.
    """
    webhook_url = getattr(settings, "DISCORD_WEBHOOK_URL", None)
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not configured. Skipping alert.")
        return

    color_map = {
        "error": 16711680,   # Red
        "warning": 16776960, # Yellow
        "info": 3447003      # Blue
    }
    
    embed = {
        "title": f"{_ENV_PREFIX}{title}",
        "description": description,
        "color": color_map.get(severity, 16711680),
        "fields": [
            {
                "name": "🌍 Environment",
                "value": f"`{_ENV_LABEL}`",
                "inline": True
            }
        ]
    }

    if error:
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        # Truncate traceback if it exceeds Discord's limit of 1024 chars per field
        if len(tb) > 1000:
            tb = tb[-1000:]
            
        embed["fields"].append({
            "name": "Traceback",
            "value": f"```python\n{tb}\n```",
            "inline": False
        })
        embed["fields"].append({
            "name": "Exception Type",
            "value": type(error).__name__,
            "inline": True
        })

    payload = {
        "embeds": [embed]
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=5.0)
    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")

