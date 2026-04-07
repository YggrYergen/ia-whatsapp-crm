# Roadmap Técnico: IA WhatsApp CRM — Plan de Implementación Definitivo

Plan de acción estructurado para el lanzamiento con Meta, optimización de recursos, minimización de latencia y construcción de una base escalable para los próximos 10 clientes.

---

> [!IMPORTANT]
> ## 📊 Estado Actual del Proyecto — 6 de Abril 2026
>
> | Fase | Estado | Detalle |
> |------|--------|---------|
> | **Fase 0** — Lanzamiento Crítico | ✅ **COMPLETADA** | RLS restrictivo (12 políticas), Singleton Google Calendar, `asyncio.gather()` en webhook, `min-instances=1` en Cloud Run, backend desplegado y operativo |
> | **Fase 1.1** — CRM y Frontend | 🔄 **EN EJECUCIÓN** | Conectar `PacientesView` a Supabase, desacoplar `CrmContext`, hand-off humano |
> | **Fase 1.2** — Calendarios Multi-Tenant | 🔄 **EN EJECUCIÓN** | OAuth 2.0 de Google, UI de autorización |
> | **Fase 1.3** — Logging y Excepciones | 🔄 **EN EJECUCIÓN** | Integrar Sentry (Backend + Frontend), alertas por email |
> | **Fase 1.4** — Alertas Híbrido | ⏳ Pendiente | — |
> | **Fase 2** — Eficiencia IA | ⏳ Pendiente | — |
> | **Fase 3** — FinOps y Escala | ⏳ Pendiente | — |
>
> **🎯 Objetivo actual:** Completar Fases 1.1 → 1.3 (CRM con datos reales, contextos desacoplados, Sentry con alertas por email). Luego testear todo end-to-end y conectar con Meta WhatsApp Business.
>
> **🏗️ Infraestructura activa:**
> - Backend: `https://ia-backend-prod-645489345350.europe-west1.run.app` (Cloud Run, `min-instances=1`)
> - DB: Supabase producción (`nemrjlimrnrusodivtoa`) con RLS habilitado
> - Frontend: Next.js 14 + TailwindCSS + shadcn

---

## Fase 0: Lanzamiento Crítico (Próximas 24 horas)

**Objetivo:** Obtener la aprobación de Meta, proteger la infraestructura y asegurar una experiencia fluida sin cuelgues del servidor para la primera clienta.

---

### 0.1 — Seguridad y Aislamiento (Bloqueante)

#### 0.1.1 — Eliminar políticas de acceso público
- Auditar todas las tablas de Supabase que tengan políticas RLS con `USING (true)`.
- Eliminar (`DROP POLICY`) cada una de esas políticas permisivas.
- Verificar que tras la eliminación, las consultas anónimas devuelvan `0 rows` o error `403`.

#### 0.1.2 — Implementar RLS restrictivo por tenant
- Crear nuevas políticas de `SELECT`, `INSERT`, `UPDATE` y `DELETE` en cada tabla relevante.
- La condición de cada política debe validar: `auth.uid()` pertenece al tenant y `tenant_id = (SELECT tenant_id FROM profiles WHERE id = auth.uid())`.
- Verificar que un usuario del Tenant A **no** pueda leer ni escribir datos del Tenant B.
- Documentar las políticas aplicadas en un archivo de referencia.

---

### 0.2 — Mitigación de Latencia Core

#### 0.2.1 — Configurar `min-instances=1` en Cloud Run
- Editar la configuración del servicio de Cloud Run para establecer `--min-instances=1`.
- Redesplegar el servicio con la nueva configuración.
- Verificar que el cold start de ~120s quede eliminado realizando un request tras un periodo de inactividad.

#### 0.2.2 — Refactorizar `google_client.py` (Singleton + async)
- Refactorizar la instanciación del cliente de Google Calendar como un **Singleton** a nivel de módulo para evitar reconstruir credenciales en cada request.
- Envolver todas las llamadas síncronas de la API de Google dentro de `asyncio.to_thread()` para no bloquear el event loop de FastAPI.
- Validar que el event loop no se bloquea durante llamadas al calendario ejecutando requests concurrentes de prueba.

#### 0.2.3 — Paralelizar operaciones de Supabase en el webhook
- Identificar las operaciones de lectura/escritura secuenciales dentro del handler del webhook de WhatsApp.
- Agrupar las operaciones independientes con `asyncio.gather()`.
- Medir la reducción de tiempo total del webhook antes/después de la paralelización.

