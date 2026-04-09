import asyncio
from supabase import AsyncClient
import json
import pytz
from datetime import datetime
from app.core.models import TenantContext
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.modules.intelligence.router import LLMFactory
from app.infrastructure.telemetry.logger_service import logger
from app.modules.intelligence.tool_registry import tool_registry
from app.infrastructure.telemetry.discord_notifier import send_discord_alert
import sentry_sdk

class ProcessMessageUseCase:
    
    @staticmethod
    async def execute(payload: dict, tenant: TenantContext, db: AsyncClient):
        logger.info(f"🚀 [ORCH] Start for Tenant={tenant.id}")
        is_simulation = payload.get("is_simulation", False)
        contact_id = None
        
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]["value"]
            if "messages" not in changes:
                logger.info("ℹ️ [ORCH] No messages in payload.")
                return
                
            message = changes["messages"][0]
            patient_phone = message.get("from")
            text_body = message.get("text", {}).get("body", "").lower()
            
            logger.info(f"📩 [ORCH] Message from {patient_phone}: '{text_body}'")

            if not tenant.is_active:
                logger.warning("⚠️ [ORCH] Tenant deactivated. Ignoring.")
                return

            logger.info("🔍 [ORCH] Looking up contact...")
            contact_res = await db.table("contacts").select("*").eq("phone_number", patient_phone).eq("tenant_id", tenant.id).execute()
            
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
            else:
                logger.info("🆕 [ORCH] Creating new contact...")
                is_processing = False
                try:
                    profile_name = changes.get("contacts", [{}])[0].get("profile", {}).get("name", "Lead")
                    new_contact = await db.table("contacts").insert({
                        "tenant_id": tenant.id,
                        "phone_number": patient_phone,
                        "name": profile_name,
                        "bot_active": True
                    }).execute()
                    if new_contact.data:
                        contact_id = new_contact.data[0]["id"]
                        contact_data = new_contact.data[0]
                        logger.info(f"✅ [ORCH] New contact created: {contact_id}")
                except Exception as e:
                    logger.error(f"❌ [ORCH] Failed creating contact: {e}")
                    sentry_sdk.capture_exception(e)
            
            clinical_keywords = ["dolor", "fibrosis", "sangrado", "emergencia", "urgencia", "infectado"]
            force_escalation = any(kw in text_body for kw in clinical_keywords)
            if force_escalation:
                logger.warning(f"🚨 [ORCH] Clinical keyword detected!")

            # ============================================================
            # STEP 1: Persist inbound message always (Bot or Human)
            # ============================================================
            if contact_id and not is_simulation:
                logger.info("💾 [ORCH] Persisting inbound message...")
                try:
                    await db.table("messages").insert({
                        "contact_id": contact_id, "tenant_id": tenant.id,
                        "sender_role": "user", "content": text_body
                    }).execute()
                except Exception as e:
                    logger.error(f"❌ [ORCH] Msg persistence err: {e}")
                    sentry_sdk.capture_exception(e)

            # ============================================================
            # STEP 2: Logic routing (Bot Active check)
            # ============================================================
            if not bot_active:
                logger.info("🔇 [ORCH] Bot muted for this contact. Skipping LLM.")
                return

            if is_processing and not is_simulation:
                logger.info("⏳ [ORCH] Already processing. Skipping.")
                return

            # ============================================================
            # PARALLEL: Set processing lock + fetch history
            # ============================================================
            async def _set_processing():
                if contact_id:
                    await db.table("contacts").update({"is_processing_llm": True}).eq("id", contact_id).execute()

            async def _fetch_history():
                history = []
                if contact_id:
                    logger.info("📚 [ORCH] Fetching history...")
                    hist_res = await db.table("messages").select("sender_role, content").eq("contact_id", contact_id).order("timestamp", desc=True).limit(20).execute()
                    if hist_res.data:
                        for m in reversed(hist_res.data):
                            rol = "assistant" if m["sender_role"] == "assistant" else "user"
                            history.append({"role": rol, "content": m["content"]})
                return history

            # Run concurrently
            _, history = await asyncio.gather(
                _set_processing(),
                _fetch_history()
            )

            if not is_simulation:
                await asyncio.sleep(3)

            chile_tz = pytz.timezone("America/Santiago")
            current_time_str = datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M")

            if not history or history[-1].get("content", "").lower() != text_body:
                history.append({"role": "user", "content": f"[(Log): {current_time_str}]\n{text_body}"})

            logger.info(f"🧠 [ORCH] Calling LLM (Provider={tenant.llm_provider})...")
            llm_strategy = LLMFactory.create(tenant_context=tenant)
            tools_schema = tool_registry.get_all_schemas(provider=tenant.llm_provider.lower())
            
            system_prompt = f"{tenant.system_prompt}\n\n[CONTEXTO]\nPaciente: {contact_data.get('name', 'Lead') if contact_data else 'Lead'}\nTeléfono: {patient_phone}\nRol: {contact_role}\nHora: {current_time_str}\n"
            if force_escalation:
                system_prompt += "\n⚠️ RIESGO: Avisa amablemente que derivas a humano y usa 'request_human_escalation'."

            response_dto = await llm_strategy.generate_response(system_prompt=system_prompt, message_history=history, tools=tools_schema)
            logger.info(f"✅ [ORCH] LLM Reply received. ToolCalls={response_dto.has_tool_calls}")

            reply_text = response_dto.content or ""
            if response_dto.has_tool_calls:
                results = []
                for t in response_dto.tool_calls:
                    logger.info(f"🛠️ [ORCH] Executing tool: {t['name']}")
                    args = json.loads(t["arguments"]) if isinstance(t["arguments"], str) else t["arguments"]
                    args.update({"tenant_context": tenant, "patient_phone": patient_phone, "caller_phone": patient_phone, "caller_role": contact_role})
                    try:
                        res = await tool_registry.execute_tool(t["name"], **args)
                        results.append(f"Tool {t['name']} result: {res}")
                    except Exception as e: 
                        results.append(f"Tool {t['name']} failed: {e}")
                        sentry_sdk.capture_exception(e)
                        await send_discord_alert(title=f"Tool Execution Error: {t['name']}", description=str(e), severity="warning", error=e)
                
                history.append({"role": "user", "content": f"[Resultados]: {results}"})
                final_dto = await llm_strategy.generate_response(system_prompt=system_prompt, message_history=history, tools=None)
                reply_text = final_dto.content or "Error final."

            if not reply_text: reply_text = "Lo siento, tuve un problema. ¿En qué te ayudo?"

            logger.info(f"📤 [ORCH] Final Reply: '{reply_text[:50]}...'")

            # ============================================================
            # PARALLEL: Persist assistant reply + send via Meta API + unset processing
            # ============================================================
            async def _persist_reply():
                if contact_id:
                    await db.table("messages").insert({"contact_id": contact_id, "tenant_id": tenant.id, "sender_role": "assistant", "content": reply_text}).execute()

            async def _send_meta():
                if not is_simulation:
                    logger.info("📲 [ORCH] Sending via Meta API...")
                    await MetaGraphAPIClient.send_text_message(phone_number_id=tenant.ws_phone_id, to=patient_phone, text=reply_text, token=tenant.ws_token or "mock")

            async def _unset_processing():
                if contact_id:
                    await db.table("contacts").update({"is_processing_llm": False}).eq("id", contact_id).execute()

            await asyncio.gather(
                _persist_reply(),
                _send_meta(),
                _unset_processing()
            )
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
            await send_discord_alert(title="AI Orchestration Fatal Crash", description=f"Pipeline exception for contact {contact_id}", error=e, severity="error")
            if contact_id:
                try: 
                    await db.table("contacts").update({"is_processing_llm": False}).eq("id", contact_id).execute()
                except Exception as cleanup_err:
                    sentry_sdk.capture_exception(cleanup_err)
