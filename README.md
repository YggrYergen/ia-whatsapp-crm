# Documentación Técnica: AI WhatsApp CRM B2B (Screaming Architecture)

## 1. Visión General y Arquitectura del Sistema

El AI WhatsApp CRM es una plataforma Software as a Service (SaaS) multi-tenant diseñada para unificar, automatizar y gestionar la atención al cliente de pequeñas y medianas empresas (B2B) a través de WhatsApp. El sistema delega la primera línea de interacción a Modelos de Lenguaje Extenso (LLMs) configurables por el cliente, dotados de herramientas activas (Function Calling) para ejecutar lógicas de negocio reales, operando bajo un paradigma estricto de Human-In-The-Loop (HITL).

El sistema está compuesto por tres componentes principales distribuidos:

1.  **Frontend (React/Next.js):** Actúa como el panel de control administrativo del cliente. Proporciona una interfaz en tiempo real reactiva impulsada por websockets para monitorear conversaciones, pausar agentes de IA e intervenir manualmente. Se despliega mediante edge computing (Cloudflare Pages).
2.  **Backend (Python/FastAPI):** El núcleo de procesamiento asíncrono y orquestador de lógica de negocio. Mantiene el estado, procesa webhooks entrantes de Meta, inyecta memoria al contexto del LLM, y ejecuta las herramientas del sistema. Optimizado para entornos serverless (Google Cloud Run).
3.  **Capa de Datos y Real-time (Supabase/PostgreSQL):** Almacenamiento persistente multi-tenant con seguridad a nivel de fila (RLS). Actúa como fuente de la verdad y motor de eventos pub/sub para sincronizar el estado entre el Backend y el Frontend instantáneamente.

### Diagrama de Arquitectura de Alto Nivel

```mermaid
flowchart TD
    subgraph Ecosistema Externo
        WA[Meta WhatsApp API]
        GC[Google Calendar API]
    end

    subgraph Backend (FastAPI - Cloud Run)
        GW[API Gateway /webhook]
        Q[Background Tasks]
        Router[LLM Router Strategy]
        ToolReg[Tool Registry]
        Event[Event Bus]
        
        GW -->|200 OK Sync| WA
        GW -->|Encola Payload| Q
        Q --> Router
        Router <-->|Tools Call| ToolReg
        ToolReg --> Event
        ToolReg -->|Citas| GC
    end

    subgraph Modelos Fundacionales
        OpenAI[OpenAI gpt-4o-mini / o4-mini]
        Gemini[Google Gemini 1.5 Flash / 3.1]
        
        Router <--> OpenAI
        Router <--> Gemini
    end

    subgraph Base de Datos & Eventos
        DB[(Supabase PostgreSQL)]
        PubSub[Realtime Channels]
        
        Q <--> DB
        DB --> PubSub
    end

    subgraph Frontend (Next.js - Cloudflare Pages)
        CRM[Dashboard HITL]
        Conf[Panel Configuración]
        
        PubSub --> CRM
        CRM -->|Pausa IA| DB
        CRM -->|Intervención| DB
        Conf -->|Guarda Prompt| DB
    end
    
    Router -->|Despacha SMS final| WA
    Event -->|Notifica Staff| WA
```

---

## 2. Catálogo Exhaustivo de Características y Capacidades

El sistema actual posee las siguientes capacidades funcionales implementadas:

### Capacidades de Inteligencia Artificial
* **Orquestación Multi-LLM Dinámica:** Implementación del patrón Strategy (`LLMFactory`) que permite instanciar e intercambiar en caliente entre proveedores y modelos (ej. OpenAI GPT-4o-mini, Google Gemini Flash) basado en las preferencias almacenadas en la fila de configuración de cada *tenant*.
* **Inyección de Memoria y Sesgo de Recencia:** El sistema recupera los últimos 15 mensajes de la base de datos, construyendo el contexto conversacional. Inyecta un marcador temporal explícito ("Log Interno") en el último mensaje para dotar a la IA de conocimiento exacto sobre la fecha y hora de la interacción, mitigando alucinaciones temporales.
* **Zero-Trust System Prompting:** Inyección obligatoria de directivas a nivel de sistema que fuerzan a la IA a priorizar el reloj interno del servidor sobre su propia "memoria" generada, y restringen la alucinación de resultados exitosos cuando las herramientas (Tools) retornan errores explícitos.