---

### 0.3 — Conexión Meta API

#### 0.3.1 — Verificación de webhooks de Meta
- Configurar el endpoint de verificación (`GET`) con el token de verificación correspondiente.
- Confirmar que Meta valida el webhook exitosamente desde el panel de la app de Facebook Developers.

#### 0.3.2 — Despliegue del flujo de mensajería entrante/saliente
- Implementar el handler para mensajes entrantes (`POST` webhook) que reciba, parsee y procese los mensajes de WhatsApp.
- Implementar el envío de respuestas salientes vía la API de WhatsApp Business Cloud.
- Verificar el flujo completo enviando un mensaje de prueba y confirmando la respuesta del bot.
- Preparar la documentación del flujo para la auditoría de Meta.

---

## Fase 1: Estabilización Operativa y Multi-Tenant (Semanas 1-2)

**Objetivo:** Habilitar al equipo médico y preparar la entrada de nuevos clientes reduciendo el trabajo manual.

---

### 1.1 — CRM y Rendimiento del Frontend

#### 1.1.1 — Conectar la vista de Pacientes a Supabase
- Crear o ajustar la query a la tabla `patients` / `contacts` en Supabase para obtener datos reales.
- Renderizar la tabla con columnas: nombre, última visita, estado, valor del cliente (LTV) y resumen del perfil clínico.
- Implementar paginación o *infinite scroll* para manejar volúmenes grandes de datos.

#### 1.1.2 — Desacoplar el estado global (Context splitting)
- Analizar el `CrmContext` actual e identificar qué datos provocan re-renders innecesarios.
- Dividir `CrmContext` en contextos más pequeños y especializados:
  - `AuthContext` — sesión del usuario, tokens, permisos.
  - `ChatContext` — mensajes activos, estado de la conversación.
  - `UIContext` — estados de la interfaz (sidebars, modales, loading).
- Migrar los componentes consumidores a los nuevos contextos.
- Verificar que teclear un mensaje en el chat no congele la lista de pacientes ni los otros paneles.

#### 1.1.3 — Conectar Hand-off humano
- Implementar la funcionalidad para que el staff envíe mensajes desde el dashboard directo al WhatsApp del paciente cuando la IA esté pausada.
- El operador debe poder ver el indicador de "IA pausada" y tomar el control de la conversación.
- Los mensajes enviados por el humano deben registrarse en la misma tabla de `messages` con `sender_type = 'staff'`.
- Al reactivar la IA, esta debe retomar el contexto de la conversación incluyendo los mensajes humanos.

---

### 1.2 — Automatización de Calendarios (Multi-Tenant)

#### 1.2.1 — Implementar flujo OAuth 2.0 de Google
- Crear un endpoint en el backend (`/api/google/auth`) que inicie el flujo OAuth 2.0 de Google con los scopes necesarios (`calendar.events`, `calendar.readonly`).
- Implementar el callback (`/api/google/callback`) que reciba el `authorization_code`, lo intercambie por tokens y almacene el `refresh_token`.
- Encriptar el `refresh_token` antes de almacenarlo en Supabase (usando AES-256 o similar), asociado al `tenant_id`.

#### 1.2.2 — UI de autorización en la configuración del tenant
- Crear un botón "Conectar Google Calendar" en el panel de configuración del tenant.
- Mostrar el estado de conexión: conectado/desconectado, email asociado, último sync.
- Permitir desconectar (revocar el token) desde la UI.

---

### 1.3 — Sistema de Logging y Manejo de Excepciones

#### 1.3.1 — Integrar Sentry en FastAPI (Backend)
- Instalar el SDK de Sentry para Python (`sentry-sdk[fastapi]`).
- Configurar la inicialización con el DSN, environment (`production`/`staging`), y release version.
- Configurar el `traces_sample_rate` para performance monitoring.
- Añadir `tenant_id` y `user_id` como tags personalizados en cada evento.
- Verificar que errores no capturados generen reportes en el dashboard de Sentry.

#### 1.3.2 — Integrar Sentry en Next.js (Frontend)
- Instalar `@sentry/nextjs`.
- Configurar `sentry.client.config.ts` y `sentry.server.config.ts`.
- Envolver la app con el error boundary de Sentry.
- Verificar que errores de frontend se reporten correctamente.

