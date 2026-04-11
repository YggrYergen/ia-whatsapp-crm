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
            text_body = message.get("text", {}).get("body", "")
            
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
            # Error points #6-7: Processing lock + history fetch
            async def _set_processing():
                if contact_id:
                    try:
                        await db.table("contacts").update({"is_processing_llm": True}).eq("id", contact_id).execute()
                    except Exception as lock_err:
                        logger.error(f"❌ [ORCH] Failed to set processing lock: {lock_err}")
                        sentry_sdk.capture_exception(lock_err)
                        await send_discord_alert(
                            title=f"❌ Processing Lock Failed | Tenant {tenant.id}",
                            description=f"Contact: {contact_id}\nError: {str(lock_err)[:300]}",
                            severity="error", error=lock_err
                        )
                        # Non-fatal: continue without lock (risk of double-processing)

            async def _fetch_history():
                history = []
                if contact_id:
                    logger.info("📚 [ORCH] Fetching history...")
                    try:
                        hist_res = await db.table("messages").select("sender_role, content").eq("contact_id", contact_id).order("timestamp", desc=True).limit(30).execute()
                        if hist_res.data:
                            for m in reversed(hist_res.data):
                                sr = m["sender_role"]
                                if sr == "system_alert":
                                    continue  # System alerts are not part of the conversation
                                elif sr in ("assistant", "human_agent"):
                                    rol = "assistant"  # Both AI and staff are "business side"
                                else:
                                    rol = "user"
                                history.append({"role": rol, "content": m["content"]})
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

            # Error points #9-10: LLM strategy creation + schema fetch
            logger.info(f"🧠 [ORCH] Calling LLM (Provider={tenant.llm_provider})...")
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

                logger.info(
                    f"✅ [ORCH] Round {rounds_executed}/{MAX_TOOL_ROUNDS} — "
                    f"ToolCalls={response_dto.has_tool_calls} | "
                    f"ContentPreview='{(response_dto.content or '')[:120]}'"
                )

                # ── No tool calls → final text response, we're done ──
                if not response_dto.has_tool_calls:
                    reply_text = response_dto.content or ""
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
            async def _persist_reply():
                if contact_id:
                    try:
                        await db.table("messages").insert({"contact_id": contact_id, "tenant_id": tenant.id, "sender_role": "assistant", "content": reply_text}).execute()
                    except Exception as persist_err:
                        logger.error(f"❌ [ORCH] Failed to persist reply: {persist_err}")
                        sentry_sdk.capture_exception(persist_err)
                        await send_discord_alert(
                            title=f"❌ Reply Persistence Failed | Tenant {tenant.id}",
                            description=f"Contact: {contact_id}\nReply: {reply_text[:200]}\nError: {str(persist_err)[:200]}",
                            severity="error", error=persist_err
                        )

            async def _send_meta():
                if not is_simulation:
                    try:
                        logger.info("📲 [ORCH] Sending via Meta API...")
                        await MetaGraphAPIClient.send_text_message(phone_number_id=tenant.ws_phone_id, to=patient_phone, text=reply_text, token=tenant.ws_token or "mock")
                    except Exception as meta_err:
                        logger.error(f"❌ [ORCH] Meta API send failed: {meta_err}")
                        sentry_sdk.capture_exception(meta_err)
                        await send_discord_alert(
                            title=f"💥 Meta API Send Failed | Tenant {tenant.id}",
                            description=f"Phone: {patient_phone}\nReply: {reply_text[:200]}\nError: {str(meta_err)[:200]}",
                            severity="error", error=meta_err
                        )

            async def _unset_processing():
                if contact_id:
                    try:
                        await db.table("contacts").update({"is_processing_llm": False}).eq("id", contact_id).execute()
                    except Exception as unset_err:
                        logger.error(f"❌ [ORCH] Failed to unset processing lock: {unset_err}")
                        sentry_sdk.capture_exception(unset_err)
                        await send_discord_alert(
                            title=f"🔒 Processing Lock Release Failed | Tenant {tenant.id}",
                            description=f"Contact {contact_id} may be permanently locked.\nError: {str(unset_err)[:300]}",
                            severity="error", error=unset_err
                        )

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