### Ejecución de Herramientas (Function Calling)
A través de la clase base `AITool` y el `ToolRegistry`, el LLM puede invocar métodos asíncronos en el backend:
* **`get_merged_availability`:** Lectura simultánea y unificación (Round-Robin) de disponibilidad sobre dos calendarios de Google (Box 1 y Box 2). Limita la consulta estrictamente entre 09:00 y 19:00 horas, parseando los rangos `FreeBusy` en franjas disponibles de 30 o 60 minutos.
* **`get_my_appointments`:** Permite al sistema listar las citas futuras, bifurcando la cantidad de información entregada según el rol del remitente (RBAC). Si es un administrador (`admin`/`staff`), muestra todas las citas del día; si es un cliente, filtra devolviendo únicamente las citas asociadas al número telefónico de origen.
* **`book_round_robin`:** Inserción de eventos en Google Calendar aplicando lógica de decisión: evalúa qué box específico está libre en el bloque solicitado e inyecta la cita. Dispara un evento `system_alert` asíncrono para notificar al staff.
* **`update_appointment`:** Función compuesta atómica que ejecuta una cancelación seguida de un reagendamiento. Retorna error si el borrado original falla.
* **`delete_appointment`:** Eliminación segura (Zero-Trust). Búsqueda de eventos en todo el día especificado. Solo procede a borrar si el número de teléfono del originador coincide con el inyectado en la descripción original del evento en Google Calendar, previniendo cancelaciones maliciosas de terceros.
* **`escalate_to_human`:** Interrupción de control delegada a la IA. La IA puede decidir emitir un evento crítico al EventBus que pausará su propio comportamiento (`bot_active = False`) y notificará al personal.

### Operaciones de Negocio y Enrutamiento (Core CRM)
* **Human-In-The-Loop (HITL):** Capacidad del cliente administrador (vía Frontend) de alternar la columna booleana `bot_active` en tiempo real, bloqueando que el Backend envíe payloads al `LLMFactory`.
* **Evaluador de Triaje Clínico:** Capa de dominio (`TriageEvaluator`) con capacidad de análisis léxico crudo sobre los síntomas ingresados para detectar *keywords* de emergencia antes o en paralelo a la lógica de la IA, publicando notificaciones asíncronas de urgencia.
* **Bus de Eventos Asíncrono (`EventBus`):** Implementación de Pub/Sub en memoria (`asyncio.Queue`) que desvincula los casos de uso (ej. Agendamiento) de los efectos secundarios (ej. Notificar por WhatsApp al administrador), garantizando respuestas de red rápidas.
* **Centro de Alertas Real-Time (Tabla Dedicada):** Transición del modelo de "Chat de Sistema" a una tabla dedicada de `alerts`. Las urgencias (Triaje clínico, escalamiento humano, cancelaciones) se despachan al bus de eventos y se reflejan instantáneamente en la campana de notificaciones del dashboard del cliente, permitiendo un flujo de trabajo centralizado y salto directo al chat afectado para su resolución.
* **Debouncing Cognitivo Eficiente (Mutex Lock):** El sistema implementa un patrón de bloqueo seguro a nivel de base de datos (`is_processing_llm`) para manejar usuarios "metralleta" (múltiples mensajes en segundos). Los webhooks subsecuentes detectan el candado, devuelven 200 OK a Meta y mueren silenciosamente sin detonar el LLM. La tarea principal consolida todo el bloque de mensajes acumulados durante la ventana antes de la inferencia, garantizando cero desperdicio de tokens y cómputo.
* **Inyección Dinámica de Contexto:** El orquestador extrae los metadatos del CRM (`status`, `role`, `name`) de la base de datos y los inyecta en el *System Prompt* en tiempo de ejecución. Esto otorga a la IA conciencia situacional instantánea (ej. sabe si habla con un lead nuevo o un cliente recurrente) sin incurrir en complejas búsquedas vectoriales (RAG).

---

## 3. Topología del Proyecto (Screaming Architecture)

