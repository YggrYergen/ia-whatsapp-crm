import asyncio
from supabase import AsyncClient
import json
import re
import pytz
from datetime import datetime
from app.core.models import TenantContext
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.modules.intelligence.router import LLMFactory
from app.infrastructure.telemetry.logger_service import logger
from app.modules.intelligence.tool_registry import tool_registry
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
import sentry_sdk
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

# ============================================================
# BUG-1 Layer 1: Internal System Prompt — Tool-Use Contract
# These rules are injected at the CODE level, appended AFTER the
# tenant-editable prompt. The tenant CANNOT modify or delete them.
# This prevents the LLM from claiming it performed actions without
# actually calling the corresponding tool functions.
# ============================================================
INTERNAL_TOOL_RULES = """
[REGLAS INTERNAS DEL SISTEMA — NO MODIFICAR]
- NUNCA afirmes que realizarás o realizaste una acción (agendar, cancelar, escalar, evaluar) sin EJECUTAR la herramienta correspondiente.
- Si no puedes ejecutar una herramienta, admítelo honestamente al paciente.
- Para escalar a un humano SIEMPRE usa 'request_human_escalation'. NO digas "voy a notificar" sin llamarla.
- Para cancelar citas SIEMPRE usa 'delete_appointment'.
- Para agendar SIEMPRE usa 'book_round_robin'.
- Para evaluar scoring SIEMPRE usa 'update_patient_scoring'.
- Si un resultado de herramienta indica ERROR, informa al paciente honestamente que la acción NO se completó.
- Cuando el paciente SOLICITA una acción (agendar, cancelar, mover, reagendar cita), EJECÚTALA INMEDIATAMENTE con la herramienta. NO pidas confirmación secundaria como "¿Quieres que proceda?", "¿Confirmas?", o "¿Deseas que lo haga?". El paciente ya confirmó su intención al solicitarla. Solo pide confirmación si FALTA información obligatoria (fecha, hora, servicio).
""".strip()

# ============================================================
# BUG-1 Layer 2: Silent Failure Detection Patterns
# Maps tool names to text patterns that indicate the LLM is
# claiming to perform the action without actually calling the tool.
# ============================================================
TOOL_ACTION_PATTERNS = [
    ("request_human_escalation", ["escalar", "derivar a humano", "notificar a un agente", "transferir a", "asistencia humana", "voy a notificar"]),
    ("update_patient_scoring", ["actualizar scoring", "puntaje", "evaluación de celulitis", "celludetox"]),
    ("delete_appointment", ["cancelar cita", "eliminar cita", "cancelar tu hora", "cita ha sido cancelada"]),
    ("book_round_robin", ["agendar", "reservar", "quedó confirmado", "cita confirmada", "reservar una hora"]),
    ("get_merged_availability", ["verificar disponibilidad", "horarios disponibles"]),
]


# ============================================================
# MEDIA HANDLING: Helper functions for WhatsApp media pipeline
# Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components#messages-object
# Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
# ============================================================

def _build_llm_content_for_media(
    text_body: str, message_type: str, media_metadata: dict | None
) -> str:
    """Build descriptive text for LLM when user sends media.
    The LLM cannot see images/files, so we describe what was sent.
    This replaces the raw empty string with meaningful context.
    """
    if message_type == "text" or not media_metadata:
        return text_body

    TYPE_LABELS = {
        "image": "una imagen/foto",
        "document": "un documento",
        "audio": "un audio/nota de voz",
        "video": "un video",
        "sticker": "un sticker",
    }

    label = TYPE_LABELS.get(message_type, f"un archivo de tipo {message_type}")
    parts = [f"[El usuario envió {label}"]

    if media_metadata.get("filename"):
        parts.append(f" llamado '{media_metadata['filename']}'")
    if media_metadata.get("mime_type"):
        parts.append(f" ({media_metadata['mime_type'].split(';')[0].strip()})")
    parts.append("]")

    if text_body:  # caption
        parts.append(f"\nMensaje adjunto: {text_body}")

    return "".join(parts)


async def _download_and_store_media(
    db: AsyncClient, tenant: TenantContext, contact_id: str,
    message_id: str, message_type: str, media_metadata: dict
):
    """Fire-and-forget: downloads media from Meta Cloud API, uploads to Supabase Storage.
    Updates the message record with storage_path on completion.

    This runs in the background via asyncio.create_task() — does NOT block the LLM pipeline.

    Retry strategy: 3 attempts with exponential backoff (2s, 4s, 8s) for transient errors.
    Permanent errors (401, 403) fail immediately without retry.

    Two-step Meta media download (per docs):
    1. GET /v25.0/<MEDIA_ID> → returns {url, mime_type, sha256, file_size}
    2. GET <url> with Bearer token → returns binary content

    Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media
    """
    media_id = media_metadata.get("media_id")
    if not media_id:
        logger.warning(f"⚠️ [MEDIA] No media_id in metadata, skipping download | msg={message_id}")
        return

    MAX_RETRIES = 3

    try:
        file_bytes = None
        media_url = None
        file_size = None
        last_err = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                client = MetaGraphAPIClient.get_client()

                # Step 1: Get ephemeral download URL from Meta (expires in ~5 min)
                url_response = await client.get(
                    f"{MetaGraphAPIClient.BASE_URL}/{media_id}",
                    headers={"Authorization": f"Bearer {tenant.ws_token}"},
                    params={"phone_number_id": tenant.ws_phone_id},
                )
                # 401/403 = permanent auth error → don't retry
                if url_response.status_code in (401, 403):
                    url_response.raise_for_status()
                url_response.raise_for_status()

                url_data = url_response.json()
                media_url = url_data.get("url")
                file_size = url_data.get("file_size")

                if not media_url:
                    raise ValueError(f"Meta returned no URL for media_id={media_id}")

                logger.info(
                    f"📥 [MEDIA] Downloading from Meta | size={file_size} | "
                    f"msg={message_id} | attempt={attempt}/{MAX_RETRIES}"
                )

                # Step 2: Download the binary content
                download_response = await client.get(
                    media_url,
                    headers={"Authorization": f"Bearer {tenant.ws_token}"},
                )
                # 401/403 = permanent → don't retry
                if download_response.status_code in (401, 403):
                    download_response.raise_for_status()
                download_response.raise_for_status()
                file_bytes = download_response.content

                # Download successful — break retry loop
                break

            except httpx.HTTPStatusError as e:
                last_err = e
                # Permanent errors (4xx except 429) → don't retry
                if e.response.status_code < 500 and e.response.status_code != 429:
                    raise
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    logger.warning(
                        f"⚠️ [MEDIA] Attempt {attempt}/{MAX_RETRIES} failed "
                        f"(HTTP {e.response.status_code}), retrying in {wait}s | msg={message_id}"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
            except (httpx.TransportError, httpx.RemoteProtocolError) as e:
                last_err = e
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    logger.warning(
                        f"⚠️ [MEDIA] Attempt {attempt}/{MAX_RETRIES} failed "
                        f"({type(e).__name__}), retrying in {wait}s | msg={message_id}"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise

        if not file_bytes:
            raise RuntimeError(f"Download failed after {MAX_RETRIES} attempts: {repr(last_err)}")

        # Step 3: Determine file extension from MIME type
        MIME_TO_EXT = {
            "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif",
            "application/pdf": "pdf",
            "application/vnd.ms-excel": "xls",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/amr": "amr", "audio/aac": "aac",
            "video/mp4": "mp4", "video/3gpp": "3gp",
        }
        mime_raw = media_metadata.get("mime_type", "")
        mime_clean = mime_raw.split(";")[0].strip()  # "audio/ogg; codecs=opus" → "audio/ogg"
        ext = MIME_TO_EXT.get(mime_clean, "bin")

        # Step 4: Upload to Supabase Storage
        # Path convention: <tenant_id>/<contact_id>/<timestamp>_<media_id_prefix>.<ext>
        timestamp = datetime.now(pytz.utc).strftime("%Y%m%d_%H%M%S")
        storage_path = f"{tenant.id}/{contact_id}/{timestamp}_{media_id[:12]}.{ext}"

        # Using service_role key — bypasses Storage RLS
        # Ref: https://supabase.com/docs/reference/python/storage-from-upload
        await db.storage.from_("whatsapp-media").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_clean},
        )

        # Step 5: Update the message record with storage info
        updated_metadata = {
            **media_metadata,
            "storage_path": storage_path,
            "file_size": file_size or len(file_bytes),
            "download_status": "completed",
        }
        await db.table("messages").update({
            "media_metadata": updated_metadata
        }).eq("id", message_id).execute()

        logger.info(
            f"✅ [MEDIA] Stored: {storage_path} "
            f"({len(file_bytes)} bytes, {mime_clean}) | msg={message_id}"
        )

    except Exception as media_err:
        # 3-CHANNEL OBSERVABILITY (Rule #5)
        logger.error(
            f"❌ [MEDIA] Download/upload failed after {MAX_RETRIES} attempts: {repr(media_err)} | "
            f"media_id={media_id} | msg={message_id} | tenant={tenant.id}"
        )
        sentry_sdk.set_context("media_failure", {
            "media_id": media_id,
            "message_id": message_id,
            "message_type": message_type,
            "tenant_id": str(tenant.id),
            "contact_id": str(contact_id),
            "environment": settings.ENVIRONMENT,
        })
        sentry_sdk.capture_exception(media_err)
        await send_discord_alert(
            title=f"❌ Media Download Failed | Tenant {tenant.id}",
            description=(
                f"**Type:** {message_type}\n"
                f"**Media ID:** {media_id[:20]}...\n"
                f"**Message ID:** {message_id}\n"
                f"**Contact:** {contact_id}\n"
                f"**Retries:** {MAX_RETRIES} exhausted\n"
                f"**Error:** {str(media_err)[:300]}"
            ),
            severity="error", error=media_err,
        )
        # Mark as failed in DB (best-effort)
        try:
            await db.table("messages").update({
                "media_metadata": {
                    **media_metadata,
                    "download_status": "failed",
                    "error": str(media_err)[:200],
                }
            }).eq("id", message_id).execute()
        except Exception as update_err:
            logger.error(f"❌ [MEDIA] Failed to mark download as failed: {repr(update_err)}")
            sentry_sdk.capture_exception(update_err)


