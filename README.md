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