La base de código abandona el patrón tradicional MVC para adoptar la Screaming Architecture (basada en principios de Domain-Driven Design y Puertos/Adaptadores). La estructura de directorios comunica inmediatamente las intenciones del negocio, separando estrictamente los detalles tecnológicos (Frameworks, DBs) de la lógica transaccional.

```text
Backend/app/
├── api/                  # Puertos de Entrada: Dependencias inyectables de FastAPI.
│   └── dependencies.py   # Extracción y validación del TenantContext desde el webhook.
│
├── core/                 # Configuración universal y primitivas del sistema.
│   ├── config.py         # Variables de entorno (Pydantic Settings).
│   ├── event_bus.py      # Motor central asíncrono pub/sub.
│   ├── exceptions.py     # Errores de dominio tipados.
│   ├── models.py         # DTOs base (ej. TenantContext).
│   └── security.py       # Validadores criptográficos de Meta.
│
├── infrastructure/       # ADAPTADORES (Detalles Tecnológicos): Nada de lógica de negocio aquí.
│   ├── calendar/         # SDK de Google.
│   ├── database/         # Singleton de Supabase y repositorios genéricos.
│   ├── llm_providers/    # Adaptadores concretos (OpenAI SDK, Gemini SDK).
│   ├── messaging/        # Clientes HTTPX puros (Meta Graph API).
│   └── telemetry/        # Configuración de logs asíncronos y colas de impresión.
│
├── modules/              # CASOS DE USO (Screaming Architecture): El corazón del negocio.
│   ├── clinical_triage/  # Lógica de evaluación médica.
│   ├── communication/    # Recepción de webhooks, verificación HITL y orquestación general.
│   ├── intelligence/     # Estrategia LLM, Factory Pattern, y Registro de Herramientas.
│   └── scheduling/       # Reglas de negocio de agendamiento (Overlap, Round-Robin).
│
└── main.py               # Application Factory: Unifica módulos, registra herramientas y arranca uvicorn.
```

### Reglas Arquitectónicas Críticas (Inviolables)

1.  **Regla de Dependencia Unidireccional:** Ningún archivo dentro de `app/modules/` (Lógica de Dominio) puede importar código de frameworks web específicos de `app/infrastructure/` a menos que sea a través de interfaces (ej. clases Abstractas) u objetos pre-instanciados pasados como dependencia (Inversion of Control).
2.  **Aislamiento de Fast Routing:** Los enrutadores (`routers.py`) están prohibidos de contener declaraciones `if/else` relacionadas con el negocio. Su única responsabilidad es recibir el stream `Body(...)`, inyectar dependencias y transferir el payload a `use_cases.py` (Background Tasks) respondiendo instantáneamente al emisor externo.
3.  **Expansión mediante Registro (OCP):** Agregar un nuevo modelo de inteligencia no debe modificar `use_cases.py`. Se debe crear un adaptador en `infrastructure/llm_providers/` y registrarse en `main.py` mediante `LLMFactory.register_strategy()`. Idéntico procedimiento aplica para herramientas de IA mediante el `ToolRegistry`.
4.  **Desacoplamiento Operativo:** Todo efecto secundario (envío de notificaciones, registro en sistemas paralelos) resultado de un proceso primario debe emitirse a través del `EventBus`, liberando el ciclo de ejecución de la corrutina principal.


## 4. Modelo de Datos y Multi-tenancy

El sistema está diseñado fundamentalmente como una plataforma multi-tenant (SaaS B2B). La arquitectura de datos impone que toda operación de lectura/escritura (I/O) esté estrictamente limitada a las fronteras del negocio que la invoca, garantizando aislamiento de datos criptográfico y lógico entre los distintos clientes (ej. Muebles Nagu vs CasaVitaCure).

La persistencia de datos y el motor de eventos en tiempo real son manejados por **Supabase (PostgreSQL)**.

### Aislamiento de Datos Criptográfico (Row Level Security - RLS)

La base de datos delega la protección de acceso a las políticas RLS nativas de PostgreSQL. El acceso público anónimo a las tablas está prohibido en el diseño final (requiriendo JWT). 