#### 1.3.3 — Configurar alertas en Sentry
- Configurar alertas por email y/o Slack para errores críticos (500, excepciones no manejadas).
- Definir reglas de agrupación de errores para evitar spam de notificaciones.

---

### 1.4 — Sistema de Alertas Híbrido

#### 1.4.1 — Notificaciones in-app para el staff médico
- Implementar notificaciones del navegador (Web Notifications API) con sonido para eventos críticos (nuevo paciente, cita cancelada, handoff requerido).
- Crear un componente de notificaciones en el dashboard que muestre un feed de alertas en tiempo real.
- Utilizar Supabase Realtime para empujar las notificaciones al frontend.

#### 1.4.2 — Notificaciones por correo electrónico
- Implementar un servicio de envío de emails (ej. Resend, SendGrid, o Supabase Edge Functions + SMTP) para alertas críticas.
- Crear templates de email para: nueva cita, cancelación, handoff requerido, alerta del sistema.
- Permitir al staff configurar qué alertas recibe por email en su perfil.

#### 1.4.3 — Evaluar Template Messages de WhatsApp para alertas
- Revisar la *Service Window* de Meta de 24 horas para mensajes proactivos.
- Diseñar y registrar *Template Messages* en Meta para alertas al staff fuera de la ventana de servicio.
- Evaluar el costo transaccional por mensaje y documentarlo para la toma de decisiones.
- Implementar la lógica condicional: usar mensaje directo si está dentro de la ventana, template si está fuera.

---

## Fase 2: Eficiencia de IA y Experiencia de Usuario (Semanas 2-4)

**Objetivo:** Optimizar el costo computacional de la IA y mejorar radicalmente la percepción de velocidad.

---

### 2.1 — Respuestas en Etapas (Streaming UX)

#### 2.1.1 — Implementar mensajes de acuse de recibo
- Detectar en el flujo del LLM cuándo se va a invocar una herramienta (tool call) que implica latencia (ej. buscar horas disponibles en Google Calendar).
- Antes de ejecutar la herramienta, enviar un mensaje intermedio al paciente vía WhatsApp: *"Perfecto, dame un segundo mientras reviso la agenda..."* (o un mensaje configurable por tenant).
- Asegurar que el mensaje intermedio se envía **inmediatamente** sin esperar el resultado de la herramienta.

#### 2.1.2 — Flujo asíncrono de tool calls
- Reestructurar el handler del webhook para que:
  1. Reciba el mensaje.
  2. Invoque el LLM.
  3. Si el LLM devuelve un tool call → envíe el acuse de recibo → ejecute la herramienta → invoque al LLM de nuevo con el resultado → envíe la respuesta final.
  4. Si no hay tool call → envíe la respuesta directamente.
- Medir la latencia percibida por el paciente antes y después de implementar este flujo.

---

### 2.2 — Routing Dinámico de Modelos

#### 2.2.1 — Clasificación de complejidad del mensaje
- Implementar un clasificador ligero (basado en reglas o un modelo ultra-pequeño) que categorice cada mensaje entrante en:
  - **Simple**: saludos, confirmaciones, preguntas de FAQ, agendamientos directos.
  - **Complejo**: triaje clínico avanzado, quejas, consultas médicas que requieren razonamiento profundo.

#### 2.2.2 — Router de modelos
- Configurar un mapa de modelos por nivel de complejidad:
  - Simple → Gemini Flash / GPT-4o-mini (rápido y barato).
  - Complejo → GPT-4o / Gemini Pro (más lento, más capaz).
- Hacer el mapa configurable por tenant (algunos pueden querer siempre el modelo premium).
- Registrar en `usage_logs` qué modelo se usó para cada interacción.

#### 2.2.3 — Fallback y monitoreo
- Implementar fallback: si el modelo rápido falla o su respuesta tiene baja confianza, re-enviar al modelo complejo.
- Crear métricas de distribución de uso por modelo para análisis FinOps.

---

## Fase 3: FinOps, Monetización y Escala (Semanas 4-8)

**Objetivo:** Preparar la infraestructura comercial para onboarding autónomo de nuevos clientes.

---

### 3.1 — Pasarela de Pagos (Stripe)

