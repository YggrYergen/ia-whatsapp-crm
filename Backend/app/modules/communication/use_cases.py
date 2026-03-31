import asyncio
from supabase import Client
import json
from app.core.models import TenantContext
from app.infrastructure.messaging.meta_graph_api import MetaGraphAPIClient
from app.modules.intelligence.router import LLMFactory
from app.infrastructure.telemetry.logger_service import logger
from app.modules.intelligence.tool_registry import tool_registry

class ProcessMessageUseCase:
    
    @staticmethod
    async def execute(payload: dict, tenant: TenantContext, db: Client):
        logger.info(f"Starting background orchestration for tenant: {tenant.id}")
        
        try:
            entry = payload["entry"][0]
            changes = entry["changes"][0]["value"]
            if "messages" not in changes:
                return
                
            message = changes["messages"][0]
            patient_phone = message.get("from")
            text_body = message.get("text", {}).get("body", "")
            
            if not tenant.is_active:
                logger.warning("Tenant deactivated. Ignoring webhook.")
                return

            contact_res = await asyncio.to_thread(
                lambda: db.table("contacts").select("*").eq("phone_number", patient_phone).eq("tenant_id", tenant.id).execute()
            )
            
            # --- 1. Manage Contact & Bot Status ---
            contact_id = None
            bot_active = True
            contact_role = "cliente"
            
            if contact_res.data:
                bot_active = contact_res.data[0].get("bot_active", True)
                contact_id = contact_res.data[0].get("id")
                contact_role = contact_res.data[0].get("role", "cliente")
            else:
                # Crear contacto de forma automática si un número desconocido inicia la conversación
                try:
                    profile_name = changes.get("contacts", [{}])[0].get("profile", {}).get("name", "Lead")
                    new_contact = await asyncio.to_thread(
                        lambda: db.table("contacts").insert({
                            "tenant_id": tenant.id,
                            "phone_number": patient_phone,
                            "name": profile_name,
                            "bot_active": True
                        }).execute()
                    )
                    if new_contact.data:
                        contact_id = new_contact.data[0]["id"]
                except Exception as e:
                    logger.error(f"Failed creating new contact: {e}", exc_info=True)
                
            # --- 2. Sincronizar Mensaje Entrante para el Frontend Realtime ---
            if contact_id:
                try:
                    await asyncio.to_thread(
                        lambda: db.table("messages").insert({
                            "contact_id": contact_id,
                            "tenant_id": tenant.id,
                            "sender_role": "user",
                            "content": text_body
                        }).execute()
                    )
                    logger.info("Inbound user message synced to Database.")
                except Exception as inbound_err:
                    logger.error(f"Inbound DB Sync error: {inbound_err}", exc_info=True)
                
            if not bot_active:
                logger.info("Human in the loop mode active for contact. Bot muted.")
                return
                
            # --- 3. Memoria: Recuperar historial para contexto de la AI ---
            history = []
            if contact_id:
                hist_res = await asyncio.to_thread(
                    lambda: db.table("messages").select("sender_role, content").eq("contact_id", contact_id).order("timestamp", desc=True).limit(15).execute()
                )
                if hist_res.data:
                    # Invertir para leer cronológicamente
                    for m in reversed(hist_res.data):
                        rol = "assistant" if m["sender_role"] == "assistant" else "user"
                        history.append({"role": rol, "content": m["content"]})
            
            import pytz
            from datetime import datetime
            chile_tz = pytz.timezone("America/Santiago")
            current_time_str = datetime.now(chile_tz).strftime("%Y-%m-%d %H:%M")

            # Si la query falló o la DB estaba vacía, inyectamos el actual por default
            if not history or history[-1].get("content") != text_body:
                # Inyección In-Prompt "Sesgo de Recencia" al final de la ventana de contexto
                time_prefix = f"[(Log Interno): El usuario envió esto a las {current_time_str} hora Chile]\n"
                history.append({"role": "user", "content": time_prefix + text_body})

            llm_strategy = LLMFactory.create(tenant_context=tenant)
            provider = tenant.llm_provider if tenant.llm_provider else "openai"
            tools_schema = tool_registry.get_all_schemas(provider=provider.lower())
            
            system_prompt = tenant.system_prompt if tenant.system_prompt else f"You are a helpful assistant for {tenant.name}."
            
            # --- 3.5. Inject Current Time Context (Anti-Alucinaciones Armor) ---
            system_prompt += f"""

[RELOJ INTERNO DEL SISTEMA - OBLIGATORIO]
La fecha y hora exacta en Santiago de Chile es: {current_time_str}
REGLA DE ORO: Ignora ABSOLUTAMENTE cualquier hora o fecha que hayas afirmado en cualquier mensaje anterior del historial. Tu "memoria" pasada ya no es confiable. Si el usuario pregunta la hora o para cualquier agendamiento, SIEMPRE BASATE ÚNICA Y ESTRICTAMENTE en este reloj maestro.
"""
            
            # --- 4. First Inference Pass ---
            response_dto = await llm_strategy.generate_response(system_prompt=system_prompt, message_history=history, tools=tools_schema)
            
            reply_text = ""
            
            if response_dto.has_tool_calls:
                logger.info(f"Functional tooling triggered ({len(response_dto.tool_calls)}) actions")
                tool_results = []
                
                for t_call in response_dto.tool_calls:
                    name = t_call.get("name")
                    args = t_call.get("arguments", "{}")
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                            
                    args["tenant_context"] = tenant
                    args["caller_phone"] = patient_phone
                    args["caller_role"] = contact_role
                            
                    logger.debug(f"Executing AI Tool: {name} con argumentos inyectados exitosamente.")
                    try:
                        result = await tool_registry.execute_tool(name, **args)
                        tool_results.append(f"Tool '{name}' result:\n{result}")
                    except Exception as e:
                        logger.exception(f"Tool Execution Vault Crash (Detailed Traceback): {e}")
                        tool_results.append(f"Tool '{name}' failed: {str(e)}")
                
                observations = "\n".join(tool_results)
                history.append({
                    "role": "system", 
                    "content": f"SYSTEM TOOL EXECUTION RESULTS:\n{observations}\n\nCRITICAL INSTRUCTION: If the tool result contains an 'error', YOU MUST TELL THE USER IT FAILED and provide the exact reason. DO NOT hallucinate success if the status is 'error'."
                })
                
                logger.info("Initiating LLM inference loop (Synthesis phase) injecting tool findings.")
                final_dto = await llm_strategy.generate_response(system_prompt=system_prompt, message_history=history, tools=None)
                reply_text = final_dto.content
            else:
                reply_text = response_dto.content

            if not reply_text:
                reply_text = "(Fallback) Se ha procesado tu solicitud."

            # --- 5. Sync Outbound Message and Dispatch ---
            if contact_id:
                try:
                    await asyncio.to_thread(
                        lambda: db.table("messages").insert({
                            "contact_id": contact_id,
                            "tenant_id": tenant.id,
                            "sender_role": "assistant",
                            "content": reply_text
                        }).execute()
                    )
                    logger.info("AI response synced to Supabase (Realtime Frontend Update Triggered)")
                except Exception as db_err:
                    logger.error(f"Failed DB Sync: {db_err}", exc_info=True)

            try:
                await MetaGraphAPIClient.send_text_message(
                    phone_number_id=tenant.ws_phone_id,
                    to=patient_phone,
                    text=reply_text,
                    token=tenant.ws_token if tenant.ws_token else "mock_token" 
                )
            except Exception as meta_err:
                logger.warning(f"Meta Sync bypassed (Local Dev Mode): {str(meta_err)}")
                
        except Exception as e:
            logger.error(f"FATAL orchestrator crash. Raw JSON snippet: {str(payload)[:250]}", exc_info=True)