* **Identidad Transaccional:** El identificador principal para enrutar el tráfico entrante de Meta no es un nombre de usuario, sino el `phone_number_id` (`ws_phone_id` en BD), un token UUID inmutable emitido por Facebook asociado a cada número de WhatsApp.
* **Cascada Multi-tenant:** Toda fila insertada en las tablas hijas (`contacts`, `messages`) exige referenciar obligatoriamente el `tenant_id` de la tabla madre (`tenants`).

### Esquema Relacional Base

1.  **Tabla `tenants` (Clientes del SaaS)**
    * **Rol:** Nodo raíz de aislamiento y almacén de configuraciones operativas.
    * **Columnas Clave:**
        * `id` (UUID): Primary Key.
        * `ws_phone_id` (Text/Unique): ID único de Meta para enrutar webhooks.
        * `llm_provider` (Text): Ej. 'openai' o 'gemini'.
        * `llm_model` (Text): Ej. 'gpt-4o-mini' o 'gemini-1.5-flash'.
        * `system_prompt` (Text): Comportamiento de IA inyectado.

2.  **Tabla `contacts` (Usuarios Finales / Leads)**
    * **Rol:** Identificación de pacientes/clientes finales por número telefónico.
    * **Índices:** Mantiene un índice compuesto único en `[tenant_id, phone_number]` para evitar colisiones de pacientes entre distintas clínicas.
    * **Columnas Clave:**
        * `bot_active` (Boolean): Bandera crítica (Kill-switch) manejada por el Frontend. Si es `false`, el Backend suspende inmediatamente el enrutamiento al LLM, logrando el Human-In-The-Loop.
        * `role` (Text): Implementación RBAC estático ('cliente', 'staff', 'admin') usado para bifurcar la visibilidad de información sensible dentro de las Tools de la IA (Ej. `CheckMyAppointmentsTool`).

3.  **Tabla `messages` (Historial Transaccional)**
    * **Rol:** Almacenamiento conversacional y detonador de eventos Real-time (vía `pg_publication`).
    * **Columnas Clave:**
        * `sender_role` (Text): Diferencia entre 'user' (cliente), 'assistant' (IA), 'human_agent' (staff manual) y 'system_alert' (Alertas urgentes).

### Flujo del `TenantContext`
A nivel de aplicación (FastAPI), la abstracción multi-tenant se logra instanciando el modelo Pydantic `TenantContext` en la puerta de enlace (`dependencies.py`). Una vez extraído el `ws_phone_id` del payload de Meta, se consulta el Tenant y este objeto fluye unidireccionalmente hacia las Background Tasks, el `LLMFactory` y el `ToolRegistry`, erradicando el uso de variables globales o configuraciones estáticas.

---

## 5. Flujo de Control Principal (El Ciclo de Vida del Webhook)

El sistema procesa la ingestión de datos de Meta de forma asíncrona y orquestada para evadir los límites de tiempo de inactividad restrictivos impuestos por los servidores de WhatsApp.

1.  **Recepción y Aceptación Temprana (API Gateway):**
    El endpoint de FastAPI (`POST /webhook`) lee el stream de bytes una única vez utilizando `payload: dict = Body(...)`. Esta estrategia elude los bloqueos internos de consumo asíncrono (HTTP 500 Stream Consumed). El sistema responde inmediatamente `HTTP 200 OK` (JSON {"status": "enqueued"}) a Meta, finalizando la conexión TCP.
2.  **Resolución de Contexto:**
    La inyección de dependencias invoca `get_tenant_context_from_payload`. Parseando el JSON anidado, extrae el `phone_number_id` y ejecuta una llamada HTTP síncrona a Supabase aislada mediante `await asyncio.to_thread(...)` previniendo la congelación del Event Loop. Se instancia el `TenantContext`.
3.  **Orquestación en Segundo Plano:**
    FastAPI lanza `ProcessMessageUseCase.execute` a la cola de `BackgroundTasks`.
    * *Verificación HITL:* Consulta la bandera `bot_active` del contacto en Supabase (creándolo si no existe). Si el bot está en pausa manual, el flujo termina silenciosamente.
    * *Sincronización Inbound:* Inserta el mensaje del usuario en la tabla `messages` para detonar la renderización inmediata en el Frontend (Supabase Real-time).
