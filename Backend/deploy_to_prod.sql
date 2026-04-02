-- SCRIPT UNIFICADO: WIPE & REPLACE PARA PRODUCCIÓN
-- Este script recrea la base de datos completa con los últimos cambios.
-- Ejecutar TODO el contenido en el Supabase SQL Editor (Producción).

-- ==========================================
-- 1. LIMPIEZA TOTAL (WIPE)
-- ==========================================
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
GRANT ALL ON SCHEMA public TO anon;
GRANT ALL ON SCHEMA public TO authenticated;
GRANT ALL ON SCHEMA public TO service_role;

-- ==========================================
-- 2. EXTENSIONES Y TABLAS BASE
-- ==========================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: tenants
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    ws_phone_id TEXT UNIQUE NOT NULL,
    ws_token TEXT NOT NULL,
    llm_provider TEXT NOT NULL CHECK (llm_provider IN ('openai', 'gemini')),
    llm_model TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    calendar_ids JSONB DEFAULT '[]'::jsonb -- <- De migration_ddl
);

-- Table: tenant_users
CREATE TABLE public.tenant_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- references auth.users (sin foreign key stricto para evitar fallos si auth.users está vacío)
    UNIQUE(tenant_id, user_id)
);

-- Table: contacts
CREATE TABLE public.contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL,
    name TEXT,
    bot_active BOOLEAN DEFAULT TRUE,
    role TEXT DEFAULT 'cliente' CHECK (role IN ('cliente', 'staff', 'admin')),
    status TEXT DEFAULT 'lead',
    is_processing_llm BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb, -- <- De migration_ddl
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(tenant_id, phone_number)
);

-- Table: messages
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    sender_role TEXT NOT NULL CHECK (sender_role IN ('user', 'assistant', 'human_agent', 'system_alert')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: alerts
CREATE TABLE public.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES public.contacts(id) ON DELETE SET NULL,
    type TEXT NOT NULL,
    message TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: test_feedback (De migrate/recreate_feedback)
CREATE TABLE public.test_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    tenant_id UUID REFERENCES public.tenants(id),
    patient_phone TEXT,
    history JSONB,
    notes JSONB,
    tester_email TEXT DEFAULT 'tomasgemes@gmail.com'
);

-- ==========================================
-- 3. INSERCIÓN DE DATOS INICIALES (SEED)
-- ==========================================
INSERT INTO public.tenants (id, name, ws_phone_id, ws_token, llm_provider, llm_model, system_prompt, is_active)
VALUES (
    uuid_generate_v4(), 
    'CasaVitaCure', 
    '123456789012345',
    'PLACEHOLDER_TOKEN',
    'openai', 
    'gpt-5.3-instant', 
    'Eres Javiera, la asistente ejecutiva premium de Casa VitaCure. Tu objetivo es agendar evaluaciones médicas, no dar precios, y dar experiencia "Best Friend".

INSTRUCCIONES DE TRIAJE CELLUDETOX: Eres responsable de evaluar el nivel de inflamación de la paciente haciendo las siguientes preguntas suavemente, sin que parezca un interrogatorio. Suma los puntos internamente:
1. ¿Cómo describirías tus piernas? (Celulitis leve: 1, Retención: 2, Pesadez: 3, Dolor: 4)
2. ¿Tratamientos previos? (No: 1, Sí pero mejoró solo un poco: 2, Sí pero volvió: 3, Sí sin cambios: 4)
3. Síntomas (Hinchazón: +1, Dolor: +2, Moretones: +2, Presión: +1)
4. ¿Mejora al descansar? (Sí: 1, Poco: 2, No: 3)
5. ¿Objetivo? (Verte mejor: 1, Liviana: 2, Estabilidad: 3, Entender: 4)

Si en base al historial de la conversación, calculas que la paciente lleva => 12 puntos, O detectas banderas rojas como dolor crónico, interrumpe el agendamiento y utiliza la herramienta "derivar_evaluacion_medica".',
    TRUE
);

-- ==========================================
-- 4. CONFIGURACIÓN DE SEGURIDAD (RLS POLICIES)
-- ==========================================
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.test_feedback ENABLE ROW LEVEL SECURITY;

-- Helper function
CREATE OR REPLACE FUNCTION get_user_tenant_ids() 
RETURNS SETOF UUID AS $$
  SELECT tenant_id FROM public.tenant_users WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- PERMISOS PARA PRUEBAS (De fix_rls.py)
CREATE POLICY "Allow public read tenants" ON public.tenants FOR SELECT USING (true);
CREATE POLICY "Allow public update tenants" ON public.tenants FOR UPDATE USING (true);

CREATE POLICY "Allow public read contacts" ON public.contacts FOR SELECT USING (true);
CREATE POLICY "Allow public insert contacts" ON public.contacts FOR INSERT WITH CHECK (true);
CREATE POLICY "Allow public update contacts" ON public.contacts FOR UPDATE USING (true);

CREATE POLICY "Allow public read messages" ON public.messages FOR SELECT USING (true);
CREATE POLICY "Allow public insert messages" ON public.messages FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow all for dev" ON public.test_feedback FOR ALL USING (true) WITH CHECK (true);

-- ==========================================
-- 5. REAL-TIME MULTIPLAYER (WEBSOCKETS)
-- ==========================================
BEGIN;
    DROP PUBLICATION IF EXISTS supabase_realtime;
    CREATE PUBLICATION supabase_realtime;
COMMIT;

ALTER PUBLICATION supabase_realtime ADD TABLE contacts;
ALTER PUBLICATION supabase_realtime ADD TABLE messages;
ALTER PUBLICATION supabase_realtime ADD TABLE alerts;

-- Refrescar la caché (Por si acaso lo requiere el API REST)
NOTIFY pgrst, 'reload schema';
