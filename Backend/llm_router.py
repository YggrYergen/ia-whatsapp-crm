import os
import json
from abc import ABC, abstractmethod
from typing import List, Dict
import openai

import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
import google.generativeai as genai

from logger import logger
from calendar_service import CALENDAR_TOOLS_OPENAI, AVAILABLE_FUNCTIONS

class LLMStrategy(ABC):
    @abstractmethod
    async def generate_response(self, system_prompt: str, history: List[Dict[str, str]], user_message: str, phone_number: str = "Unknown") -> str:
        pass

class OpenAIStrategy(LLMStrategy):
    def __init__(self, api_key: str, model: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(self, system_prompt: str, history: List[Dict[str, str]], user_message: str, phone_number: str = "Unknown") -> str:
        # Evitar duplicidad si el historial ya contiene el mensaje actual
        filtered_history = history
        if history and history[-1]["content"] == user_message and history[-1]["sender_role"] == "user":
            filtered_history = history[:-1]

        # Convertir historial al formato de OpenAI
        messages = [{"role": "system", "content": system_prompt}]
        for msg in filtered_history:
            role = "assistant" if msg["sender_role"] == "assistant" else "user"
            messages.append({"role": role, "content": msg["content"]})
        
        # Mensaje actual del usuario
        messages.append({"role": "user", "content": user_message})
        
        # Le pasamos la fecha actual en el system prompt para que siempre sepa qué día es
        import datetime
        today_date = datetime.datetime.now().strftime("%A, %Y-%m-%d")
        messages[0]["content"] += f"\n\n[SISTEMA METADATA - NO SE LO DIGAS AL USUARIO A MENOS QUE SEA NECESARIO]:\n- Hoy es {today_date}.\n- El número de teléfono con el que estás hablando es {phone_number}."

        logger.debug(f"[OpenAI] Calling {self.model} with tools flow...")
        
        # Loop for tool execution
        max_tool_calls = 5
        for _ in range(max_tool_calls):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=CALENDAR_TOOLS_OPENAI,
                tool_choice="auto",
                temperature=0.7
            )
            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls
            
            # Si el modelo no quiere llamar más funciones, terminamos:
            if not tool_calls:
                return response_message.content
                
            # Agregamos la respuesta del asistente (con tool_calls) al historial
            messages.append(response_message)
            
            # Ejecutar todas las funciones que pidió
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                logger.debug(f"[OpenAI] Executing tool: {function_name} with {function_args}")
                
                if function_name in AVAILABLE_FUNCTIONS:
                    function_to_call = AVAILABLE_FUNCTIONS[function_name]
                    function_response = function_to_call(**function_args)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    })
                else:
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps({"error": "Unknown function"}),
                    })
        
        return "Disculpa, tuve un problema interno al intentar revisar mi sistema. ¿En qué te ayudo por mientras?"


