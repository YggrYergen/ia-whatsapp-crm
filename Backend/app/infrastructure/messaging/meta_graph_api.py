import httpx
from app.infrastructure.telemetry.logger_service import logger

class MetaGraphAPIClient:
    """Async Adapter for WhatsApp Cloud API v19.0 with Singleton Pooling Limits."""
    
    BASE_URL = "https://graph.facebook.com/v19.0"
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
            raise
        except Exception as e:
            logger.error(f"Hardware/Network HTTP layer error: {str(e)}")
            raise
