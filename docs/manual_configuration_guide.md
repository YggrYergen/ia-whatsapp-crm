# Guía Exhaustiva de Configuración Manual para Producción

Para que el CRM (Versión 1.4) opere sin errores, debes configurar los servicios de terceros. 
**NOTA CRÍTICA:** No configures Meta (WhatsApp) hasta que ABSOLUTAMENTE TODOS los demás pasos locales (Base de Datos, Alertas, Correo y Calendar) y Pruebas Simuladas E2E estén correctos. 

Sigue estos pasos *al pie de la letra* respetando el orden.

---

## 1. Supabase (Base de Datos y RLS)

Proteger la BD para que solo admita usuarios autenticados del Tenant correcto.

### Pasos en la UI de Supabase:
1. Navega a **https://supabase.com/dashboard/projects**.
2. Selecciona tu proyecto actual (ej. `IA WhatsApp CRM`).
3. En la barra lateral izquierda, haz clic en **SQL Editor** (`/sql/new`).
4. Selecciona **+ New query**.
5. Abre en tu repositorio local el archivo situado en `D:\WebDev\IA\Backend\sql\fix_rls_production.sql`. Copia *todo* su contenido (Ctrl+C).
6. Pega el contenido en el editor SQL de Supabase (Ctrl+V) y haz clic en el botón verde **Run** (o presiona `Cmd/Ctrl + Enter`).
7. Valida en la terminal inferior que reciba un mensaje como *"Success. No rows returned"*.
8. Ve a **Project Settings (Engranaje) -> API** y verifica que `SUPABASE_SERVICE_ROLE_KEY` exista en tu archivo `.env` del backend (¡jamás en el del frontend!).

---

## 2. Resend (Alertas de Correo para Triage/Negocio)

Configurar notificaciones administrativas para Handoffs u urgencias médicas de los pacientes.

### Pasos en la UI de Resend:
1. Ve a **https://resend.com/domains**.
2. Haz clic derecho arriba en **Add Domain**. Ingresa tu dominio limpio (ej. `tuasistentevirtual.cl`) y la región.
3. El sistema te mostrará una lista de **DNS Records** (usualmente un TXT para SPF, p. ej. `v=spf1 include:amazonses.com ~all`, y otro TXT para DKIM como `resend._domainkey`).
4. Abre una ventana en tu Administrador DNS (Cloudflare, GoDaddy, Namecheap o Vercel) y crea exactamente esos registros TXT.
5. Vuelve a Resend y haz clic en **Verify**. Puede tomar minutos. Su estatus pasará a verde ("Verified").
6. Ve a **https://resend.com/api-keys**.
7. Haz clic en **Create API Key**, ponle "Permisos Full Access" y nombre "CRM CRM1.4". Cópialo.
8. Agrégalo al `.env` backend como `RESEND_API_KEY`.
9. Verifica que en `D:\WebDev\IA\Backend\app\infrastructure\email\email_service.py` el `FROM_EMAIL` (Línea 7) coincida con un usuario bajo tu dominio ya verificado (ej. `alertas@tuasistentevirtual.cl`).

---

## 3. Discord (Telemetría de Excepciones)

Es súper útil tener el Traceback explícito inyectado directo en un chat del equipo dev sin incurrir en costos extras de monitoreo.

### Pasos en la UI de Discord:
1. Ve a tu aplicación de Discord de escritorio o la web. 
2. Haz clic derecho sobre tu Servidor de Equipo (u Opciones de Servidor). Selecciona **Server Settings (Ajustes del servidor)**.
3. Ve a la pestaña **Integrations (Integraciones)** (bajo Apps en el panel izquierdo).
4. Haz clic en la cajita **Webhooks**, y luego **New Webhook**.
5. Llámalo "Javiera Server Logger". 
6. Cópiala desde el botón **Copy Webhook URL**.
7. Inyéctala en el archivo `.env` del **Backend**: `DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/XX/YY"`.

---

## 4. Google Cloud Console (Calendar API)

Permitir al usuario conectar su Calendar desde la UI local.

### Pasos en Google Cloud:
1. Entra a **https://console.cloud.google.com/apis/credentials**.
2. Dale arriba a **Create Credentials -> OAuth client ID**.
3. Selecciona tipo **Web application**.
4. En "Authorized redirect URIs", haz clic en **ADD URI** e ingresa la ruta de retorno final, por ejemplo: `http://localhost:8000/api/google/callback` y/o la de producción.
5. Toma el **Client ID** y **Client Secret** generados, pégalos en el `.env` del Backend como `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`.

---

## 5. Meta for Developers (WhatsApp Webhook) FINAL

**ADVERTENCIA:** Ejecuta esto ÚNICAMENTE cuando hayas pasado todo el `comprehensive_test_plan.md` hasta la Fase 5. 

### Pasos en la UI de Meta:
1. Entra a **https://developers.facebook.com/** y loguéate.
2. Ve a **My Apps** y selecciona el nombre de tu App (ej. "Javiera CRM").
3. En la columna izquierda (App Dashboard), ubica la sección **WhatsApp** y despliégala.
4. Haz clic en **Configuration**.
5. Busca el bloque central que dice **Webhook**. Verás un botón llamado **Edit** (Editar), haz clic allí.
6. Completa el formulario modal de esta manera:
   - **Callback URL:** Ingresa la URI pública definitiva de tu backend (Ej: `https://api.tu-dominio.com/webhook`).
   - **Verify Token:** Inventa o pega un string aleatorio altamente seguro (ej. `mypassword123`). Ese mismo valor **debe estar** seteado en tu archivo `.env` local en la variable `WHATSAPP_WEBHOOK_VERIFY_TOKEN`.
7. Haz clic en **Verify and Save**. (Meta mandará un `GET` a tu server; si tu server está online y configurado con ese token exacto, dirá 'Success'. Si no, fallará y no podrás avanzar).
8. Después de que guarde, haz clic debajo en el botón **Manage** (dentro del mismo bloque de Webhook).
9. Mueve el switch a **On** para la fila del evento `messages` (y opcionalmente `messages_template_status_update`). Haz clic en **Done**.