4.  **Inyección de Memoria y RAG Lineal:**
    Extrae los últimos 15 mensajes del contacto, los invierte cronológicamente, e inyecta la hora actual chilena del servidor mediante el *System Prompt* y un marcador temporal en el último mensaje del usuario para cimentar el contexto del modelo y prevenir "Alucinaciones Temporales".
5.  **Inferencia LLM y Bucle de Función:**
    * El `LLMFactory` instancía la estrategia dinámicamente según la preferencia del Tenant.
    * El modelo ejecuta una inferencia. Si determina invocar herramientas, el `tool_registry` entra en acción, capturando las respuestas e inyectándolas recursivamente al historial del modelo para una segunda pasada de síntesis lógica ("Observation Loop").
6.  **Despacho y Sincronización Outbound:**
    La cadena de texto final producida por el modelo es insertada en la tabla `messages` (con `sender_role="assistant"`) e inmediatamente lanzada por un socket de red mediante `httpx.AsyncClient` hacia la Meta Graph API para su entrega física al dispositivo del usuario final.

---

## 6. Sistema de Inteligencia y Herramientas (Tool Registry)

La arquitectura abstrae completamente las interacciones de herramientas, permitiendo añadir capacidades infinitas (ej. Búsqueda SQL de inventario, integraciones con ERPs, calculadoras de envío) sin alterar los bucles recursivos del LLM en `use_cases.py`.

### Arquitectura de Registro (Tool Vault)
Basado fuertemente en los principios SOLID (Open/Closed Principle), el motor utiliza un patrón de Registro Global:
1.  **Abstracción `AITool`:** Toda herramienta debe heredar obligatoriamente de la clase abstracta `AITool` (ubicada en `app/modules/intelligence/tools/base.py`). Exige la declaración de un método `get_schema()` para construir el JSON Schema específico del proveedor (OpenAI vs Gemini) y un método asíncrono `execute(**kwargs)` para inyectar la lógica de negocio real.
2.  **`ToolRegistry` Singleton:** Inicializado durante el `lifespan` de FastAPI, captura y acopla las instancias de las herramientas (`tool_registry.register(CheckAvailabilityTool())`).
3.  **Inyección de Contexto Mágico:** Al ejecutar una herramienta dictada por el LLM, el `use_cases.py` inyecta en los `**kwargs` metadatos críticos (`tenant_context`, `caller_phone`, `caller_role`) independientemente de si el modelo los suministró o no, facilitando auditorías de seguridad granulares (Zero-Trust).

### Catálogo de Herramientas Implementadas
Ubicadas en `app/modules/scheduling/tools.py`:

* **`CheckAvailabilityTool`:** Llama a `SchedulingService.check_availability`. Devuelve los *slots* limpios extraídos de Google Calendar para las franjas horarias configuradas.
* **`CheckMyAppointmentsTool`:** Llama a `SchedulingService.get_appointments`. Integra lógica RBAC evaluando el `caller_role`.
* **`BookAppointmentTool` / `UpdateAppointmentTool` / `DeleteAppointmentTool`:** Orquestan I/O contra Google Calendar. En el caso de borrado (`DeleteAppointmentTool`), si el emisor no es staff, restringe forzosamente el `target_phone` al número del celular originador para asegurar inmutabilidad e imposibilidad de vandalismo por terceros en la base de datos de reservas.
* **`EscalateHumanTool`:** Detiene la automatización modificando el flag `bot_active=False` a nivel de base de datos e invoca una alerta asíncrona del sistema.

### Tolerancia a Fallos de Herramientas
El registro captura excepciones profundas surgidas de la ejecución (ej. colapso de una API externa, error 500 de Google). Si una herramienta falla, el bloque `try/except` en el `ToolRegistry` interviene, neutralizando la traza de la pila y devolviendo forzosamente una respuesta JSON estandarizada de error (`{"status": "error", "message": "Internal execution error"}`). 
El sistema inyecta este fallo como *Tool Observation* (Observación de Herramienta) para el LLM, apalancándose en el Prompt Fuerte para obligar al modelo a notificar al usuario sobre la avería en vez de alucinar un resultado afirmativo (Manejo de Alucinación por Complacencia).

## 7. Despliegue, Configuración y Operaciones