class ProcessMessageUseCase:
    
    @staticmethod
    async def execute(payload: dict, tenant: TenantContext, db: AsyncClient):
        logger.info(f"🚀 [ORCH] Start for Tenant={tenant.id}")
        # Tag ALL Sentry events in this execution with tenant context
        sentry_sdk.set_tag("tenant_id", str(tenant.id))
        # Block F2: correlation_id for cross-referencing logs ↔ Sentry events
        try:
            from asgi_correlation_id import correlation_id as cid_ctx
            _cid = cid_ctx.get()
            if _cid:
                sentry_sdk.set_tag("correlation_id", _cid)
                logger.info(f"🔗 [ORCH] correlation_id={_cid}")
        except Exception as cid_err:
            logger.debug(f"[ORCH] correlation_id not available (non-critical): {cid_err}")
        is_simulation = payload.get("is_simulation", False)
        contact_id = None
        
        try:
            # Error points #1-2: Payload parsing — malformed webhook
            try:
                entry = payload["entry"][0]
                changes = entry["changes"][0]["value"]
            except (KeyError, IndexError, TypeError) as parse_err:
                logger.error(f"❌ [ORCH] Malformed webhook payload: {parse_err}")
                sentry_sdk.set_context("malformed_payload", {
                    "payload_keys": list(payload.keys()) if isinstance(payload, dict) else str(type(payload)),
                    "tenant_id": str(tenant.id),
                })
                sentry_sdk.capture_exception(parse_err)
                await send_discord_alert(
                    title=f"❌ Malformed Webhook Payload | Tenant {tenant.id}",
                    description=f"Could not parse entry/changes from payload: {str(parse_err)[:300]}",
                    severity="error", error=parse_err
                )
                return

            if "messages" not in changes:
                logger.info("ℹ️ [ORCH] No messages in payload.")
                return
                
            message = changes["messages"][0]
            patient_phone = message.get("from")

            # ============================================================
            # MEDIA HANDLING: Type detection + metadata extraction
            # Zero-latency: pure JSON parsing of the webhook payload.
            # No network calls. No disk I/O. No blocking.
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components#messages-object
            # ============================================================
            message_type = message.get("type", "text")
            text_body = ""
            media_metadata = None

            if message_type == "text":
                text_body = message.get("text", {}).get("body", "")
            elif message_type in ("image", "document", "audio", "video", "sticker"):
                media_obj = message.get(message_type, {})
                media_metadata = {
                    "media_id": media_obj.get("id"),
                    "mime_type": media_obj.get("mime_type"),
                    "sha256": media_obj.get("sha256"),
                    "caption": media_obj.get("caption"),
                    "filename": media_obj.get("filename"),  # documents only
                    "animated": media_obj.get("animated"),  # stickers only
                    "download_status": "pending",
                    "storage_path": None,
                }
                text_body = media_obj.get("caption", "")
                logger.info(
                    f"📎 [ORCH] Media message: type={message_type}, "
                    f"mime={media_obj.get('mime_type')}, "
                    f"media_id={media_obj.get('id', 'N/A')[:20]}..."
                )
            elif message_type == "location":
                loc = message.get("location", {})
                media_metadata = {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                    "name": loc.get("name"),
                    "address": loc.get("address"),
                }
                text_body = f"📍 Ubicación: {loc.get('name', '')} {loc.get('address', '')}".strip()
            elif message_type == "reaction":
                reaction = message.get("reaction", {})
                media_metadata = {
                    "reacted_message_id": reaction.get("message_id"),
                    "emoji": reaction.get("emoji"),
                }
                text_body = ""  # Reactions don't generate LLM text
                logger.info(f"😊 [ORCH] Reaction: {reaction.get('emoji')}")
            else:
                message_type = "unsupported"
                text_body = ""
                logger.warning(f"⚠️ [ORCH] Unsupported message type: {message.get('type')}")
                sentry_sdk.capture_message(
                    f"Unsupported WhatsApp message type: {message.get('type')} | Tenant {tenant.id}",
                    level="warning"
                )
            
            # ============================================================
            # Step 4: Extract wamid for webhook deduplication
            # Meta WhatsApp Cloud API assigns a unique ID to each inbound
            # message (format: wamid.*). Used to detect duplicate webhook
            # deliveries (Meta retries if initial 200 response was slow).
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
            # ============================================================
            wamid = message.get("id")  # e.g. "wamid.HBgNNTY5..."
            
            # ============================================================
            # Block G2: BSUID Dormant Capture — extract from webhook payload
            # As of April 2026, BSUIDs are present in ALL webhook payloads.
            # Format: CC.alphanumeric (e.g., CL.1A2B3C4D5E6F7890)
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks
            # ⚠️ DORMANT: extracted and stored, but NOT used for contact lookup
            # ============================================================
            raw_bsuid = message.get("user_id")
            bsuid = None
            if raw_bsuid and isinstance(raw_bsuid, str) and re.match(r'^[A-Z]{2}\..+$', raw_bsuid):
                bsuid = raw_bsuid
                logger.info(f"📎 [ORCH] BSUID extracted: {bsuid[:20]}...")
            elif raw_bsuid:
                # user_id present but doesn't match BSUID format — log for investigation
                logger.warning(f"⚠️ [ORCH] Unexpected user_id format: '{str(raw_bsuid)[:50]}'")
                sentry_sdk.set_context("bsuid_unexpected", {
                    "raw_value": str(raw_bsuid)[:100],
                    "tenant_id": str(tenant.id),
                    "patient_phone": patient_phone,
                })
                sentry_sdk.capture_message("Unexpected user_id format in webhook", level="warning")
            
            logger.info(f"📩 [ORCH] Message from {patient_phone}: '{text_body}'")

            if not tenant.is_active:
                logger.warning("⚠️ [ORCH] Tenant deactivated. Ignoring.")
                return

            # Error point #3: Contact lookup DB query
            logger.info("🔍 [ORCH] Looking up contact...")
            try:
                contact_res = await db.table("contacts").select("*").eq("phone_number", patient_phone).eq("tenant_id", tenant.id).execute()
            except Exception as lookup_err:
                logger.error(f"❌ [ORCH] Contact lookup failed: {lookup_err}")
                sentry_sdk.capture_exception(lookup_err)
                await send_discord_alert(
                    title=f"❌ Contact Lookup Failed | Tenant {tenant.id}",
                    description=f"Phone: {patient_phone}\nError: {str(lookup_err)[:300]}",
                    severity="error", error=lookup_err
                )
                return  # Cannot proceed without contact info
            
            bot_active = True
            contact_role = "cliente"
            contact_data = None
            
            if contact_res.data:
                contact_data = contact_res.data[0]
                bot_active = contact_data.get("bot_active", True)
                contact_id = contact_data.get("id")
                contact_role = contact_data.get("role", "cliente")
                is_processing = contact_data.get("is_processing_llm", False)
                logger.info(f"✅ [ORCH] Contact found: {contact_id} | BotActive={bot_active} | Processing={is_processing}")
                
                # ============================================================
                # Block G4: BSUID Backfill — enrich existing contacts
                # If we have a valid BSUID and the contact doesn't have one yet,
                # store it. This is non-blocking — failure doesn't affect flow.
                # ============================================================
                if bsuid and not contact_data.get("bsuid"):
                    try:
                        await db.table("contacts").update({"bsuid": bsuid}).eq("id", contact_id).execute()
                        logger.info(f"📎 [ORCH] BSUID backfilled for contact {contact_id}")
                    except Exception as bf_err:
                        logger.warning(f"⚠️ [ORCH] BSUID backfill failed (non-blocking): {bf_err}")
                        sentry_sdk.capture_exception(bf_err)
                        await send_discord_alert(
                            title=f"⚠️ BSUID Backfill Failed | Tenant {tenant.id}",
                            description=f"Contact: {contact_id}\nBSUID: {bsuid[:20]}...\nError: {str(bf_err)[:300]}",
                            severity="warning", error=bf_err
                        )
            else:
                logger.info("🆕 [ORCH] Creating new contact...")
                is_processing = False
                try:
                    profile_name = changes.get("contacts", [{}])[0].get("profile", {}).get("name", "Lead")
                    # Block G3: Include bsuid in new contact creation (nullable)
                    new_contact = await db.table("contacts").insert({
                        "tenant_id": tenant.id,
                        "phone_number": patient_phone,
                        "name": profile_name,
                        "bot_active": True,
                        "bsuid": bsuid,  # Block G3: dormant capture — NULL if absent/invalid
                    }).execute()
                    if new_contact.data:
                        contact_id = new_contact.data[0]["id"]
                        contact_data = new_contact.data[0]
                        logger.info(f"✅ [ORCH] New contact created: {contact_id}{' with BSUID' if bsuid else ''}")
                except Exception as e:
                    logger.error(f"❌ [ORCH] Failed creating contact: {e}")
                    sentry_sdk.capture_exception(e)
                    await send_discord_alert(title=f"❌ Contact Creation Error | Tenant {tenant.id}", description=str(e), severity="error", error=e)
            
            clinical_keywords = ["dolor", "fibrosis", "sangrado", "emergencia", "urgencia", "infectado"]
            text_body_lower = text_body.lower()  # Only for keyword matching, preserve original casing
            force_escalation = any(kw in text_body_lower for kw in clinical_keywords)
            if force_escalation:
                logger.warning(f"🚨 [ORCH] Clinical keyword detected!")

            # ============================================================
            # STEP 1: Persist inbound message always (Bot or Human)
            # ============================================================
            if contact_id and not is_simulation:
                logger.info("💾 [ORCH] Persisting inbound message...")
                try:
                    insert_data = {
                        "contact_id": contact_id, "tenant_id": tenant.id,
                        "sender_role": "user", "content": text_body,
                        "message_type": message_type,
                        "media_metadata": media_metadata,  # NULL for text messages
                    }
                    # Step 4: Include wamid for dedup — partial UNIQUE index
                    # catches duplicate webhook deliveries at the DB level.
                    if wamid:
                        insert_data["wamid"] = wamid
                    inserted_msg_res = await db.table("messages").insert(insert_data).execute()
                    inserted_msg_id = None
                    if inserted_msg_res.data:
                        inserted_msg_id = inserted_msg_res.data[0].get("id")
                except Exception as e:
                    err_str = str(e)
                    # Step 4: Check if this is a UNIQUE violation on wamid
                    # (duplicate webhook delivery from Meta). If so, skip
                    # processing entirely — this message was already handled.
                    if wamid and ("idx_messages_wamid_unique" in err_str or "duplicate key" in err_str.lower()):
                        logger.warning(
                            f"🔁 [ORCH] Duplicate webhook detected via wamid={wamid[:30]}... "
                            f"Skipping duplicate processing for phone {patient_phone}."
                        )
                        sentry_sdk.capture_message(
                            f"Webhook dedup triggered | wamid={wamid[:30]} | Tenant {tenant.id}",
                            level="info"
                        )
                        return  # Skip — already processed
                    logger.error(f"❌ [ORCH] Msg persistence err: {e}")
                    sentry_sdk.capture_exception(e)
                    await send_discord_alert(title=f"❌ Msg Persistence Error | Tenant {tenant.id}", description=f"Failed to persist inbound message for contact {contact_id}: {str(e)[:300]}", severity="error", error=e)

            # ============================================================
            # MEDIA HANDLING: Fire-and-forget background download + upload
            # This MUST be after persist and before LLM pipeline.
            # Runs as asyncio.create_task — does NOT block LLM response.
            # Stickers excluded (cosmetic, no business value in downloading).
            # ============================================================
            if (contact_id and not is_simulation
                and message_type in ("image", "document", "audio", "video")
                and media_metadata and 'inserted_msg_id' in dir() and inserted_msg_id):
                asyncio.create_task(
                    _download_and_store_media(
                        db, tenant, contact_id, inserted_msg_id, message_type, media_metadata
                    )
                )
                logger.info(f"🚀 [MEDIA] Background download task launched for msg={inserted_msg_id}")

            # ============================================================
            # MEDIA HANDLING: Reactions skip entire LLM pipeline
            # Reactions are emoji responses to existing messages — no customer intent
            # to interpret. We persisted the message above; now return.
            # ============================================================
            if message_type == "reaction":
                logger.info(f"😊 [ORCH] Reaction persisted, skipping LLM pipeline")
                return

            # ============================================================
            # INC-4: Update last_message_at on every processed message
            # This field was stale since contact creation. Critical for
            # activity tracking, stale contact detection, and analytics.
            # Non-fatal: failure here does not block message processing.
            # ============================================================
            if contact_id and not is_simulation:
                try:
                    await db.table("contacts").update({
                        "last_message_at": datetime.now(pytz.utc).isoformat()
                    }).eq("id", contact_id).execute()
                except Exception as lm_err:
                    logger.error(f"❌ [ORCH] Failed to update last_message_at for contact {contact_id}: {lm_err}")
                    sentry_sdk.set_context("last_message_at_update", {
                        "contact_id": str(contact_id),
                        "tenant_id": str(tenant.id),
                        "patient_phone": patient_phone,
                    })
                    sentry_sdk.capture_exception(lm_err)
                    await send_discord_alert(
                        title=f"❌ last_message_at Update Failed | Tenant {tenant.id}",
                        description=f"Contact: {contact_id}\nPhone: {patient_phone}\nError: {str(lm_err)[:300]}",
                        severity="error", error=lm_err
                    )
                    # Non-fatal: continue processing

            # ============================================================
            # STEP 2: Logic routing (Bot Active check)
            # ============================================================
            if not bot_active:
                logger.info("🔇 [ORCH] Bot muted for this contact. Skipping LLM.")
                return

            # ============================================================
            # Block E3: Processing Lock TTL — 90-second stale lock release
            #
            # If is_processing_llm=True but updated_at is older than 90s,
            # the previous pipeline likely crashed without releasing the lock.
            # Force-release it instead of silently dropping the message.
            # ============================================================
            if is_processing and not is_simulation:
                stale_lock = False
                try:
                    updated_at_str = contact_data.get("updated_at") if contact_data else None
                    if updated_at_str:
                        chile_tz_check = pytz.timezone("America/Santiago")
                        if isinstance(updated_at_str, str):
                            # Parse ISO format from Supabase
                            updated_at_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                        else:
                            updated_at_dt = updated_at_str
                        now_utc = datetime.now(pytz.utc)
                        age_seconds = (now_utc - updated_at_dt).total_seconds()
                        if age_seconds > 90:
                            stale_lock = True
                            logger.warning(
                                f"🔓 [ORCH] STALE LOCK detected: contact {contact_id} locked for {age_seconds:.0f}s (>90s). "
                                f"Force-releasing."
                            )
                            sentry_sdk.capture_message(
                                f"Stale processing lock force-released | Contact {contact_id} | Age {age_seconds:.0f}s",
                                level="warning"
                            )
                            await send_discord_alert(
                                title=f"🔓 Stale Lock Force-Released | Tenant {tenant.id}",
                                description=(
                                    f"Contact `{contact_id}` was locked for {age_seconds:.0f}s (>90s limit).\n"
                                    f"Phone: {patient_phone}\n"
                                    f"Previous pipeline likely crashed without cleanup."
                                ),
                                severity="warning"
                            )
                except Exception as ttl_err:
                    logger.error(f"❌ [ORCH] Lock TTL check failed: {ttl_err}")
                    sentry_sdk.capture_exception(ttl_err)
                    # If TTL check fails, treat as NOT stale (conservative)
                
                if not stale_lock:
                    logger.info("⏳ [ORCH] Already processing (lock is fresh). Skipping.")
                    return
                # If stale_lock=True, force-release it so the atomic RPC can re-acquire.
                # Without this, the RPC sees is_processing_llm=true and returns false,
                # dropping the message even though the lock is stale.
                try:
                    await db.table("contacts").update({"is_processing_llm": False}).eq("id", contact_id).execute()
                    logger.info(f"🔓 [ORCH] Stale lock force-released for contact {contact_id}. Proceeding to re-acquire.")
                except Exception as release_err:
                    logger.error(f"❌ [ORCH] Failed to force-release stale lock: {release_err}")
                    sentry_sdk.capture_exception(release_err)
                    return  # Can't release the stale lock — can't proceed safely

            # ============================================================
            # Block E2: Rate Limit Check — before LLM call
            # ============================================================
            try:
                allowed, remaining, reset_secs = await rate_limiter.check_and_increment(
                    str(tenant.id), patient_phone
                )
                if not allowed:
                    logger.warning(f"🚫 [ORCH] Rate limited: {patient_phone} | Resets in {reset_secs}s")
                    # Send polite throttle message directly without LLM
                    throttle_msg = (
                        "Estás enviando muchos mensajes. Por favor espera unos minutos "
                        "antes de escribir de nuevo. ¡Gracias por tu paciencia! 🙏"
                    )
                    if not is_simulation:
                        try:
                            await MetaGraphAPIClient.send_text_message(
                                phone_number_id=tenant.ws_phone_id,
                                to=patient_phone,
                                text=throttle_msg,
                                token=tenant.ws_token or "mock"
                            )
                        except Exception as throttle_send_err:
                            logger.error(f"❌ [ORCH] Failed to send throttle msg: {throttle_send_err}")
                            sentry_sdk.capture_exception(throttle_send_err)
                    return
            except Exception as rate_err:
                logger.error(f"❌ [ORCH] Rate limiter error: {rate_err}")
                sentry_sdk.capture_exception(rate_err)
                await send_discord_alert(
                    title=f"❌ Rate Limiter Error | Tenant {tenant.id}",
                    description=f"Rate limiter check failed. Proceeding without rate limit.\nError: {str(rate_err)[:300]}",
                    severity="error", error=rate_err
                )
                # Non-fatal: proceed without rate limit if the limiter itself fails

            # ============================================================
            # PARALLEL: Acquire processing lock (ATOMIC) + fetch history
            # ============================================================
            # Step 4: Replace non-atomic _set_processing with database-level
            # acquire_processing_lock RPC. This is the ONLY reliable way to
            # prevent double-processing across Cloud Run instances.
            # The RPC does: UPDATE contacts SET is_processing_llm=true
            #   WHERE id=p_contact_id AND is_processing_llm=false
            # If another pipeline already locked, it returns false.
            # ============================================================
            async def _acquire_lock_atomic():
                """Atomically acquire the processing lock via database RPC.
                Returns True if lock acquired, False if already locked."""
                if not contact_id:
                    return True  # No contact = no lock needed (shouldn't happen)
                try:
                    result = await db.rpc(
                        'acquire_processing_lock',
                        {'p_contact_id': str(contact_id)}
                    ).execute()
                    acquired = result.data if isinstance(result.data, bool) else bool(result.data)
                    if not acquired:
                        logger.info(
                            f"🔒 [ORCH] Atomic lock NOT acquired — another pipeline owns it. "
                            f"Contact: {contact_id} | Phone: {patient_phone}"
                        )
                    else:
                        logger.info(f"🔓 [ORCH] Atomic lock ACQUIRED for contact {contact_id}")
                    return acquired
                except Exception as lock_err:
                    logger.error(f"❌ [ORCH] Atomic lock RPC failed: {lock_err}")
                    sentry_sdk.set_context("atomic_lock_failure", {
                        "contact_id": str(contact_id),
                        "tenant_id": str(tenant.id),
                        "patient_phone": patient_phone,
                    })
                    sentry_sdk.capture_exception(lock_err)
                    await send_discord_alert(
                        title=f"❌ Atomic Lock RPC Failed | Tenant {tenant.id}",
                        description=(
                            f"acquire_processing_lock failed for contact {contact_id}.\n"
                            f"Phone: {patient_phone}\n"
                            f"Falling back to non-atomic lock.\n"
                            f"Error: {str(lock_err)[:300]}"
                        ),
                        severity="error", error=lock_err
                    )
                    # Fallback: set lock non-atomically (better than no lock)
                    try:
                        await db.table("contacts").update({"is_processing_llm": True}).eq("id", contact_id).execute()
                    except Exception as fallback_lock_err:
                        logger.error(f"❌ [ORCH] Fallback non-atomic lock ALSO failed: {fallback_lock_err}")
                        sentry_sdk.capture_exception(fallback_lock_err)
                    return True  # Proceed with processing (risk of double, but better than dropping)

            async def _fetch_history():
                history = []
                if contact_id:
                    logger.info("📚 [ORCH] Fetching history...")
                    try:
                        hist_res = await db.table("messages").select("sender_role, content, message_type, media_metadata").eq("contact_id", contact_id).order("timestamp", desc=True).limit(30).execute()
                        if hist_res.data:
                            for m in reversed(hist_res.data):
                                sr = m["sender_role"]
                                if sr == "system_alert":
                                    continue  # System alerts are not part of the conversation
                                elif sr == "human_agent":
                                    # Block I fix (BUG-E): Map human_agent to role:"user" with name field
                                    # Per OpenAI docs: NEVER use role:"assistant" for human participants.
                                    # If the LLM sees staff messages as its own prior output, it gets
                                    # confused about its role and contradicts the human agent.
                                    # Using role:"user" + name:"agente_humano" lets the LLM know
                                    # a human already intervened without confusing its own identity.
                                    # Ref: https://platform.openai.com/docs/guides/text?api-mode=chat
                                    history.append({
                                        "role": "user",
                                        "name": "agente_humano",
                                        "content": f"[Mensaje del equipo]: {m['content']}"
                                    })
                                    continue
                                elif sr == "assistant":
                                    rol = "assistant"
                                else:
                                    rol = "user"
                                # MEDIA HANDLING: Rebuild descriptive text for past media messages
                                # so the LLM sees "[El usuario envió una imagen]" instead of empty string
                                msg_content = m["content"]
                                if rol == "user" and m.get("message_type") and m["message_type"] != "text":
                                    msg_content = _build_llm_content_for_media(
                                        m["content"], m["message_type"], m.get("media_metadata")
                                    )
                                history.append({"role": rol, "content": msg_content})
                    except Exception as hist_err:
                        logger.error(f"❌ [ORCH] Failed to fetch history: {hist_err}")
                        sentry_sdk.capture_exception(hist_err)
                        await send_discord_alert(
                            title=f"❌ History Fetch Failed | Tenant {tenant.id}",
                            description=f"Contact: {contact_id}\nError: {str(hist_err)[:300]}",
                            severity="error", error=hist_err
                        )
                        # Non-fatal: continue with empty history
                return history

            # Run concurrently: atomic lock + history fetch
            lock_acquired, history = await asyncio.gather(
                _acquire_lock_atomic(),
                _fetch_history()
            )

            # Step 4: If lock was NOT acquired, another pipeline is processing.
            # Skip to avoid double-processing. The wamid dedup above catches
            # Meta retries; this catches rapid sequential user messages.
            if not lock_acquired and not is_simulation:
                logger.info(
                    f"⏳ [ORCH] Lock not acquired (another pipeline active). "
                    f"Skipping for contact {contact_id} | Phone {patient_phone}"
                )
                return

            # ============================================================
            # RAPID-FIRE MESSAGE BATCHING
            # When humans send multiple WhatsApp messages quickly (e.g.
            # "Y" + "Nada" + "Lo extraño"), each triggers a separate
            # webhook. Messages 2+ are PERSISTED to DB (line ~216) but
            # their pipelines exit at the lock check (line ~467).
            # 
            # The 3-second sleep gives time for rapid-fire messages to
            # accumulate in the DB. After sleeping, we RE-FETCH history
            # to capture ALL messages, not just the first one.
            # Without this, the LLM only sees message 1 and the rest
            # are silently dropped from the conversation context.
            # ============================================================
            if not is_simulation:
                await asyncio.sleep(1.5)  # Sprint 2: reduced from 3s → 1.5s for faster responses

            chile_tz = pytz.timezone("America/Santiago")
            current_time_str = datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M")

            # Re-fetch history AFTER sleep to capture rapid-fire messages
            # that were persisted to DB by other (lock-blocked) pipelines.
            try:
                fresh_history = await _fetch_history()
                msgs_before = len(history)
                msgs_after = len(fresh_history)
                if msgs_after > msgs_before:
                    logger.info(
                        f"📨 [ORCH] Rapid-fire batch captured: {msgs_after - msgs_before} new message(s) "
                        f"arrived during sleep window for contact {contact_id}"
                    )
                    sentry_sdk.set_context("rapid_fire_batch", {
                        "contact_id": str(contact_id),
                        "tenant_id": str(tenant.id),
                        "msgs_before_sleep": msgs_before,
                        "msgs_after_sleep": msgs_after,
                        "new_messages": msgs_after - msgs_before,
                    })
                history = fresh_history
            except Exception as refetch_err:
                logger.error(f"❌ [ORCH] History re-fetch after sleep failed: {refetch_err}")
                sentry_sdk.capture_exception(refetch_err)
                await send_discord_alert(
                    title=f"❌ History Re-fetch Failed | Tenant {tenant.id}",
                    description=(
                        f"Post-sleep history re-fetch failed for contact {contact_id}.\n"
                        f"Falling back to pre-sleep history ({len(history)} messages).\n"
                        f"Error: {str(refetch_err)[:300]}"
                    ),
                    severity="error", error=refetch_err
                )
                # Non-fatal: continue with the original (stale) history

            # Append current message only if not already in re-fetched history
            # MEDIA HANDLING: Use descriptive text for LLM instead of raw empty string
            llm_content = _build_llm_content_for_media(text_body, message_type, media_metadata)
            if not history or history[-1].get("content", "").lower() != (llm_content or "").lower():
                history.append({"role": "user", "content": llm_content})

            # Error points #9-10: LLM strategy creation + schema fetch
            import time as _time_mod
            _pipeline_llm_start = _time_mod.monotonic()
            logger.info(
                f"🧠 [ORCH] Calling LLM (Provider={tenant.llm_provider} | "
                f"Adapter={type(llm_strategy).__name__ if 'llm_strategy' in dir() else 'pending'})..."
            )
            try:
                llm_strategy = LLMFactory.create(tenant_context=tenant)
            except Exception as factory_err:
                logger.error(f"❌ [ORCH] LLMFactory.create failed: {factory_err}")
                sentry_sdk.set_context("llm_factory_error", {
                    "provider": tenant.llm_provider,
                    "model": tenant.llm_model,
                    "tenant_id": str(tenant.id),
                })
                sentry_sdk.capture_exception(factory_err)
                await send_discord_alert(
                    title=f"💥 LLM Factory Failed | Tenant {tenant.id}",
                    description=f"Provider: {tenant.llm_provider}\nModel: {tenant.llm_model}\nError: {str(factory_err)[:300]}",
                    severity="error", error=factory_err
                )
                raise  # Fatal — cannot proceed without LLM

            try:
                tools_schema = tool_registry.get_all_schemas(provider=tenant.llm_provider.lower())
            except Exception as schema_err:
                logger.error(f"❌ [ORCH] Tool schema fetch failed: {schema_err}")
                sentry_sdk.capture_exception(schema_err)
                await send_discord_alert(
                    title=f"💥 Tool Schema Fetch Failed | Tenant {tenant.id}",
                    description=f"Provider: {tenant.llm_provider}\nError: {str(schema_err)[:300]}",
                    severity="error", error=schema_err
                )
                tools_schema = []  # Non-fatal: proceed without tools
            
            # ============================================================
            # BUG-1 Layer 1: Inject INTERNAL_TOOL_RULES between tenant
            # prompt and [CONTEXTO]. These are system-level safety rules
            # the tenant cannot edit or accidentally delete.
            # ============================================================

            # ============================================================
            # Service Catalog Injection — fetched fresh from DB per-message
            # This makes service changes "real-time" without Supabase Realtime.
            # Every incoming WhatsApp message triggers handle_incoming() which
            # calls this code, so updated prices/durations take effect immediately.
            # ============================================================
            services_block = ""
            try:
                services_res = await db.table("tenant_services") \
                    .select("name, description, price, price_is_variable, duration_minutes") \
                    .eq("tenant_id", str(tenant.id)) \
                    .eq("is_active", True) \
                    .order("sort_order") \
                    .execute()

                if services_res.data and len(services_res.data) > 0:
                    lines = ["[CATÁLOGO DE SERVICIOS]"]
                    for svc in services_res.data:
                        parts = [f"- {svc['name']}"]
                        if svc.get("description"):
                            parts.append(f"  ({svc['description'][:80]})")
                        if svc.get("price") is not None:
                            prefix = "Desde " if svc.get("price_is_variable") else ""
                            parts.append(f"  — {prefix}${svc['price']:,}".replace(",", "."))
                        if svc.get("duration_minutes"):
                            parts.append(f"  — {svc['duration_minutes']} min")
                        lines.append("".join(parts))

                    raw_catalog = "\n".join(lines)
                    # Truncation safety: prevent prompt overflow
                    if len(raw_catalog) > 2000:
                        services_block = raw_catalog[:1980] + "\n... (catálogo truncado)"
                        _trunc_msg = (
                            f"[ProcessMsgUC] Service catalog truncated: {len(raw_catalog)} chars > 2000 | "
                            f"tenant={tenant.id} | services={len(services_res.data)} | env={settings.ENVIRONMENT}"
                        )
                        logger.warning(_trunc_msg)
                        sentry_sdk.capture_message(_trunc_msg, level="warning")
                        await send_discord_alert(
                            title=f"⚠️ Service Catalog Truncated | Tenant {tenant.id}",
                            description=(
                                f"**Where:** `ProcessMsgUC.prompt_assembly`\n"
                                f"**What:** Catalog has {len(raw_catalog)} chars (max 2000)\n"
                                f"**Services count:** {len(services_res.data)}\n"
                                f"**Env:** {settings.ENVIRONMENT}"
                            ),
                            severity="warning",
                        )
                    else:
                        services_block = raw_catalog
                    logger.debug(f"[ProcessMsgUC] Injected {len(services_res.data)} services into prompt | tenant={tenant.id}")
            except Exception as svc_err:
                # Graceful degradation: if catalog fetch fails, proceed without it
                _svc_msg = (
                    f"[ProcessMsgUC] Service catalog fetch FAILED (non-fatal) | "
                    f"tenant={tenant.id} | env={settings.ENVIRONMENT} | error={str(svc_err)[:200]}"
                )
                logger.error(_svc_msg, exc_info=True)
                sentry_sdk.capture_exception(svc_err)
                await send_discord_alert(
                    title=f"❌ Service Catalog Fetch Failed | Tenant {tenant.id}",
                    description=(
                        f"**Where:** `ProcessMsgUC.prompt_assembly`\n"
                        f"**What:** tenant_services query failed — LLM proceeds WITHOUT catalog\n"
                        f"**Tenant:** `{tenant.id}`\n"
                        f"**Env:** {settings.ENVIRONMENT}\n"
                        f"**Error:** ```{str(svc_err)[:300]}```"
                    ),
                    severity="error", error=svc_err,
                )

            # Assemble final prompt: tenant prompt + tool rules + catalog + context
            catalog_section = f"\n\n{services_block}" if services_block else ""
            system_prompt = f"{tenant.system_prompt}\n\n{INTERNAL_TOOL_RULES}{catalog_section}\n\n[CONTEXTO]\nPaciente: {contact_data.get('name', 'Lead') if contact_data else 'Lead'}\nTeléfono: {patient_phone}\nRol: {contact_role}\nHora: {current_time_str}\n"
            if force_escalation:
                system_prompt += "\n⚠️ RIESGO: Avisa amablemente que derivas a humano y usa 'request_human_escalation'."

            # ============================================================
            # BUG-1 Layer 3: Conditional tool_choice override
            # When force_escalation=True, force the LLM to call the
            # escalation tool instead of just talking about it.
            # Per OpenAI docs: {"type": "function", "function": {"name": X}}
            # Ref: https://platform.openai.com/docs/guides/function-calling
            # ============================================================
            tool_choice_override = None
            if force_escalation and tools_schema:
                tool_choice_override = {"type": "function", "function": {"name": "request_human_escalation"}}
                logger.info("🔒 [ORCH] force_escalation=True → tool_choice forced to 'request_human_escalation'")

            # ============================================================
            # BLOCK D: Multi-Turn Agentic Loop (2026-04-11)
            # 
            # Protocol: OpenAI Function Calling multi-turn conversation
            # Ref: https://platform.openai.com/docs/guides/function-calling
            #
            # Flow per round:
            #   1. LLM returns assistant message (text and/or tool_calls)
            #   2. If tool_calls: append assistant msg to history, execute
            #      tools, append role:"tool" with matching tool_call_id
            #   3. Loop back to LLM with updated history
            #   4. If no tool_calls: extract reply text and break
            #
            # Safety:
            #   - MAX_TOOL_ROUNDS caps tool execution rounds (prevents infinite loops)
            #   - Every tool_call MUST get a role:"tool" response (API breaks otherwise)
            #   - parallel_tool_calls=False (Block B) → exactly 1 tool per LLM turn
            #   - tool_choice_override only applies to round 0 (force_escalation)
            #
            # Observability (§6): 10 failure points, all instrumented.
            # ============================================================
            MAX_TOOL_ROUNDS = 3
            reply_text = ""
            total_prompt_tokens = 0
            total_completion_tokens = 0
            rounds_executed = 0
            ack_sent = False  # Pre-tool ACK: send exactly one acknowledgment per pipeline run
            ack_text_for_shadow = ""  # Captured ACK text for shadow forward

            # ── ACK Templates ──
            # Tool-specific acknowledgment messages sent BEFORE tool execution
            # to eliminate perceived dead-air for the customer.
            # Tools that execute in <2s (escalation, scoring) are excluded.
            _ACK_TEMPLATES = {
                "book_round_robin": "Perfecto, estoy verificando disponibilidad para agendar tu cita 📅...",
                "get_merged_availability": "Dame un momento, estoy revisando los horarios disponibles 📋...",
                "delete_appointment": "Un momento, estoy procesando la cancelación ❌...",
                "modify_appointment": "Un momento, estoy modificando tu cita 📝...",
                "move_appointment": "Un momento, estoy buscando el mejor horario para reagendar 🔄...",
            }
            _ACK_DEFAULT = "Dame un momento, estoy procesando tu solicitud ⏳..."
            # Tools that are fast enough to NOT need an ACK
            _ACK_SKIP_TOOLS = {"request_human_escalation", "update_patient_scoring"}

            for round_num in range(MAX_TOOL_ROUNDS + 1):  # +1 allows a final text-only response
                # Determine tools availability — strip tools on final safety round
                round_tools = tools_schema if round_num < MAX_TOOL_ROUNDS else None
                # tool_choice_override only applies on round 0 (e.g. force_escalation)
                round_tool_choice = tool_choice_override if round_num == 0 else None

                try:
                    response_dto = await llm_strategy.generate_response(
                        system_prompt=system_prompt,
                        message_history=history,
                        tools=round_tools,
                        tool_choice_override=round_tool_choice
                    )
                except Exception as llm_err:
                    # Error point #1: LLM API call fails (429, 500, timeout, etc.)
                    # The adapter already has Sentry+Discord instrumentation and re-raises.
                    # We catch here to provide a graceful fallback reply.
                    logger.error(f"💥 [ORCH] LLM call failed on round {round_num+1}: {llm_err}")
                    sentry_sdk.set_context("agentic_loop", {
                        "round": round_num + 1,
                        "max_rounds": MAX_TOOL_ROUNDS,
                        "tenant_id": str(tenant.id),
                        "patient_phone": patient_phone,
                    })
                    sentry_sdk.capture_exception(llm_err)
                    await send_discord_alert(
                        title=f"💥 LLM Call Failed in Loop | Round {round_num+1} | Tenant {tenant.id}",
                        description=f"Phone: {patient_phone}\nError: {str(llm_err)[:300]}",
                        severity="error", error=llm_err
                    )
                    reply_text = "Disculpa, tuve un inconveniente técnico. ¿Podrías intentar de nuevo en un momento?"
                    break

                rounds_executed = round_num + 1

                # Accumulate usage tracking (C2)
                total_prompt_tokens += response_dto.prompt_tokens or 0
                total_completion_tokens += response_dto.completion_tokens or 0

                _round_elapsed = _time_mod.monotonic() - _pipeline_llm_start
                logger.info(
                    f"✅ [ORCH] Round {rounds_executed}/{MAX_TOOL_ROUNDS} — "
                    f"ToolCalls={response_dto.has_tool_calls} | "
                    f"Elapsed={_round_elapsed:.1f}s | "
                    f"Tokens(in={response_dto.prompt_tokens or 0},out={response_dto.completion_tokens or 0}"
                    f",reasoning={getattr(response_dto, 'reasoning_tokens', 0) or 0}) | "
                    f"ContentPreview='{(response_dto.content or '')[:120]}'"
                )

                # ── No tool calls → final text response, we're done ──
                if not response_dto.has_tool_calls:
                    reply_text = response_dto.content or ""
                    break

                # ── TRUNCATION CIRCUIT BREAKER (Block I, BUG-A/BUG-D) ──
                # If the response was truncated (finish_reason="length") AND has
                # tool_calls, the JSON arguments are likely CORRUPT (cut off mid-string).
                # Executing corrupt tool_calls creates a doom loop:
                #   truncated JSON → parse error → error response to LLM →
                #   LLM retries same tool → same truncation → repeat until MAX_TOOL_ROUNDS
                #
                # Fix: treat truncated tool_calls as if no tools were called.
                # Use whatever text content the model DID produce as the reply.
                # Ref: https://platform.openai.com/docs/api-reference/chat/object
                if response_dto.was_truncated and response_dto.has_tool_calls:
                    logger.warning(
                        f"⚠️ [ORCH] TRUNCATION CIRCUIT BREAKER TRIGGERED | Round {rounds_executed} | "
                        f"Tenant {tenant.id} | Phone {patient_phone} | "
                        f"Tool calls DISCARDED (JSON likely corrupt)"
                    )
                    sentry_sdk.set_context("truncation_circuit_breaker", {
                        "round": rounds_executed,
                        "tenant_id": str(tenant.id),
                        "patient_phone": patient_phone,
                        "discarded_tool_names": [tc["name"] for tc in response_dto.tool_calls],
                        "content_preview": (response_dto.content or "")[:200],
                    })
                    sentry_sdk.capture_message(
                        f"Truncation circuit breaker triggered | Tenant {tenant.id} | Round {rounds_executed}",
                        level="warning"
                    )
                    await send_discord_alert(
                        title=f"⚠️ Truncation Circuit Breaker | Tenant {tenant.id}",
                        description=(
                            f"Round {rounds_executed}: tool_calls DISCARDED due to truncation.\n"
                            f"Discarded tools: {[tc['name'] for tc in response_dto.tool_calls]}\n"
                            f"Using text content as reply instead.\n"
                            f"Phone: {patient_phone}"
                        ),
                        severity="warning"
                    )
                    # Use whatever partial text the model produced
                    reply_text = response_dto.content or "Disculpa, tuve un inconveniente técnico. ¿Podrías intentar de nuevo?"
                    break

                # ── Tool calls present → execute and loop ──

                # STEP 1: Append the assistant's tool_call message to history
                # Per OpenAI docs: the assistant message with tool_calls MUST
                # be in history before the role:"tool" responses.
                assistant_tool_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"] if isinstance(tc["arguments"], str) else json.dumps(tc["arguments"])
                            }
                        }
                        for tc in response_dto.tool_calls
                    ]
                }
                # C1: Preserve any content the assistant sent alongside tool_calls
                if response_dto.content:
                    assistant_tool_msg["content"] = response_dto.content
                history.append(assistant_tool_msg)

                # ============================================================
                # PRE-TOOL ACK: Send immediate acknowledgment to customer
                # 
                # Why: Tool execution + LLM follow-up takes 15-130s.
                #      Customer sees silence → frustration → repeat messages.
                #      ACK gives instant feedback: "your request was understood."
                #
                # Rules:
                #   1. Sent ONCE per pipeline (ack_sent flag)
                #   2. LLM content (if any) takes priority over template
                #   3. Fast tools (escalation, scoring) are skipped
                #   4. Non-blocking: failure never stops tool execution
                #   5. Persisted to messages table for CRM audit trail
                #
                # Ref: Meta API pair-rate-limit is per-user behavioral;
                #      2 msgs per turn (ACK + final) is well within safe range.
                # ============================================================
                if not ack_sent and not is_simulation:
                    first_tool_name = response_dto.tool_calls[0]["name"] if response_dto.tool_calls else "unknown"
                    # Skip ACK for fast tools that don't need it
                    if first_tool_name not in _ACK_SKIP_TOOLS:
                        # Priority: LLM's own content > tool-specific template > default
                        ack_text = (
                            response_dto.content.strip()
                            if response_dto.content and response_dto.content.strip()
                            else _ACK_TEMPLATES.get(first_tool_name, _ACK_DEFAULT)
                        )
                        try:
                            logger.info(
                                f"📨 [ORCH] Sending pre-tool ACK | tool={first_tool_name} | "
                                f"source={'llm_content' if response_dto.content and response_dto.content.strip() else 'template'} | "
                                f"len={len(ack_text)} | tenant={tenant.id}"
                            )
                            sentry_sdk.add_breadcrumb(
                                category="ack",
                                message=f"Pre-tool ACK for {first_tool_name}",
                                data={"tool": first_tool_name, "ack_len": len(ack_text), "source": "llm" if response_dto.content else "template"},
                                level="info",
                            )
                            # Send ACK to customer via Meta API
                            await MetaGraphAPIClient.send_text_message(
                                phone_number_id=tenant.ws_phone_id,
                                to=patient_phone,
                                text=ack_text,
                                token=tenant.ws_token or "mock"
                            )
                            ack_sent = True
                            ack_text_for_shadow = ack_text  # Capture for shadow forward
                            logger.info(f"✅ [ORCH] ACK delivered to {patient_phone}")

                            # Persist ACK to messages table for CRM audit trail
                            if contact_id:
                                try:
                                    await db.table("messages").insert({
                                        "contact_id": contact_id,
                                        "tenant_id": tenant.id,
                                        "sender_role": "assistant",
                                        "content": ack_text,
                                    }).execute()
                                    logger.debug(f"💾 [ORCH] ACK persisted for contact {contact_id}")
                                except Exception as ack_persist_err:
                                    # Non-blocking: ACK was sent to customer, persistence is best-effort
                                    _persist_msg = (
                                        f"[ORCH] ACK persistence failed (non-blocking) | "
                                        f"tenant={tenant.id} | contact={contact_id} | "
                                        f"phone={patient_phone} | tool={first_tool_name} | "
                                        f"env={settings.ENVIRONMENT} | error={repr(ack_persist_err)}"
                                    )
                                    logger.error(_persist_msg, exc_info=True)
                                    sentry_sdk.set_context("ack_persist_failure", {
                                        "tenant_id": str(tenant.id),
                                        "contact_id": str(contact_id),
                                        "patient_phone": patient_phone,
                                        "tool_name": first_tool_name,
                                        "ack_text_preview": ack_text[:100],
                                        "environment": settings.ENVIRONMENT,
                                    })
                                    sentry_sdk.capture_exception(ack_persist_err)
                                    await send_discord_alert(
                                        title=f"⚠️ ACK Persist Failed | Tenant {tenant.id}",
                                        description=(
                                            f"**Where:** `ProcessMsgUC.ack_persist`\n"
                                            f"**What:** ACK sent to customer but DB persist failed\n"
                                            f"**Contact:** `{contact_id}`\n"
                                            f"**Phone:** {patient_phone}\n"
                                            f"**Tool:** {first_tool_name}\n"
                                            f"**Env:** {settings.ENVIRONMENT}\n"
                                            f"**Error:** ```{repr(ack_persist_err)[:300]}```"
                                        ),
                                        severity="warning", error=ack_persist_err
                                    )
                        except Exception as ack_send_err:
                            # NON-BLOCKING: ACK failure must NEVER prevent tool execution
                            _ack_err_msg = (
                                f"[ORCH] ACK send FAILED (non-blocking) | "
                                f"tenant={tenant.id} | contact={contact_id} | "
                                f"phone={patient_phone} | tool={first_tool_name} | "
                                f"env={settings.ENVIRONMENT} | error={repr(ack_send_err)}"
                            )
                            logger.error(_ack_err_msg, exc_info=True)
                            sentry_sdk.set_context("ack_send_failure", {
                                "tenant_id": str(tenant.id),
                                "contact_id": str(contact_id),
                                "patient_phone": patient_phone,
                                "tool_name": first_tool_name,
                                "ack_text_preview": ack_text[:100],
                                "environment": settings.ENVIRONMENT,
                            })
                            sentry_sdk.capture_exception(ack_send_err)
                            await send_discord_alert(
                                title=f"⚠️ ACK Send Failed | Tenant {tenant.id}",
                                description=(
                                    f"**Where:** `ProcessMsgUC.ack_send`\n"
                                    f"**What:** Pre-tool acknowledgment failed (non-blocking)\n"
                                    f"**Contact:** `{contact_id}`\n"
                                    f"**Phone:** {patient_phone}\n"
                                    f"**Tool:** {first_tool_name}\n"
                                    f"**Env:** {settings.ENVIRONMENT}\n"
                                    f"**Error:** ```{repr(ack_send_err)[:300]}```"
                                ),
                                severity="warning", error=ack_send_err
                            )
                            # ack_sent remains False — no state corruption

                # STEP 2: Execute each tool and append role:"tool" response
                has_crash = False
                has_business_error = False

                for tc in response_dto.tool_calls:
                    tool_name = tc["name"]
                    tool_call_id = tc.get("id")

                    # Error point #9: tool_call_id missing (should be impossible but guard)
                    if not tool_call_id:
                        logger.error(f"❌ [ORCH] tool_call_id missing for tool '{tool_name}' — generating fallback ID")
                        sentry_sdk.capture_message(
                            f"tool_call_id missing for '{tool_name}' | Tenant {tenant.id}",
                            level="error"
                        )
                        await send_discord_alert(
                            title=f"❌ Missing tool_call_id: {tool_name} | Tenant {tenant.id}",
                            description=f"OpenAI response had no tool_call_id. Generated fallback. Phone: {patient_phone}",
                            severity="error"
                        )
                        tool_call_id = f"fallback_{tool_name}_{round_num}"

                    logger.info(f"🛠️ [ORCH] Round {rounds_executed}/{MAX_TOOL_ROUNDS} — executing: {tool_name} (call_id={tool_call_id[:20]}...)")

                    # Parse arguments
                    try:
                        # Error point #5: json.loads fails (should be impossible with strict:true)
                        args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                    except (json.JSONDecodeError, TypeError) as parse_err:
                        logger.error(f"❌ [ORCH] Failed to parse tool arguments for '{tool_name}': {parse_err}")
                        sentry_sdk.set_context("argument_parse_error", {
                            "tool_name": tool_name,
                            "raw_arguments": str(tc.get("arguments", ""))[:500],
                            "tenant_id": str(tenant.id),
                        })
                        sentry_sdk.capture_exception(parse_err)
                        await send_discord_alert(
                            title=f"❌ Tool Arg Parse Error: {tool_name} | Tenant {tenant.id}",
                            description=f"Failed to parse arguments: {str(parse_err)[:200]}\nRaw: {str(tc.get('arguments', ''))[:200]}",
                            severity="error", error=parse_err
                        )
                        result_str = json.dumps({
                            "status": "error",
                            "message": f"EXCEPTION: Failed to parse arguments for {tool_name}: {str(parse_err)}"
                        })
                        has_crash = True
                        # CRITICAL: Always append role:"tool" even on parse failure
                        history.append({
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_str
                        })
                        continue

                    # Inject runtime context that tools need but aren't in schema
                    args.update({
                        "tenant_context": tenant,
                        "patient_phone": patient_phone,
                        "caller_phone": patient_phone,
                        "caller_role": contact_role
                    })

                    try:
                        # Error point #2+3: Tool not found or execution crash
                        # Both are handled inside tool_registry.execute_tool with Sentry+Discord
                        result_str = await tool_registry.execute_tool(tool_name, **args)
                        logger.info(f"✅ [ORCH] Tool '{tool_name}' result: {str(result_str)[:300]}")

                        # ============================================================
                        # BUG-3: Detect tool-level status:error responses
                        # These are NOT Python exceptions — the tool ran but returned
                        # an error (e.g. "no appointment found", GCal 403).
                        # ALWAYS report to Sentry + Discord for observability.
                        # ============================================================
                        if '"status": "error"' in result_str or '"status":"error"' in result_str:
                            has_business_error = True
                            logger.warning(f"⚠️ [ORCH] Tool '{tool_name}' returned status:error — alerting Sentry/Discord")
                            sentry_sdk.set_context("tool_error", {
                                "tool_name": tool_name,
                                "result": result_str[:500],
                                "tenant_id": str(tenant.id),
                                "patient_phone": patient_phone,
                                "contact_role": contact_role,
                                "round": rounds_executed,
                            })
                            sentry_sdk.capture_message(
                                f"Tool '{tool_name}' returned error | Tenant {tenant.id}",
                                level="warning"
                            )
                            await send_discord_alert(
                                title=f"⚠️ Tool Error: {tool_name} | Tenant {tenant.id}",
                                description=f"Tool returned error status.\nPhone: {patient_phone}\nRole: {contact_role}\nRound: {rounds_executed}\nResult: {result_str[:300]}",
                                severity="warning"
                            )

                    except Exception as tool_exec_err:
                        # Error point #3: Tool execution crashes (Python exception)
                        # tool_registry already captures to Sentry+Discord, but we
                        # also need to set the error result for the role:"tool" message
                        logger.error(f"💥 [ORCH] Tool '{tool_name}' crashed: {tool_exec_err}")
                        result_str = json.dumps({
                            "status": "error",
                            "message": f"EXCEPTION: Tool {tool_name} crashed: {str(tool_exec_err)}"
                        })
                        has_crash = True
                        sentry_sdk.capture_exception(tool_exec_err)
                        await send_discord_alert(
                            title=f"💥 Tool Crash: {tool_name} | Tenant {tenant.id}",
                            description=f"Round: {rounds_executed}\nPhone: {patient_phone}\nError: {str(tool_exec_err)[:300]}",
                            severity="error", error=tool_exec_err
                        )

                    # STEP 3: ALWAYS append role:"tool" with matching tool_call_id
                    # CRITICAL: OpenAI API breaks if any tool_call doesn't get a response.
                    # This MUST happen whether the tool succeeded, returned error, or crashed.
                    history.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str
                    })

                # STEP 4: Inject system instructions for error cases
                # These guide the LLM's synthesis of tool results
                if has_crash:
                    logger.warning(f"⚠️ [ORCH] Tool CRASHED in round {rounds_executed} — injecting human-escalation instruction")
                    history.append({
                        "role": "user",
                        "content": "[INSTRUCCIÓN SISTEMA]: Uno o más herramientas tuvieron un FALLO TÉCNICO. "
                                   "Informa al paciente amablemente que hubo un inconveniente técnico al procesar su solicitud, "
                                   "que ya se notificó a un miembro del equipo humano para que intervenga en la conversación, "
                                   "y que el equipo técnico fue alertado del problema. "
                                   "Tranquiliza al paciente y continúa la conversación normalmente para ayudar en lo que puedas. "
                                   "NO digas que la acción se realizó correctamente."
                    })
                elif has_business_error:
                    logger.info(f"ℹ️ [ORCH] Tool returned business-level error in round {rounds_executed} — LLM will relay naturally")
                    history.append({
                        "role": "user",
                        "content": "[INSTRUCCIÓN SISTEMA]: Los resultados anteriores contienen respuestas de error del sistema. "
                                   "Transmite la información al paciente de forma natural y amable, usando el mensaje de error como contexto. "
                                   "NO digas que la acción se realizó correctamente si el resultado indica que no se pudo completar. "
                                   "Continúa la conversación normalmente."
                    })

                # Loop continues → next iteration calls LLM with updated history
                # (the LLM will see the tool results and either respond with text or call another tool)

            else:
                # Error point #6: for/else — MAX_TOOL_ROUNDS exhausted (loop never broke)
                logger.warning(f"⚠️ [ORCH] MAX_TOOL_ROUNDS ({MAX_TOOL_ROUNDS}) exhausted for tenant {tenant.id}")
                sentry_sdk.set_context("max_rounds_exhausted", {
                    "tenant_id": str(tenant.id),
                    "patient_phone": patient_phone,
                    "rounds_executed": rounds_executed,
                    "max_rounds": MAX_TOOL_ROUNDS,
                })
                sentry_sdk.capture_message(
                    f"Max tool rounds exhausted ({MAX_TOOL_ROUNDS}) | Tenant {tenant.id}",
                    level="warning"
                )
                await send_discord_alert(
                    title=f"⚠️ Max Tool Rounds | Tenant {tenant.id}",
                    description=f"LLM kept calling tools for {MAX_TOOL_ROUNDS} rounds without producing a final response.\nPhone: {patient_phone}",
                    severity="warning"
                )
                if not reply_text:
                    reply_text = "Disculpa, tuve un inconveniente procesando tu solicitud. ¿Podrías intentar de nuevo?"

            # Log accumulated usage across all rounds
            logger.info(
                f"📊 [ORCH] Pipeline usage — rounds={rounds_executed} "
                f"total_prompt={total_prompt_tokens} total_completion={total_completion_tokens}"
            )

            if not reply_text: reply_text = "Lo siento, tuve un problema. ¿En qué te ayudo?"

            logger.info(f"📤 [ORCH] Final Reply: '{reply_text[:80]}...'")

            # ============================================================
            # PARALLEL: Persist assistant reply + send via Meta API + unset processing
            # ============================================================
            # Error points #17-20: Post-loop parallel operations
            # ============================================================
            # TENACITY RETRY POLICY (INC-7, April 18 2026)
            # Transient httpx.ConnectError / ConnectTimeout caused cascading
            # failures — appointment modified but user never received reply.
            # Fix: 3 attempts, exponential backoff 1s→2s→4s, only on
            # transient network errors. Non-network errors fail immediately.
            # Ref: https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages
            #      → "Implement Exponential Backoff"
            # Ref: https://www.python-httpx.org/ → retry on ConnectError
            # ============================================================
            _RETRY_POLICY = dict(
                retry=retry_if_exception_type((httpx.ConnectError, httpx.ConnectTimeout)),
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=1, max=8),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )

            async def _persist_reply():
                if contact_id:
                    try:
                        @retry(**_RETRY_POLICY)
                        async def _do_persist():
                            await db.table("messages").insert({"contact_id": contact_id, "tenant_id": tenant.id, "sender_role": "assistant", "content": reply_text}).execute()
                        await _do_persist()
                    except Exception as persist_err:
                        logger.error(f"❌ [ORCH] Failed to persist reply after retries: {repr(persist_err)}")
                        sentry_sdk.capture_exception(persist_err)
                        await send_discord_alert(
                            title=f"❌ Reply Persistence Failed | Tenant {tenant.id}",
                            description=f"Contact: {contact_id}\nReply: {reply_text[:200]}\nError: {repr(persist_err)[:200]}",
                            severity="error", error=persist_err
                        )

            async def _send_meta():
                if not is_simulation:
                    try:
                        @retry(**_RETRY_POLICY)
                        async def _do_send():
                            logger.info("📲 [ORCH] Sending via Meta API...")
                            await MetaGraphAPIClient.send_text_message(phone_number_id=tenant.ws_phone_id, to=patient_phone, text=reply_text, token=tenant.ws_token or "mock")
                        await _do_send()
                    except Exception as meta_err:
                        logger.error(f"❌ [ORCH] Meta API send failed after retries: {repr(meta_err)}")
                        sentry_sdk.capture_exception(meta_err)
                        await send_discord_alert(
                            title=f"💥 Meta API Send Failed | Tenant {tenant.id}",
                            description=f"Phone: {patient_phone}\nReply: {reply_text[:200]}\nError: {repr(meta_err)[:200]}",
                            severity="error", error=meta_err
                        )

            # NOTE: _unset_processing() REMOVED from here (INC-3, April 12 2026)
            # Lock release now happens in the `finally` block at the end of the
            # pipeline, with retry logic (INC-5). This guarantees execution even
            # when asyncio.gather fails due to network death cascades.

            # ============================================================
            # Block E4: Shadow-forward conversation to admin WhatsApp
            # Sends BOTH user message + bot response to admin number
            # Uses tenant's own WABA phone (dynamic per tenant, no hardcoded numbers)
            # NOTE: SHADOW_FORWARD_PHONE is the only fixed part (admin's receiving number)
            # TODO: When multi-WABA is implemented (Sprint 3-4), this still works because
            #       it uses tenant.ws_phone_id which is already per-tenant.
            # ============================================================
            async def _shadow_forward():
                shadow_phone = settings.SHADOW_FORWARD_PHONE
                if not shadow_phone or is_simulation:
                    return
                try:
                    tenant_name = tenant.name or str(tenant.id)[:8]
                    # Include ACK text in shadow if it was sent
                    ack_line = f"\n⏳ ACK: {ack_text_for_shadow}" if ack_text_for_shadow else ""
                    forward_text = (
                        f"[{tenant_name}]\n"
                        f"👤 {patient_phone}: {text_body}"
                        f"{ack_line}\n"
                        f"🤖 Bot: {reply_text}"
                    )
                    # Truncate to WhatsApp's 4096 char limit
                    if len(forward_text) > 4000:
                        forward_text = forward_text[:3997] + "..."
                    await MetaGraphAPIClient.send_text_message(
                        phone_number_id=tenant.ws_phone_id,
                        to=shadow_phone,
                        text=forward_text,
                        token=tenant.ws_token or "mock"
                    )
                    logger.debug(f"📨 [ORCH] Shadow-forwarded to admin {shadow_phone}")
                except Exception as fwd_err:
                    # Non-fatal: shadow forwarding failure must not affect the user
                    logger.error(f"❌ [ORCH] Shadow forward failed: {repr(fwd_err)}")
                    sentry_sdk.capture_exception(fwd_err)
                    await send_discord_alert(
                        title=f"❌ Shadow Forward Failed | Tenant {tenant.id}",
                        description=f"Admin: {shadow_phone}\nError: {repr(fwd_err)[:300]}",
                        severity="error", error=fwd_err
                    )

            # return_exceptions=True: prevents one failing task from cancelling
            # the others. Each task has its own try/except (Rule 9), but gather
            # itself can still propagate if a task's except block raises.
            _gather_results = await asyncio.gather(
                _persist_reply(),
                _send_meta(),
                _shadow_forward(),
                return_exceptions=True
            )
            # Log any unexpected exceptions that leaked past the internal try/except
            _task_names = ["_persist_reply", "_send_meta", "_shadow_forward"]
            for _i, _result in enumerate(_gather_results):
                if isinstance(_result, BaseException):
                    logger.error(
                        f"💥 [ORCH] Gather task '{_task_names[_i]}' leaked exception: {repr(_result)}"
                    )
                    sentry_sdk.capture_exception(_result)
            logger.info("✨ [ORCH] Done.")

        except Exception as e:
            logger.error(f"💥 [ORCH] FATAL: {e}", exc_info=True)
            # Enrich Sentry with pipeline context for easier debugging
            # Ref: https://docs.sentry.io/platforms/python/enriching-events/context/
            sentry_sdk.set_context("pipeline", {
                "tenant_id": str(tenant.id) if tenant else "unknown",
                "contact_id": str(contact_id) if contact_id else "unknown",
                "is_simulation": payload.get("is_simulation", False),
                "step": "orchestration_pipeline",
            })
            sentry_sdk.capture_exception(e)
            await send_discord_alert(title=f"💥 AI Orchestration Fatal Crash | Tenant {tenant.id}", description=f"Pipeline exception for contact {contact_id}", error=e, severity="error")

        finally:
            # ============================================================
            # INC-3 + INC-5: Processing lock release with retry
            #
            # This is the ONLY place the processing lock is released.
            # Guarantees:
            #   - ALWAYS runs (finally block) — even on unhandled exceptions
            #   - 1 retry with 2s backoff — handles transient network failures
            #   - Full Sentry + Discord alerting if BOTH attempts fail
            #   - Discord alert includes the exact SQL for manual unlock
            #
            # Root cause (April 12 2026 incident):
            #   _unset_processing() was inside asyncio.gather alongside
            #   _send_meta(). When Cloud Run's network died, ALL gather
            #   tasks failed simultaneously. No retry, no finally block =
            #   contact permanently locked, all messages silently dropped.
            # ============================================================
            if contact_id:
                _lock_released = False
                for _lock_attempt in range(2):
                    try:
                        await db.table("contacts").update({
                            "is_processing_llm": False
                        }).eq("id", contact_id).execute()
                        logger.info(
                            f"🔓 [ORCH] Lock released for contact {contact_id} "
                            f"(attempt {_lock_attempt + 1})"
                        )
                        _lock_released = True
                        break
                    except Exception as lock_release_err:
                        if _lock_attempt == 0:
                            # First attempt failed — retry after backoff
                            logger.warning(
                                f"⚠️ [ORCH] Lock release attempt 1 failed for contact "
                                f"{contact_id}, retrying in 2s: {lock_release_err}"
                            )
                            sentry_sdk.capture_message(
                                f"Lock release retry triggered | Contact {contact_id} | "
                                f"Tenant {tenant.id}",
                                level="warning"
                            )
                            try:
                                await asyncio.sleep(2)
                            except Exception:
                                pass  # sleep failure is non-critical
                        else:
                            # Second attempt also failed — CRITICAL alert
                            logger.error(
                                f"🔴 [ORCH] Lock release FAILED after 2 attempts — "
                                f"contact {contact_id} may be permanently locked: "
                                f"{lock_release_err}"
                            )
                            sentry_sdk.set_context("lock_release_failure", {
                                "contact_id": str(contact_id),
                                "tenant_id": str(tenant.id) if tenant else "unknown",
                                "patient_phone": patient_phone if 'patient_phone' in dir() else "unknown",
                                "attempts": 2,
                                "final_error": str(lock_release_err)[:500],
                                "incident_ref": "INC-3/INC-5 April 12 2026",
                            })
                            sentry_sdk.capture_exception(lock_release_err)
                            try:
                                await send_discord_alert(
                                    title=(
                                        f"🔴 PERMANENT LOCK RISK | Contact {contact_id} "
                                        f"| Tenant {tenant.id}"
                                    ),
                                    description=(
                                        f"Lock release failed after 2 attempts.\n"
                                        f"Contact may be permanently locked "
                                        f"(is_processing_llm=true).\n\n"
                                        f"MANUAL INTERVENTION REQUIRED:\n"
                                        f"```sql\n"
                                        f"UPDATE contacts SET is_processing_llm = false "
                                        f"WHERE id = '{contact_id}';\n"
                                        f"```\n\n"
                                        f"Error: {str(lock_release_err)[:300]}"
                                    ),
                                    severity="error", error=lock_release_err
                                )
                            except Exception:
                                # If even Discord fails, we've logged + Sentry'd above
                                pass
