# Configuración de Alertas en Sentry (Dashboard)

Sentry está configurado en el código para capturar excepciones globales y logs de error tanto en el Backend (FastAPI) como en el Frontend (Next.js).

Sin embargo, las alertas por correo y notificaciones deben configurarse **manualmente en el Dashboard de Sentry**.

## 1. Crear un Sentry Alert Rule (Backend)

1. Ingresa a `sentry.io` y selecciona el proyecto del **Backend**.
2. Ve a **Alerts** en el menú izquierdo y haz clic en **Create Alert**.
3. Selecciona **Issues** -> **Issue Alert**.
4. Construye la alerta con estas reglas:
   - **WHEN**: `A new issue is created` o `An issue's state changes from resolved to unresolved`.
   - **IF**: `The issue's level is equal to error or fatal`.
   - **THEN**: `Send an email to: tomasgemes@gmail.com`.
5. Guárdalo como "Backend Critical Errors".

## 2. Crear un Sentry Alert Rule (Frontend)

1. Repite los pasos anteriores para el proyecto del **Frontend**.
2. Excluir errores de red comunes:
   - **IF**: `The issue's title does not contain "NetworkError"` y `does not contain "Timeout"`.
   - **THEN**: `Send an email to: tomasgemes@gmail.com`.
3. Guárdalo como "Frontend Critical Bugs".

## 3. (Opcional) Integración con Discord vía Sentry

Si quieres que Sentry envíe TODA la data estructurada a Discord automáticamente (en lugar de solo los fallos atrapados por el Webhook manual que hemos configurado en FastAPI):

1. Ve a **Settings -> Integrations** en Sentry.
2. Busca "Discord" o "Webhooks".
3. Configura el Webhook URL del canal de desarrolladores.
4. En las Alert Rules, añade un **THEN**: `Send a notification via webhook...`.
