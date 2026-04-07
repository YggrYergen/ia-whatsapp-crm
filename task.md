# Tasks — IA WhatsApp CRM Roadmap

---

## Fase 0: Lanzamiento Crítico (Próximas 24 horas)

### 0.1 Seguridad y Aislamiento (Bloqueante)
- [x] Auditar todas las tablas con políticas RLS `USING (true)`
- [x] Eliminar (`DROP POLICY`) cada política de acceso público (8 políticas eliminadas)
- [x] Verificar que consultas anónimas retornen `0 rows` o error `403`
- [x] Crear tabla `tenant_users` con FK a `auth.users` y `tenants`
- [x] Crear función helper `get_my_tenant_id()` con `SECURITY DEFINER` + `search_path`
- [x] Crear políticas RLS restrictivas (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) validando JWT + `tenant_id` (12 políticas)
- [x] Habilitar RLS en `tenants`, `contacts`, `messages`, `alerts`
- [x] Corregir security advisors (alerts RLS + function search_path)
- [x] Documentar las políticas aplicadas

### 0.2 Mitigación de Latencia Core
- [x] Configurar `--min-instances=1` en Cloud Run
- [x] Redesplegar el servicio con la nueva configuración
- [x] Verificar eliminación del cold start (~120s) con request tras inactividad
- [x] Refactorizar `google_client.py` como Singleton (`_GoogleServiceSingleton`)
- [x] Envolver llamadas síncronas de Google API en `asyncio.to_thread()`
- [x] Identificar operaciones secuenciales de Supabase en el webhook
- [x] Agrupar operaciones independientes con `asyncio.gather()` (3 pre-LLM + 3 post-LLM)
- [x] Actualizar Dockerfile para incluir `credentials/`
- [x] Restaurar env vars en Cloud Run (5 variables requeridas)
- [x] Verificar deploy exitoso con health check

### 0.3 Conexión Meta API
- [x] Configurar endpoint de verificación (`GET`) con token de verificación (ya existente en `routers.py`)
- [x] Implementar handler de mensajes entrantes (`POST` webhook) (ya existente)
- [x] Implementar envío de respuestas salientes vía WhatsApp Business Cloud API (ya existente en `meta_graph_api.py`)
- [x] Verificar flujo completo: health check → backend operativo

---

## Fase 1: Estabilización Operativa y Multi-Tenant (Semanas 1-2)

### 1.1 CRM y Rendimiento del Frontend
- [ ] Crear/ajustar query a tabla `patients`/`contacts` en Supabase
- [ ] Renderizar tabla con columnas: nombre, última visita, estado, LTV, resumen clínico
- [ ] Implementar paginación o infinite scroll
- [ ] Analizar `CrmContext` e identificar re-renders innecesarios
- [ ] Crear `AuthContext`, `ChatContext`, `UIContext`
- [ ] Migrar componentes consumidores a los nuevos contextos
- [ ] Implementar envío de mensajes del staff al WhatsApp del paciente (hand-off)
- [ ] Mostrar indicador de "IA pausada" en la UI
- [ ] Al reactivar IA, retomar contexto incluyendo mensajes humanos

### 1.2 Automatización de Calendarios (Multi-Tenant)
- [ ] Crear endpoint `/api/google/auth` para iniciar flujo OAuth 2.0
- [ ] Implementar callback `/api/google/callback`
- [ ] Encriptar `refresh_token` (AES-256) y almacenar en Supabase
- [ ] Crear botón "Conectar Google Calendar" en configuración del tenant
- [ ] Implementar opción de desconectar (revocar token)

### 1.3 Sistema de Logging y Manejo de Excepciones
- [ ] Integrar Sentry en FastAPI (Backend)
- [ ] Integrar Sentry en Next.js (Frontend)
- [ ] Configurar alertas (email/Slack) para errores críticos

### 1.4 Sistema de Alertas Híbrido
- [ ] Implementar Web Notifications API con sonido
- [ ] Crear componente de feed de alertas en tiempo real
- [ ] Implementar servicio de envío de emails para alertas
- [ ] Evaluar y registrar Template Messages en Meta

---

## Fase 2: Eficiencia de IA y Experiencia de Usuario (Semanas 2-4)

### 2.1 Respuestas en Etapas (Streaming UX)
- [ ] Detectar tool calls con latencia y enviar acuse de recibo
- [ ] Reestructurar handler del webhook para flujo con acuse
- [ ] Medir latencia percibida antes/después

### 2.2 Routing Dinámico de Modelos
- [ ] Implementar clasificador de complejidad
- [ ] Configurar mapa de modelos por nivel de complejidad
- [ ] Implementar fallback y monitoreo

---

## Fase 3: FinOps, Monetización y Escala (Semanas 4-8)

### 3.1 Pasarela de Pagos (Stripe)
- [ ] Integración de Stripe Checkout para suscripciones
- [ ] Implementar Metered Billing

### 3.2 Tracking Preciso de Cómputo
- [ ] Crear tabla `usage_logs` en Supabase
- [ ] Interceptar metadatos de tokens
- [ ] Dashboard de consumo en frontend

### 3.3 Control de Acceso y Suscripciones
- [ ] Middleware de validación de suscripción
- [ ] Notificación al administrador
- [ ] Respuesta fallback al paciente