#### 3.1.1 — Integración de Stripe Checkout
- Crear una cuenta Stripe y configurar productos/precios para los planes de suscripción.
- Implementar un endpoint `/api/stripe/checkout` que genere una sesión de Stripe Checkout para el tenant.
- Implementar el webhook de Stripe (`/api/stripe/webhook`) para procesar eventos: `checkout.session.completed`, `invoice.paid`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`.
- Almacenar el `stripe_customer_id` y `stripe_subscription_id` en la tabla de `tenants`.

#### 3.1.2 — Implementar Metered Billing (facturación por uso)
- Configurar un precio *metered* en Stripe para los créditos/tokens de IA.
- Cada vez que se procese una interacción de IA, reportar el uso a Stripe via `stripe.subscription_items.create_usage_record()`.
- Permitir al tenant ver su consumo actual desde el dashboard.

---

### 3.2 — Tracking Preciso de Cómputo

#### 3.2.1 — Crear la tabla `usage_logs`
- Crear la tabla en Supabase con las siguientes columnas:
  - `id` (UUID, PK)
  - `tenant_id` (FK a tenants)
  - `conversation_id` (FK a conversations)
  - `model_used` (text — ej. `gpt-4o-mini`, `gemini-flash`)
  - `prompt_tokens` (integer)
  - `completion_tokens` (integer)
  - `total_tokens` (integer)
  - `estimated_cost_usd` (numeric)
  - `created_at` (timestamptz)
- Aplicar RLS por `tenant_id`.

#### 3.2.2 — Interceptar metadatos de tokens
- Tras cada llamada al LLM (OpenAI/Gemini), extraer los metadatos de uso: `prompt_tokens`, `completion_tokens`, modelo utilizado.
- Calcular el costo estimado basándose en la tabla de precios del proveedor (configurable).
- Insertar un registro en `usage_logs` con todos los datos.

#### 3.2.3 — Dashboard de consumo
- Crear una vista en el frontend que muestre al administrador del tenant:
  - Consumo acumulado del mes (tokens y costo estimado en USD).
  - Desglose por modelo.
  - Gráfico de tendencia diaria.
  - Porcentaje del límite consumido.

---

### 3.3 — Control de Acceso y Suscripciones

#### 3.3.1 — Middleware de validación de suscripción
- Crear un middleware en FastAPI que, antes de procesar cada mensaje de WhatsApp:
  1. Consulte el estado de suscripción del tenant (`active`, `past_due`, `canceled`, `trialing`).
  2. Consulte si el tenant ha excedido su límite mensual de tokens/créditos.
  3. Si la suscripción está inactiva o el límite excedido → **pausar** el procesamiento del LLM.

#### 3.3.2 — Notificación al administrador
- Cuando se detecte una suscripción inactiva o límite excedido:
  - Enviar un email automático al administrador de la clínica informando la situación.
  - Mostrar un banner de alerta en el dashboard del CRM.
  - Registrar el evento en un log de auditoría.

#### 3.3.3 — Respuesta fallback al paciente
- Cuando el LLM esté pausado por motivos de suscripción, responder al paciente con un mensaje genérico configurable: *"Gracias por tu mensaje. En este momento nuestro sistema está en mantenimiento. Por favor comunícate directamente al [teléfono de la clínica]."*
- El mensaje de fallback debe ser configurable por tenant.

---

## Verificación General

### Automatizada
- **Fase 0**: Test de regresión de RLS con consultas cross-tenant. Health check del webhook de Meta. Test de latencia del cold start con `min-instances=1`.
- **Fase 1**: Tests de integración del flujo OAuth de Google. Tests de renderización de la tabla de pacientes. Test de entrega de mensajes hand-off.
- **Fase 2**: Benchmark de latencia percibida con/sin acuse de recibo. Test unitario del clasificador de complejidad. Test de fallback del router de modelos.
- **Fase 3**: Test del webhook de Stripe con eventos simulados. Test de inserción en `usage_logs`. Test del middleware de suscripción con tenant excedido.

### Manual
- **Fase 0**: Enviar mensaje de WhatsApp real y verificar respuesta end-to-end. Confirmar en el panel de Meta que el webhook está verificado.
- **Fase 1**: Un operador del staff envía un mensaje manual desde el dashboard y el paciente lo recibe en WhatsApp. El administrador conecta Google Calendar vía OAuth.
- **Fase 2**: El usuario envía un mensaje que requiere búsqueda en calendario y recibe el acuse de recibo antes de la respuesta final.
- **Fase 3**: El administrador completa un checkout de Stripe y su suscripción queda activa. Un tenant que excede su límite recibe la notificación y el paciente recibe el fallback.
