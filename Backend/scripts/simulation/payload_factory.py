# ================================================================================
# Phase 5A: Meta Webhook Payload Factory
# ================================================================================
# Generates payloads that EXACTLY match the official Meta Cloud API webhook format.
# Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
#
# All payloads include "is_simulation": true at root to skip Meta API sends
# and debounce delays in the backend pipeline.
# ================================================================================

import uuid
import time
import base64
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────
# These match the dev Supabase tenant record (verified via MCP):
#   tenant_id: d8376510-911e-42ef-9f3b-e018d9f10915
#   ws_phone_id: 123456789012345
DEFAULT_PHONE_NUMBER_ID = "123456789012345"
DEFAULT_DISPLAY_NUMBER = "15550001111"
DEFAULT_WABA_ID = "102290129340398"


def _generate_wamid() -> str:
    """Generate a realistic-looking WhatsApp message ID."""
    raw = uuid.uuid4().bytes
    encoded = base64.b64encode(raw).decode("utf-8").rstrip("=")
    return f"wamid.{encoded}"


def _current_timestamp() -> str:
    """Unix timestamp as string, matching Meta's format."""
    return str(int(time.time()))


# ── Core Payload Builders ──────────────────────────────────────────────

def make_text_message(
    from_number: str,
    text: str,
    profile_name: str = "Sim User",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    display_phone_number: str = DEFAULT_DISPLAY_NUMBER,
    waba_id: str = DEFAULT_WABA_ID,
) -> dict:
    """
    Standard text message webhook payload.
    This is the most common payload type — a user sends a text message.
    
    Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples#incoming-messages
    """
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": display_phone_number,
                        "phone_number_id": phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": profile_name},
                        "wa_id": from_number,
                    }],
                    "messages": [{
                        "from": from_number,
                        "id": _generate_wamid(),
                        "timestamp": _current_timestamp(),
                        "type": "text",
                        "text": {"body": text},
                    }],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


def make_status_update(
    message_id: str = "wamid.TEST_STATUS_ID",
    status: str = "delivered",
    recipient_id: str = "16505551234",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    display_phone_number: str = DEFAULT_DISPLAY_NUMBER,
    waba_id: str = DEFAULT_WABA_ID,
) -> dict:
    """
    Delivery/read status webhook — no messages array.
    The backend should gracefully skip these (field=messages but no messages key).
    
    Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples#outgoing-messages
    """
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": display_phone_number,
                        "phone_number_id": phone_number_id,
                    },
                    "statuses": [{
                        "id": message_id,
                        "status": status,
                        "timestamp": _current_timestamp(),
                        "recipient_id": recipient_id,
                        "conversation": {
                            "id": "conv_" + uuid.uuid4().hex[:16],
                            "origin": {"type": "service"},
                        },
                        "pricing": {
                            "billable": True,
                            "pricing_model": "CBP",
                            "category": "service",
                        },
                    }],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


def make_image_message(
    from_number: str,
    image_id: str = "img_123456789",
    mime_type: str = "image/jpeg",
    caption: Optional[str] = None,
    profile_name: str = "Sim User",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    display_phone_number: str = DEFAULT_DISPLAY_NUMBER,
    waba_id: str = DEFAULT_WABA_ID,
) -> dict:
    """
    Image message webhook. The backend currently only handles text messages,
    so this should gracefully degrade (no crash, logs warning).
    """
    msg = {
        "from": from_number,
        "id": _generate_wamid(),
        "timestamp": _current_timestamp(),
        "type": "image",
        "image": {
            "id": image_id,
            "mime_type": mime_type,
            "sha256": "abc123def456",
        },
    }
    if caption:
        msg["image"]["caption"] = caption
    
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": display_phone_number,
                        "phone_number_id": phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": profile_name},
                        "wa_id": from_number,
                    }],
                    "messages": [msg],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


def make_location_message(
    from_number: str,
    latitude: float = -33.4489,
    longitude: float = -70.6693,
    name: Optional[str] = "Santiago, Chile",
    address: Optional[str] = None,
    profile_name: str = "Sim User",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    display_phone_number: str = DEFAULT_DISPLAY_NUMBER,
    waba_id: str = DEFAULT_WABA_ID,
) -> dict:
    """Location message webhook payload."""
    location = {"latitude": latitude, "longitude": longitude}
    if name:
        location["name"] = name
    if address:
        location["address"] = address
    
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": display_phone_number,
                        "phone_number_id": phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": profile_name},
                        "wa_id": from_number,
                    }],
                    "messages": [{
                        "from": from_number,
                        "id": _generate_wamid(),
                        "timestamp": _current_timestamp(),
                        "type": "location",
                        "location": location,
                    }],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


def make_reaction_message(
    from_number: str,
    emoji: str = "👍",
    reacted_message_id: str = "wamid.REACTED_MSG",
    profile_name: str = "Sim User",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    display_phone_number: str = DEFAULT_DISPLAY_NUMBER,
    waba_id: str = DEFAULT_WABA_ID,
) -> dict:
    """Reaction message webhook payload."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": waba_id,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": display_phone_number,
                        "phone_number_id": phone_number_id,
                    },
                    "contacts": [{
                        "profile": {"name": profile_name},
                        "wa_id": from_number,
                    }],
                    "messages": [{
                        "from": from_number,
                        "id": _generate_wamid(),
                        "timestamp": _current_timestamp(),
                        "type": "reaction",
                        "reaction": {
                            "message_id": reacted_message_id,
                            "emoji": emoji,
                        },
                    }],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


# ── Malformed / Edge Case Payloads ─────────────────────────────────────

def make_malformed_no_entry() -> dict:
    """Missing 'entry' array — should trigger error handling."""
    return {
        "object": "whatsapp_business_account",
        "is_simulation": True,
    }


def make_malformed_no_changes() -> dict:
    """Has entry but no changes — should trigger error handling."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": DEFAULT_WABA_ID}],
        "is_simulation": True,
    }


def make_malformed_no_metadata() -> dict:
    """Has changes but no metadata/phone_number_id — should fail tenant lookup."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": DEFAULT_WABA_ID,
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": "56900000000",
                        "id": _generate_wamid(),
                        "timestamp": _current_timestamp(),
                        "type": "text",
                        "text": {"body": "orphan message"},
                    }],
                },
                "field": "messages",
            }],
        }],
        "is_simulation": True,
    }


def make_empty_message_body(
    from_number: str = "56900000001",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
) -> dict:
    """Text message with empty body string."""
    return make_text_message(
        from_number=from_number,
        text="",
        profile_name="Empty Msg User",
        phone_number_id=phone_number_id,
    )


def make_very_long_message(
    from_number: str = "56900000002",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
    length: int = 5000,
) -> dict:
    """Text message with a very long body (stress test LLM context)."""
    long_text = "Este es un mensaje muy largo. " * (length // 30)
    return make_text_message(
        from_number=from_number,
        text=long_text[:length],
        profile_name="Long Msg User",
        phone_number_id=phone_number_id,
    )


def make_special_characters_message(
    from_number: str = "56900000003",
    phone_number_id: str = DEFAULT_PHONE_NUMBER_ID,
) -> dict:
    """Text with emojis, unicode, special chars — encoding stress test."""
    return make_text_message(
        from_number=from_number,
        text="Hola! 🇨🇱 ¿Cómo están? <script>alert('xss')</script> 日本語 \\ \" ' \n\ttabs & más 💉🏥",
        profile_name="Spëcial Çhàrs 🎭",
        phone_number_id=phone_number_id,
    )
