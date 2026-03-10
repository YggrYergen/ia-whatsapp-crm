import os
import httpx
from logger import logger

async def send_whatsapp_message(phone_number: str, text: str, phone_number_id: str, token: str):
    """
    Sifts a message cleanly back to the WhatsApp Cloud API.
    Uses the modern v19.0 API or later.
    """
    # Meta Graph API Base URL
    GRAPH_API_VERSION = "v19.0"
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{phone_number_id}/messages"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Meta requires payload for Sending text specific structure:
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=10.0)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully sent WhatsApp message to {phone_number}")
                return response.json()
            else:
                logger.error(f"Failed to send WhatsApp message. Status: {response.status_code}, Response: {response.text}")
                return None
    except Exception as e:
        logger.exception(f"Error calling WhatsApp API: {str(e)}")
        return None
