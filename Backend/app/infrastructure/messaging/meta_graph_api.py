import httpx
import sentry_sdk
from app.infrastructure.telemetry.logger_service import logger

class MetaGraphAPIClient:
    """Async Adapter for WhatsApp Cloud API v25.0 with Singleton Pooling Limits.
    
    Ref: https://developers.facebook.com/docs/graph-api/changelog/version25.0
    v19.0 deprecated May 21, 2026. Updated 2026-04-11.
    """
    
    BASE_URL = "https://graph.facebook.com/v25.0"
    _http_client: httpx.AsyncClient = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._http_client is None:
            # Aggressive connection limits tailored for socket resilience under scale.
            limits = httpx.Limits(max_keepalive_connections=50, max_connections=100)
            cls._http_client = httpx.AsyncClient(limits=limits, timeout=10.0)
        return cls._http_client

    @staticmethod
    async def send_text_message(phone_number_id: str, to: str, text: str, token: str) -> dict:
        url = f"{MetaGraphAPIClient.BASE_URL}/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        
        client = MetaGraphAPIClient.get_client()
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.debug(f"WhatsApp text IO sent natively. Graph Node Reply -> {response.text}")
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Meta Graph Connection HTTP issue: {e.response.text}")
            sentry_sdk.set_context("meta_graph_api", {"phone_number_id": phone_number_id, "to": to, "status_code": e.response.status_code, "response_body": e.response.text[:500]})
            sentry_sdk.capture_exception(e)
            raise
        except Exception as e:
            # repr() because ConnectError and similar httpx exceptions return empty str()
            logger.error(f"Hardware/Network HTTP layer error: {repr(e)}")
            sentry_sdk.capture_exception(e)
            raise
