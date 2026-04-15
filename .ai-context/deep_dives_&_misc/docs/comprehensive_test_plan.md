# Plan Exhaustivo de Testing QA y E2E (Release 1.4)

Antes de redireccionar tráfico de WhatsApp Real de pacientes, debes validar el sistema internamente y asegurarlo.
**AVISO MUY IMPORTANTE:** La Fase 6 (la configuración del webhook de Meta) será LO ABSOLUTO ÚLTIMO QUE HAREMOS. Está totalmente prohibido linkear Meta hasta que las Fases 1 a 5 hayan sido confirmadas operativamente de manera local/simulada.

Cualquier fallo se aísla, se depura y se arregla localmente sin arriesgar bloqueos de Meta Graph.

---

## FASE 1: Verificación de Autorización y Carga (Frontend)
El sistema ahora soporta Multi-Tenant protegido por RLS (Row Level Security).

1. **Abre el frontend** en `http://localhost:3000/` usando un perfil fresco o modo incógnito.
2. Inicia sesión con tus credenciales de `CasaVitaCure` establecidas en Supabase.
3. Dirígete a la URL de rutas de recursos protegidas: `http://localhost:3000/chats`. 
   - **Criterio de Éxito:** La pantalla debe cargar todas las carpetas ( Inbox, Todos, Reservas). La campana en el Sidebar debe existir. Ningún error de "RLS Policy violated" debe aparecer en la consola F12 de Chrome o terminal.
4. **Data Bleed Check (Seguridad):** 
   - Genera la siguiente cURL (o pégala en un bash):
     ```bash
     curl -H "apikey: [TU_ANON_KEY_PUBLICA]" \
          -H "Authorization: Bearer [TU_ANON_KEY_PUBLICA]" \
          -X GET "https://[TU_PROYECTO].supabase.co/rest/v1/contacts?select=*"
     ```
   - **Criterio de Éxito:** Debe obligatoriamente retornar un array vacío `[]` por bloqueo explícito RLS. Si salen los contactos del CRM, **no pases de este punto**. Repasa y reejecuta `sql/fix_rls_production.sql`.

---

## FASE 2: UI Notificaciones Locales
Valida la recepción RealTime y Audio de las alertas in-app.

1. Abre `http://localhost:3000/chats`. Acepta los permisos de notificación flotantes del navegador.
2. Abre en split-screen local un visor con tu Dashboard de Supabase.
3. Ve a `Table Editor`, selecciona `alerts` y clickea `Insert row`.
4. Añade manualmente un registro forzado:
   - `tenant_id`: El UUID tuyo (`d8376510-911e-42ef-9f3b-e018d9f10915`).
   - `message`: `Prueba de Alerta E2E QA`.
   - `type`: `escalation`.
   - Clic en **Save**.
5. **Criterio de Éxito:** 
   - El sistema en React hace sonar el tono SineWave al instante.
   - Ves un Toast visible en la interfaz diciendo "Alerta de Sistema" con `Prueba de Alerta E2E QA`.
   - El icono de campana sube su burbuja numérica de `0` a `1`. Clickea la campana y revisa que apareció tu prueba.

---

## FASE 3: Telemetría / Alerting a Soporte
El Backend ahora vigila y re-envía errores automáticamente a plataformas externas (Discord, Email).

1. **Test Correo Resend (Notificación de Negocio)**:
   - Utiliza exactamente el paso 4 de la Fase 2, pero insertando un `alert` con razón de `"Handoff por Agresividad"`.
   - **Criterio de Éxito:** En 2 minutos máximos revisa el inbox del email que asignaste (`tomasgemes@gmail.com`). Debes tener un email enviado usando la marca Resend confirmando "ALERTA CRM: Handoff Requerido / Asistencia".
2. **Test Traceback a Devs (Discord Logging)**:
   - Levanta tu backend FastApi en otra terminal.
   - Mediante Postman / CURL o navegador, golpea la ruta directa `GET http://localhost:8000/api/debug-exception`.
   - Esto hace un Raise Exception explícito forzando un Catch 500 Global.
   - **Criterio de Éxito:** Tu canal de Webhooks en la app Discord recibe automáticamente un Bot Message con banda roja titulado "FATAL: Unhandled Exception", con el código exacto de Python listado en el *Traceback*.

---

## FASE 4: Sincronización Bidireccional Calendar (API)
Garantizar que el OAuth de Google puede agendar e ingresar leer slots.

1. Ve a `http://localhost:3000/config`.
2. Busca la tarjeta **Integración con Google Calendar**. Aparecerá como "No configurado / Desconectado" si no has logueado esta DB.
3. Haz click en el botón verde de Conexión y avanza por la pasarela de Gmail. Asegúrate de dar los checks azules de edición a los calendarios.
4. **Criterio de Éxito:** Redirige a config exitosamente visualizado el correo logueado y color verde "Conectado".

---

## FASE 5: Simulación AI (Local Core Heart)
El Endpoint `/api/simulate` crea un estado paralelo identico a Meta Graph Webhooks. Simularemos de inicio a fin todo lo que haría WhatsApp, pero sin requerir ni usar Meta.

1. Haz un request `POST http://localhost:8000/api/simulate`
2. **Body en JSON (Raw)**:
   ```json
   {
       "tenant_id": "d8376510-911e-42ef-9f3b-e018d9f10915",
       "phone_number": "+56999887766",
       "message_text": "Me llamo Roberto y tengo un dolor urgente en la encía. Quiero reservar mañana de inmediato."
   }
   ```
3. Mira la terminal del backend mientras trabaja en el `ProcessMessageUseCase`.
4. El LLM interpretará que se le solicitó información de reservas y llamará al Tool `CheckAvailabilityTool`. 
5. Mira la pestaña de chats del React App (`http://localhost:3000/chats`) para el usuario creado automáticamente "+56999887766".
6. **Criterio de Éxito:** Verás en RealTime cómo entra la burbuja de Roberto y unos segundos después llega la del asistente virtual que consultó sobre fechas dando una opción coherente al contexto y el `System Prompt`. Todo esto 100% de manera local y en tu interfaz en tiempo real sin involucrar a WhatsApp.

---

## FASE 6: Live Webhook a Meta (Prueba Definitiva Pública)
ESTE PASO SE EJECUTA SI Y SÓLO SÍ LAS FASES 1 A LA 5 ESTÁN APROBADAS EN VERDE.
Es el momento en que abrimos nuestro puerto validado a que Meta Inyecte Eventos Reales de la calle.

1. Procede a configurar Meta For Developers como indica el Paso 6 de `manual_configuration_guide.md`.
2. Con la URL `https://[api-production.cloudrun.app]/webhook` dada de alta y verificada como OK en Facebook.
3. Abre un teléfono con una tarjeta SIM convencional y escribe "Buen día asistente" al teléfono de tu WhatsApp Business asociado al CRM.
4. Observa los logs del Backend de Producción.
   - Trazará que el Payload Meta y procesará la petición de la misma manera exitosa en que lo hizo `/api/simulate` en la fase 5.
5. **Criterio de Éxito Final:** Llega el texto al teléfono móvil del paciente respondiendo sus dudas, y simultáneamente avanza el diálogo en tu Dashboard UI como supervisor observándolo.

**¡Felicidades, al validar el cruce externo tu CRM está 100% conectado!**