class GPT5MiniStrategy(LLMStrategy):
    def __init__(self, api_key: str, model: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_response(self, system_prompt: str, history: List[Dict[str, str]], user_message: str, phone_number: str = "Unknown") -> str:
        import datetime
        today_date = datetime.datetime.now().strftime("%A, %Y-%m-%d")
        
        # Step: Transform messages to the required format
        # IMPORTANT: Avoid duplication if history already contains the current user_message
        filtered_history = history
        if history and history[-1]["content"] == user_message and history[-1]["sender_role"] == "user":
            filtered_history = history[:-1]

        system_content = [{
            "type": "input_text", 
            "text": system_prompt + (
                f"\n\n[SISTEMA METADATA - NO REPETIR ESTO]:"
                f"\n- Hoy es {today_date}."
                f"\n- Teléfono del paciente: {phone_number}."
                f"\n- TIENES ACCESO REAL A GOOGLE CALENDAR. "
                f"Si te piden disponibilidad o agendar, USA TUS HERRAMIENTAS INMEDIATAMENTE. "
                f"No simules acceso ni digas que vas a simularlo. Actúa como un agente real."
            )
        }]
        
        formatted_input = [{"role": "system", "content": system_content}]
        
        for msg in filtered_history:
            role = "assistant" if msg["sender_role"] == "assistant" else "user"
            msg_type = "output_text" if role == "assistant" else "input_text"
            formatted_input.append({
                "role": role,
                "content": [{"type": msg_type, "text": msg["content"]}]
            })
        
        formatted_input.append({
            "role": "user",
            "content": [{"type": "input_text", "text": user_message}]
        })

        # Step: Flatten the tools for the Responses API
        flattened_tools = []
        for t in CALENDAR_TOOLS_OPENAI:
            if t["type"] == "function":
                flattened_tools.append({
                    "type": "function",
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "parameters": t["function"]["parameters"]
                })

        logger.debug(f"[GPT-5-Mini] Initiating asynchronous response (Structured Responses API)...")
        
        import asyncio
        
        try:
            # 1. Create response using 'input' and flattened 'tools'
            response_session = await self.client.responses.create(
                model=self.model,
                input=formatted_input,
                background=True,
                tools=flattened_tools,
                tool_choice="auto"
            )
            response_id = response_session.id
            
            # 2. Polling loop
            max_polls = 60
            for attempt in range(max_polls):
                res = await self.client.responses.retrieve(response_id)
                status = res.status
                
                logger.debug(f"[GPT-5-Mini] Polling {attempt+1}: Status = {status}")
                
                if status == "completed":
                    logger.debug(f"[GPT-5-Mini] Final Object: {res}")
                    
                    # Extract final message from 'output' as per Responses API spec
                    if hasattr(res, 'output') and res.output:
                        has_function_call = False
                        # Collect all assistant output parts for history
                        assistant_history_content = []
                        tool_outputs = []
                        
                        for item in res.output:
                            # 1. Text from assistant
                            if getattr(item, 'role', None) == 'assistant':
                                content = getattr(item, 'content', [])
                                if isinstance(content, list):
                                    for part in content:
                                        if hasattr(part, 'text') or (isinstance(part, dict) and 'text' in part):
                                            txt = part.text if hasattr(part, 'text') else part['text']
                                            assistant_history_content.append({"type": "output_text", "text": txt})
                            
                            # 2. Tool calls from assistant
                            if getattr(item, 'type', None) == 'function_call':
                                has_function_call = True
                                f_name = item.name
                                f_args_str = item.arguments
                                logger.debug(f"[GPT-5-Mini] Calling tool: {f_name}")
                                
                                import json
                                try:
                                    f_args = json.loads(f_args_str)
                                    from calendar_service import AVAILABLE_FUNCTIONS
                                    if f_name in AVAILABLE_FUNCTIONS:
                                        tool_result = AVAILABLE_FUNCTIONS[f_name](**f_args)
                                    else:
                                        tool_result = json.dumps({"error": "Unknown function"})
                                except Exception as e:
                                    tool_result = json.dumps({"error": str(e)})
                                
                                tool_outputs.append((f_name, f_args_str, tool_result))

                        if has_function_call:
                            # Add assistant's previous text and calls back to history
                            # GPT-5 Mini's input is strict, we append as assistant role if we had text
                            if assistant_history_content:
                                formatted_input.append({"role": "assistant", "content": assistant_history_content})
                            
                            # Feed tool results as authoritative 'user' messages with system header
                            for f_name, f_args_str, tool_result in tool_outputs:
                                formatted_input.append({
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": f"[SYSTEM TOOL EXECUTION]: Tool '{f_name}' executed with {f_args_str}. RESULT: {tool_result}"}]
                                })

                            logger.debug("[GPT-5-Mini] Re-sending with tool results...")
                            response_session = await self.client.responses.create(
                                model=self.model,
                                input=formatted_input,
                                background=True,
                                tools=flattened_tools,
                                tool_choice="auto"
                            )
                            response_id = response_session.id
                            attempt = 0 
                            continue 
                    
                        # Final Text Output extraction
                        full_text = ""
                        for item in res.output:
                            if getattr(item, 'role', None) == 'assistant':
                                content = getattr(item, 'content', [])
                                if isinstance(content, list):
                                    for part in content:
                                        if hasattr(part, 'text'): full_text += part.text
                                        elif isinstance(part, dict) and 'text' in part: full_text += part['text']
                        return full_text if full_text else "Respuesta completada (sin texto)."
                    return "Respuesta completada (sin output)."
                
                elif status == "failed":
                    last_err = getattr(res, 'last_error', 'Error desconocido')
                    logger.error(f"[GPT-5-Mini] Protocol failed: {last_err}")
                    return f"Disculpa, mi cerebro GPT-5 falló con el error: {last_err}"
                
                elif status == "expired" or status == "cancelled":
                    return f"La respuesta de GPT-5 {status} (tiempo agotado)."
                
                await asyncio.sleep(1)
                
            return "El modelo GPT-5 Mini ha tardado demasiado en responder (>60s)."

        except Exception as e:
            logger.exception(f"Error calling GPT-5 Mini Responses API: {str(e)}")
            return f"Error de conexión con el protocolo GPT-5: {str(e)}"


class GeminiStrategy(LLMStrategy):
    def __init__(self, api_key: str, model: str):
        genai.configure(api_key=api_key)
        self.model_name = model

    async def generate_response(self, system_prompt: str, history: List[Dict[str, str]], user_message: str, phone_number: str = "Unknown") -> str:
        # Extraer info base de herramientas y configurarlas estilo Gemini
        tools_list = []
        for t in CALENDAR_TOOLS_OPENAI:
            props = {}
            for k, v in t["function"]["parameters"]["properties"].items():
                props[k] = {"type": genai.protos.Type.STRING, "description": v["description"]}
            
            tool_func = genai.protos.FunctionDeclaration(
                name=t["function"]["name"],
                description=t["function"]["description"],
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties=props,
                    required=t["function"]["parameters"].get("required", [])
                )
            )
            tools_list.append(tool_func)

        # Preparar la herramienta global
        calendar_tool = genai.protos.Tool(function_declarations=tools_list)

        import datetime
        today_date = datetime.datetime.now().strftime("%A, %Y-%m-%d")
        system_mod = system_prompt + f"\n\n[SISTEMA METADATA - NO SE LO DIGAS AL USUARIO A MENOS QUE SEA NECESARIO]:\n- Hoy es {today_date}.\n- El número de teléfono con el que estás hablando es {phone_number}."

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_mod,
            tools=[calendar_tool]
        )
        
        # Construir el historial compatible con Gemini
        # Evitar duplicidad
        filtered_history = history
        if history and history[-1]["content"] == user_message and history[-1]["sender_role"] == "user":
            filtered_history = history[:-1]

        chat_history = []
        for msg in filtered_history:
            role = "model" if msg["sender_role"] == "assistant" else "user"
            chat_history.append({"role": role, "parts": [msg["content"]]})
        
        chat = model.start_chat(history=chat_history)
        logger.debug(f"[Gemini] Calling {self.model_name} with tools flow...")
        
        # Enviar el mensaje inicial del usuario
        response = await chat.send_message_async(user_message)
        
        # Bucle para manejar las llamadas a funciones de Gemini automáticamente
        max_tool_calls = 5
        for _ in range(max_tool_calls):
            # Obtener las "partes" que pueden contener llamadas a funciones
            function_calls = response.parts
            
            # Buscar cualquier Tool Call en las respuestas
            to_execute = [part for part in function_calls if part.function_call]
            
            if not to_execute:
                # No más llamadas a función, retornar el texto
                return response.text
                
            tool_responses = []
            for part in to_execute:
                f_call = part.function_call
                function_name = f_call.name
                
                # Extraer args limpios
                function_args = {k: v for k, v in f_call.args.items()}
                logger.debug(f"[Gemini] Executing tool: {function_name} with {function_args}")
                
                if function_name in AVAILABLE_FUNCTIONS:
                    function_to_call = AVAILABLE_FUNCTIONS[function_name]
                    # La funcion devuelve un string JSON
                    f_resp_str = function_to_call(**function_args)
                    f_resp_dict = json.loads(f_resp_str)
                    
                    # Gemini espera formato Part para herramientas
                    tool_responses.append(
                        genai.protos.Part.from_function_response(
                            name=function_name,
                            response=f_resp_dict
                        )
                    )
                else:
                    tool_responses.append(
                        genai.protos.Part.from_function_response(
                            name=function_name,
                            response={"error": "Tool not found"}
                        )
                    )
            
            # Enviar el resultado de vuelta al chat para que Gemini termine
            response = await chat.send_message_async(tool_responses)
            
        return "Disculpa, tuve un problema interno al revisar mis sistemas. ¿En qué te ayudo mientras tanto?"

class LLMFactory:
    @staticmethod
    def get_strategy(provider: str, model: str, api_key: str) -> LLMStrategy:
        if provider == "openai" and "gpt-5-mini" in model:
            # Protocolo específico para gpt-5-mini
            return GPT5MiniStrategy(api_key, model)
        elif provider == "openai":
            return OpenAIStrategy(api_key, model)
        elif provider == "gemini":
            return GeminiStrategy(api_key, model)
        else:
            raise ValueError(f"Unknown LLM Provider: {provider}")