El proyecto está diseñado para operar en entornos *serverless* altamente escalables y de cobro por uso (Google Cloud Run para el Backend y Cloudflare Pages para el Frontend). El determinismo en los despliegues está garantizado mediante Docker y validación estricta de variables de entorno mediante `pydantic-settings`.

### Variables de Entorno (.env)
El sistema requiere inyección explícita de secretos. En producción, estos deben inyectarse a través de un Secret Manager (GCP Secrets o similares) y no guardarse en el contenedor.

#### Backend (FastAPI)
```env
# Operacionales
ENVIRONMENT=development        # O 'production'. Determina el formateador de logs.
LOG_LEVEL=DEBUG                # 'INFO', 'WARNING' o 'ERROR' en producción para ahorrar ciclos CPU.
MOCK_LLM=False                 # 'True' anula llamadas a la API ahorrando cuota en dev.

# Autenticación Meta
WHATSAPP_VERIFY_TOKEN=abc123   # Token estático para validar la creación del webhook.

# Inteligencia Artificial
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=AIza...

# Base de Datos Administrativa (Bypassea RLS en el Backend)
SUPABASE_URL=https://<tu-id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=ey...
```

#### Frontend (Next.js)
El prefijo `NEXT_PUBLIC_` es obligatorio para exponer estas variables al cliente en tiempo de compilación.
```env
NEXT_PUBLIC_SUPABASE_URL=https://<tu-id>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=ey... # Llave anónima restringida por RLS.
```

### Contenedorización y Docker Build
El Backend utiliza un *Build Multi-stage* (`deploy/Dockerfile`) para mantener la imagen final estéril, segura y con una huella de memoria reducida.
1.  **Stage Builder:** Instala `poetry`, `uv` y compila las dependencias en un entorno virtual aislado (`/opt/venv`).
2.  **Stage Runner:** Crea un usuario no-root (`crmuser`), copia exclusivamente el código fuente y el entorno virtual compilado. Descarta las herramientas de compilación para reducir vulnerabilidades.

Comando de despliegue local:
```bash
docker-compose -f deploy/docker-compose.yml up --build
```

### Concurrencia Dinámica en Google Cloud Run
El comando `CMD` del `Dockerfile` está diseñado elásticamente:
```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --no-access-log"]
```
* **Asignación de Puertos:** Cloud Run inyecta la variable `$PORT` (usualmente 8080) de forma dinámica. El fallback `:-8000` asegura el funcionamiento local.
* **Optimización de Memoria (Workers):** Si se despliega en un contenedor de bajo cómputo (ej. 1 vCPU), levantar múltiples *workers* genera *Context Switching*, colapsando la memoria RAM. El contenedor por defecto arranca con `1` worker, modificable inyectando la variable `WEB_CONCURRENCY` a nivel de orquestador (Fórmula sugerida: `2 x Nucleos + 1`).
* **Supresión de Ruido I/O:** El flag `--no-access-log` evita que Uvicorn escriba en disco cada ping exitoso `200 OK` de Meta, ahorrando cuota de ingesta en Google Cloud Logging.

### Sistema de Telemetría Asíncrona (`logger_service.py`)
El módulo de logging evita los bloqueos de hilos (Thread-blocking) comunes en aplicaciones síncronas.
* **Modo Development (`ENVIRONMENT=development`):** Imprime logs en consola mediante un `StreamHandler` con colores y tracebacks completos (`exc_info=True` propagado), esencial para depuración del ciclo de LLMs.
* **Modo Producción (`ENVIRONMENT=production`):** Desvía los logs a un `logging.handlers.QueueHandler`, permitiendo que el Event Loop de FastAPI continúe de inmediato. Un hilo en segundo plano consume la cola, renderizando un formato JSON rígido a través de `orjson` nativo, garantizando su ingestión limpia en sistemas APM (Datadog, GCP Cloud Logging).

---

## 8. Estado de Implementación y Roadmap

Esta matriz define el estado actual del proyecto de cara a su transformación en un SaaS multi-tenant comercial, diferenciando la deuda técnica superada de los requisitos operacionales pendientes.

