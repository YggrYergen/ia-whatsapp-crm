# WhatsApp AI CRM - Multi-tenant SaaS (2026 Edition)

Este proyecto es un CRM B2B multi-tenant que integra WhatsApp con los modelos más potentes de IA (GPT-5.4 y Gemini 3.1).

## Arquitectura
- **Backend:** FastAPI (Python 3.11+) con BackgroundTasks para respuesta < 3s.
- **Frontend:** Next.js (App Router) con Supabase Realtime para chat en vivo.
- **BD:** Supabase (PostgreSQL) con RLS (Row Level Security).

## Configuración Local

### 1. Base de Datos (Supabase)
1. Crea un proyecto en [Supabase](https://supabase.com).
2. Ejecuta el archivo `schema.sql` en el SQL Editor de Supabase.
3. Habilita **Point in Time Recovery** en el panel para backups de 24h.

### 2. Backend (FastAPI)
1. `cd backend`
2. Crea un `.env`:
   ```env
   SUPABASE_URL=tu_url
   SUPABASE_SERVICE_ROLE_KEY=tu_service_key
   OPENAI_API_KEY=tu_key
   GEMINI_API_KEY=tu_key
   WHATSAPP_VERIFY_TOKEN=tu_token_verificacion
   ENVIRONMENT=development
   ```
3. `pip install -r requirements.txt`
4. `uvicorn main:app --reload`

### 3. Frontend (Next.js)
1. `cd frontend`
2. Crea un `.env.local`:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=tu_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=tu_anon_key
   ```
3. `npm install`
4. `npm run dev`

## Despliegue Producción

### Google Cloud Run (Backend)
1. `gcloud builds submit --tag gcr.io/PROJECT_ID/backend .`
2. `gcloud run deploy backend --image gcr.io/PROJECT_ID/backend --set-env-vars ENVIRONMENT=production`

### Vercel (Frontend)
1. Importa la carpeta `frontend/` en Vercel.
2. Configura las variables de entorno de Supabase.

## HITL e IA
- El CRM permite pausar la IA por contacto (`bot_active` en la tabla `contacts`).
- Si se pausa la IA, el agente humano puede responder manualmente desde la interfaz.

---


# Documentación de Estado Actual v1: Asistente IA

## 1. Visión General de la Arquitectura

El ecosistema opera bajo un esquema B2B multi-tenant que unifica las comunicaciones de WhatsApp. Utiliza un backend rápido (FastAPI) encargado de recibir los webhooks de Meta, responder con un 200 OK inmediatamente (para sortear los límites de WhatsApp) y derivar el procesamiento pesado a tareas asíncronas (`BackgroundTasks`). 

Las integraciones asíncronas se conectan a un enrutador inteligente de Modelos Fundacionales (OpenAI GPT-5 o Gemini), que a su vez orquesta llamadas a funciones (Function Calling) en tiempo real a servicios como Google Calendar. Todos los cambios de estado y mensajes se inyectan a una base de datos PostgreSQL en Supabase, la cual propaga de inmediato las actualizaciones vía `Realtime channels` al CRM reactivo del Frontend (Next.js), permitiendo una experiencia robusta y Human-In-The-Loop.

```mermaid
graph TD
    WA[WhatsApp Meta Webhook] <-->|JSON payload| Fast[FastAPI / main.py]
    Fast -->|Background Tasks| Router[LLM Factory Router]
    Router <-->|Responses API| OpenAI[OpenAI gpt-5/o4-mini]
    Router <-->|Tool Execution| Gemini[Gemini 3.1 Pro/Flash]
    Router -->|Function Calling| Tools[Google Calendar & Triage]
    Fast <-->|PostgreSQL (RLS)| DB[(Supabase)]
    DB <-->|Pub/Sub Realtime| UI[Next.js CRM Frontend]
```

## 2. Matriz de Estado de Implementación

| Módulo / Característica | Estado Actual | Descripción Breve | Archivos Clave |
|---|---|---|---|
| **Estructura Multi-Tenant** | Completado | Soporte nativo y aislamiento de BD implementado con RLS. | `schema.sql` |
| **Gateway WhatsApp & Background** | Completado | Recepción de webhooks, verificación Meta y encolado rápido. | `Backend/main.py` |
| **Frontend CRM en Tiempo Real** | Completado | Chat visual sincronizado por Supabase Realtime, con Human-in-the-Loop. | `Frontend/app/page.tsx` |
| **Routing de LLMs (GPT/Gemini)** | Completado | Fábrica de estrategias que parsea tools para Gemini o uses Responses API de GPT-5. | `Backend/llm_router.py` |
| **Herramientas de Agenda** | Completado | Lógica de negocio (CRUD) que interactúa orgánicamente con Google Calendar API. | `Backend/calendar_service.py` |
| **Servicio de Triaje** | Completado | Motor de pausa automática y notificación a número interno en casos de emergencia. | `Backend/triage_service.py` |
| **Panel de Configuración IA** | WIP | Interfaz para seleccionar el provider, modelo y alterar el system prompt del tenant. | `Frontend/app/config/page.tsx` |
| **Simulador de Chats Local** | WIP | Flujo aislado para emular pacientes contra el webhook usando un tenant semilla. | `Frontend/app/api/simulate/` |
| **Pagos Automatizados/Funnels** | No Iniciado | Gestión automática para links de reservas, remarketing y envíos de PDF automatizados. | (Backlog) |
| **Analítica y Retención** | No Iniciado | Paneles BI de conversiones y rastreo activo a pacientes ausentes. | (Backlog) |


## 3. Funcionalidades Completadas y Estables

- **Motor Central y Manejo de Conexiones (Webhook de Meta):**
  La integración con WhatsApp fluye eficientemente, capturando metadatos correctos de teléfono y token (verificado en modo `subscribe`). La persistencia inicial está probada y asegurada sin latencia hacia Meta.

- **Inteligencia Robusta y Orquestación Multi-Modelo:**
  El `LLMFactory` provee una transición perfecta entre las infraestructuras de OpenAI y Google. Maneja historiales complejos, injectando los retornos de las herramientas al historial. Específicamente, domina la estricta y reciente _Responses API_ para los modelos de OpenAI (limitados a temperatura `1` en O4-mini y GPT-5).

- **Ejecución Total y Real en Google Calendar:**
  A diferencia de un asistente simulado, el bot interroga el calendario real de la cuenta de servicio y parsea solapamientos entre slots locales (`america/santiago`) e inserta de forma oficial las citas (`book_appointment`, `update_appointment`, `delete_appointment`).

- **Dashboard "Human-in-the-Loop" (Intervención de Agente) y Dual-Role Visual:**
  A través de las políticas RLS y `Realtime`, el frontend permite pausas directas `bot_active=False` con un clic. La mensajería visualiza inteligentemente la orientación de las burbujas distinguiendo si el agente está en modo de prueba "Simulador Celular" o interactuando de cara a pacientes reales como un CRM estándar.

- **Filtro de Seguridad, Triaje y Escalación (Escalate to Human):**
  La aplicación identifica métricas de peligro y deriva automáticamente a clínica o invoca `escalate_to_human` cuando el usuario exige hablar con una persona. Esto detiene el responder automatizado para ese contacto y lanza una traza crítica (Push) al staff interno (loggeada simultáneamente vía Supabase a la vista de "Alertas Sistema").

- **Seguridad en Mutaciones (Google Calendar):**
  Se desarrollaron interceptores dentro del motor de IA para validar rigurosamente la identidad (número de teléfono) incrustada en las descripciones de Google Calendar antes de permitir una alteración de cita o cancelación originada por la IA, bloqueando vectores de ataque al calendario comercial.

## 4. Funcionalidades en Desarrollo (WIP)

- **Ajustes de Interfaz de Configuración:**
  La página de ajustes (`app/config/page.tsx`) ya levanta la jerarquía y expone al cliente opciones vitales de GPT y Gemini e instrucciones iniciales del `system_prompt`. Sin embargo, es un esqueleto prematuro (carece de manejo robusto de sesiones e inicialización multi-tenant gráfica más allá de recuperar el `.single()` quemado del schema).
  
- **Test de Simulación Interna:**
  Se ha introducido la ruta para simular peticiones con el prefijo "56912345678" y permitir bypass al Meta Webhook enviando peticiones fetch a `/api/simulate`. Funciones en UI instaladas pero etiquetado experimentalmente como desarrollo.

## 5. Backlog y Tareas Pendientes

- **Links de Reserva Dinámicos:** Falta inyectar conectores directos de pagos para que la Agenda requiera fondos mínimos en cuentas específicas.
- **Automatización Documental Post y Pre-Venta:** Embudos y webhooks salientes que disparen guías y FAQs en PDF (Ej. "Requisitos para cirugía") automatizados mediante cron jobs o triggers de Supabase.
- **Optimización Preventiva y Data Analysis:** Desarrollar vistas o procesos asíncronos en el backend que escaneen inactividad (Ej. Contactos sin mensaje desde > 90 días) para disparar promps en frío. Tracking del ROI basado en interacciones en el módulo Dashboard (Next.js).

## 6. Deuda Técnica y Observaciones

- **Información "Hardcodeada" / Variables Quemadas:**
  - El seed principal del `schema.sql` está inicializando registros vitales de Meta con `'123456789012345'` y `'PLACEHOLDER_TOKEN'`.
  - El simulador del frontend Next.js acopla el trigger mock a `56912345678` intencionalmente para la cuenta demo.
  - Las derivaciones del bot en el módulo de triaje encolan las alarmas un número telefónico estrictamente amarrado a `alert_phone = "+56999999999"`.
  - Las credenciales de Service Account en calendar son mapeos absolutos rudimentarios (`SERVICE_ACCOUNT_FILE = r'D:\WebDev\IA\backend\casavitacure-crm-1b7950d2fa11.json'`).

- **Reglas de Seguridad Web:**
  - FastApi `main.py` incluye CORS explícitamente vulnerable para testing: `allow_origins=["*"]`. Debe cerrarse según el deployment oficial y documentarse.

- **Refactorización Core de LLM:**
  - Dentro de `llm_router.py`, los for-loops y condicionales para inyectar los arrays del Responses API de OpenAI están altamente acoplados al comportamiento local actual de `o4` y `gpt-5`. Extender la firma para manejar decenas de herramientas externas podría romper fácilmente las estructuras restrictivas actuales requeridas.

- **Inexistencia de Testing Automatizado:** 
  Se confía fuertemente en unos cuantos scripts manuales (`check_db.py`, `debug_gpt5_tools.py`, `test_gpt5_tools.py`), pero carece total y absolutamente de test funcionales `pytest` o test de estrés integrados en una pipeline normal de validación de backend.
