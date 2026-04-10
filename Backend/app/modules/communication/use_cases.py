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

class ProcessMessageUseCase:
    
    @staticmethod
    async def execute(payload: dict, tenant: TenantContext, db: AsyncClient):
        logger.info(f"🚀 [ORCH] Start for Tenant={tenant.id}")
        # Tag ALL Sentry events in this execution with tenant context
        sentry_sdk.set_tag("tenant_id", str(tenant.id))
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
                    await send_discord_alert(title=f"❌ Contact Creation Error | Tenant {tenant.id}", description=str(e), severity="error", error=e)
            
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
                    await send_discord_alert(title=f"❌ Msg Persistence Error | Tenant {tenant.id}", description=f"Failed to persist inbound message for contact {contact_id}: {str(e)[:300]}", severity="error", error=e)

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
            
            # ============================================================
            # BUG-1 Layer 1: Inject INTERNAL_TOOL_RULES between tenant
            # prompt and [CONTEXTO]. These are system-level safety rules
            # the tenant cannot edit or accidentally delete.
            # ============================================================
            system_prompt = f"{tenant.system_prompt}\n\n{INTERNAL_TOOL_RULES}\n\n[CONTEXTO]\nPaciente: {contact_data.get('name', 'Lead') if contact_data else 'Lead'}\nTeléfono: {patient_phone}\nRol: {contact_role}\nHora: {current_time_str}\n"
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

            response_dto = await llm_strategy.generate_response(
                system_prompt=system_prompt,
                message_history=history,
                tools=tools_schema,
                tool_choice_override=tool_choice_override
            )
            
            # ============================================================
            # BUG-1 Layer 4: Enhanced logging — full response details
            # ============================================================
            logger.info(f"✅ [ORCH] LLM Reply received. ToolCalls={response_dto.has_tool_calls} | ContentPreview='{(response_dto.content or '')[:150]}'")

            # ============================================================
            # BUG-1 Layer 2: Post-LLM Silent Failure Detection
            # Detect the "Silence Pattern": LLM text implies a tool action
            # (e.g., "voy a notificar a un agente") but has_tool_calls=False.
            # This is a critical guardrail — log to Sentry + Discord.
            # ============================================================
            if not response_dto.has_tool_calls and response_dto.content:
                content_lower = response_dto.content.lower()
                for tool_name, patterns in TOOL_ACTION_PATTERNS:
                    if any(p in content_lower for p in patterns):
                        logger.warning(f"🚨 [ORCH] SILENT FAILURE DETECTED: LLM text implies '{tool_name}' but has_tool_calls=False")
                        sentry_sdk.set_context("silent_failure", {
                            "expected_tool": tool_name,
                            "llm_content": response_dto.content[:500],
                            "has_tool_calls": False,
                            "tenant_id": str(tenant.id),
                            "contact_id": str(contact_id) if contact_id else "unknown",
                            "patient_phone": patient_phone,
                            "force_escalation": force_escalation,
                        })
                        sentry_sdk.capture_message(
                            f"LLM Silent Failure: implied '{tool_name}' without calling it",
                            level="warning"
                        )
                        await send_discord_alert(
                            title=f"🚨 LLM Silent Failure: {tool_name}",
                            description=f"LLM text implied tool action but didn't call it.\nTenant: {tenant.id}\nPhone: {patient_phone}\nContent: {response_dto.content[:200]}",
                            severity="warning"
                        )
                        break

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
                        # BUG-1 Layer 4: Log tool result for traceability
                        logger.info(f"✅ [ORCH] Tool '{t['name']}' result: {str(res)[:300]}")
                        # ============================================================
                        # BUG-3: Detect tool-level status:error responses
                        # These are NOT Python exceptions — the tool ran but
                        # returned an error (e.g. "no appointment found").
                        # ALWAYS report to Sentry + Discord for observability.
                        # ============================================================
                        res_str = str(res)
                        if '"status": "error"' in res_str or '"status":"error"' in res_str:
                            logger.warning(f"⚠️ [ORCH] Tool '{t['name']}' returned status:error — alerting Sentry/Discord")
                            sentry_sdk.set_context("tool_error", {
                                "tool_name": t['name'],
                                "result": res_str[:500],
                                "tenant_id": str(tenant.id),
                                "patient_phone": patient_phone,
                                "contact_role": contact_role,
                            })
                            sentry_sdk.capture_message(
                                f"Tool '{t['name']}' returned error | Tenant {tenant.id}",
                                level="warning"
                            )
                            await send_discord_alert(
                                title=f"⚠️ Tool Error: {t['name']} | Tenant {tenant.id}",
                                description=f"Tool returned error status.\nPhone: {patient_phone}\nRole: {contact_role}\nResult: {res_str[:300]}",
                                severity="warning"
                            )
                    except Exception as e: 
                        results.append(f"Tool {t['name']} EXCEPTION: {e}")
                        sentry_sdk.capture_exception(e)
                        await send_discord_alert(title=f"💥 Tool Crash: {t['name']} | Tenant {tenant.id}", description=str(e), severity="error", error=e)
                
                # ============================================================
                # BUG-3 Fix: Tool Result Error Injection (Synthesis Pass)
                # Distinguish between:
                #   - "business errors" (tool ran OK but e.g. "no appointment
                #     found") → LLM should relay naturally
                #   - "technical crashes" (Python exception) → LLM should
                #     tell patient a human was requested
                # ============================================================
                has_business_error = any(
                    ('"status": "error"' in r or '"status":"error"' in r) and "EXCEPTION:" not in r
                    for r in results
                )
                has_crash = any("EXCEPTION:" in r for r in results)
                
                history.append({"role": "user", "content": f"[Resultados]: {results}"})
                
                if has_crash:
                    # Technical crash: escalate to human
                    logger.warning(f"⚠️ [ORCH] Tool CRASHED — injecting human-escalation instruction")
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
                    # Business error: just relay the tool's message naturally
                    logger.info(f"ℹ️ [ORCH] Tool returned business-level error — LLM will relay naturally")
                    history.append({
                        "role": "user", 
                        "content": "[INSTRUCCIÓN SISTEMA]: Los resultados anteriores contienen respuestas de error del sistema. "
                                   "Transmite la información al paciente de forma natural y amable, usando el mensaje de error como contexto. "
                                   "NO digas que la acción se realizó correctamente si el resultado indica que no se pudo completar. "
                                   "Continúa la conversación normalmente."
                    })
                
                final_dto = await llm_strategy.generate_response(system_prompt=system_prompt, message_history=history, tools=None)
                reply_text = final_dto.content or "Error final."

            if not reply_text: reply_text = "Lo siento, tuve un problema. ¿En qué te ayudo?"

            logger.info(f"📤 [ORCH] Final Reply: '{reply_text[:80]}...'")

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
            await send_discord_alert(title=f"💥 AI Orchestration Fatal Crash | Tenant {tenant.id}", description=f"Pipeline exception for contact {contact_id}", error=e, severity="error")
            if contact_id:
                try: 
                    await db.table("contacts").update({"is_processing_llm": False}).eq("id", contact_id).execute()
                except Exception as cleanup_err:
                    sentry_sdk.capture_exception(cleanup_err)
                    await send_discord_alert(title=f"🔒 Processing Lock Cleanup Failed | Contact {contact_id}", description=f"Failed to reset is_processing_llm=False. Contact may be permanently locked: {str(cleanup_err)[:300]}", severity="error", error=cleanup_err)