### A. Cumplido (Deuda Técnica Estructural)
| Característica / Módulo | Estado | Descripción |
| :--- | :--- | :--- |
| **Screaming Architecture** | ✅ Completado | Separación estricta de dominios (Infraestructura vs Casos de Uso). Código legible y escalable. |
| **Resolución de Body en Webhook** | ✅ Completado | Inyección `Body(...)` en FastAPI, previniendo colapsos asíncronos y garantizando concurrencia. |
| **Protección I/O Bloqueante** | ✅ Completado | `asyncio.to_thread` envuelve operaciones de base de datos evitando la congelación del Event Loop. |
| **Logging de Alto Rendimiento** | ✅ Completado | Logs estructurados JSON asíncronos para producción, logs legibles con traceback en local. |
| **Connection Pooling (Meta)** | ✅ Completado | Cliente efímero para BD que erradica timeouts HTTP/2 y cliente estático para Meta Graph API. |
| **Autenticación SSO Frontend** | ✅ Completado | Supabase Auth (Google Login) integrado en Next.js. El Dashboard valida sesiones. |
| **Rate Limiting Defensivo** | ✅ Completado | Integración de `slowapi` restringiendo el webhook frente ataques/Spam. |
| **Seguridad de Secretos (GCP)** | ✅ Completado | Llaves de LLMs, Meta y base64 de Google Calendar aisladas en Google Secret Manager. Eliminadas del entorno estático. |

### B. Backlog Crítico (Transición a SaaS - P0 y P1)
| Característica / Requerimiento | Prioridad | Descripción y Plan de Acción |
| :--- | :--- | :--- |
| **Mocking UI Nivel Enterprise** | 🚨 **P0** (Bloqueante) | Implementar Layout estructurado (Sidebar, TopNav) con vistas simuladas para Dashboard principal, Agenda y Pacientes, aislando la interactividad real solo en 'Chats' y 'Configuración' para elevar el valor percibido del cliente. |
| **Debouncing Mutex (Mensajes Múltiples)** | 🚨 **P0** (Bloqueante) | Implementar bandera de bloqueo (`is_processing_llm`) en Supabase. Consolidar ráfagas de mensajes del usuario en una sola llamada al LLM utilizando el patrón de Lock en `ProcessMessageUseCase` para optimizar tokens y UX. |
| **Conciencia de Contexto (Inyección en Prompt)** | 🚨 **P0** (Bloqueante) | Extraer metadatos de la tabla `contacts` (estado, rol, nombre) e inyectarlos dinámicamente en la instrucción del sistema antes de invocar a `LLMFactory`. |
| **Sistema de Alertas Real-time (Campana)** | ⚡ **P1** (Escalabilidad) | Finalizar reemplazo del contacto fantasma "Alertas Sistema" por la tabla `alerts`. Implementar suscripción WebSocket en el Navbar del Frontend para notificaciones accionables. |
| **Caché en Memoria del TenantContext** | ⚡ **P1** (Escalabilidad) | Implementar librería `cachetools` en `dependencies.py` (TTL de 5 min) para evitar consultar Supabase en cada uno de los cientos de webhooks por minuto. |

### C. Plataforma SuperAdmin y FinOps (Deuda Técnica - P2)
*Actualmente pendiente de desarrollo robusto en backend para control comercial y rentabilidad.*
| Característica / Requerimiento | Prioridad | Descripción y Plan de Acción |
| :--- | :--- | :--- |
| **Telemetría de Consumo LLM (FinOps)** | 💰 **P2** (Comercial) | Modificar el DTO `LLMResponse` para capturar `prompt_tokens` y `completion_tokens`. Emitir evento asíncrono para guardar en nueva tabla `tenant_billing_logs` calculando el costo en USD por petición y por cliente. |
| **Panel de Control SuperAdmin** | 💰 **P2** (Comercial) | Vista maestra protegida por RLS estricto. Permite ver el margen de ganancia por clínica (Costo Tokens vs Suscripción Mensual) y activar un "Kill-Switch" (`is_active=False`) para clínicas morosas, cortando su webhook. |
| **Políticas RLS Vinculantes (DB)** | 🔧 **P3** (Optimización) | Eliminar las políticas `Allow public...` actuales en la Base de Datos. Reescribir RLS utilizando la función `auth.uid()` acoplada a la tabla de privilegios `tenant_users`. |