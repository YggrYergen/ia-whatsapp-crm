-- D:\WebDev\IA\schema.sql

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table: tenants
CREATE TABLE public.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    ws_phone_id TEXT UNIQUE NOT NULL, -- WhatsApp Phone ID from Meta
    ws_token TEXT NOT NULL,           -- WhatsApp Permanent Token
    llm_provider TEXT NOT NULL CHECK (llm_provider IN ('openai', 'gemini')),
    llm_model TEXT NOT NULL,          -- e.g., 'gpt-4o-mini', 'gemini-1.5-flash'
    system_prompt TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Note: In Supabase, Next.js auth users exist in auth.users.
-- We need a relation to map auth.users to tenants for RLS in the frontend CRM.
CREATE TABLE public.tenant_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, user_id)
);

-- Table: contacts
CREATE TABLE public.contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    phone_number TEXT NOT NULL, -- WhatsApp Number
    name TEXT,
    bot_active BOOLEAN DEFAULT TRUE,
    status TEXT DEFAULT 'lead',
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(tenant_id, phone_number)
);

-- Table: messages
CREATE TABLE public.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE, -- Denormalized for easier RLS and querying
    sender_role TEXT NOT NULL CHECK (sender_role IN ('user', 'assistant', 'human_agent')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Insert Seed Tenant "CasaVitaCure"
INSERT INTO public.tenants (id, name, ws_phone_id, ws_token, llm_provider, llm_model, system_prompt, is_active)
VALUES (
    uuid_generate_v4(), 
    'CasaVitaCure', 
    '123456789012345', -- Placeholder, replace with real WhatsApp Phone ID
    'PLACEHOLDER_TOKEN', -- Placeholder, replace with real WhatsApp Token
    'openai', 
    'gpt-5.3-instant', 
    'Eres el asistente virtual de CasaVitaCure. Tu objetivo es agendar reservas y resolver dudas sobre nuestra clínica oftalmológica.', 
    TRUE
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Helper function to get the current user's tenant_id(s)
CREATE OR REPLACE FUNCTION get_user_tenant_ids() 
RETURNS SETOF UUID AS $$
  SELECT tenant_id FROM public.tenant_users WHERE user_id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- RLS Policies for Frontend (Authenticated Users)
-- Tenants: Users can view their own tenant configuration
CREATE POLICY "Users can view their own tenant" ON public.tenants
    FOR SELECT USING (id IN (SELECT get_user_tenant_ids()));
    
CREATE POLICY "Users can update their own tenant" ON public.tenants
    FOR UPDATE USING (id IN (SELECT get_user_tenant_ids()));

-- Contacts: Users can view/insert/update contacts of their own tenant
CREATE POLICY "Users can view own contacts" ON public.contacts
    FOR SELECT USING (tenant_id IN (SELECT get_user_tenant_ids()));

CREATE POLICY "Users can update own contacts" ON public.contacts
    FOR UPDATE USING (tenant_id IN (SELECT get_user_tenant_ids()));

CREATE POLICY "Users can insert own contacts" ON public.contacts
    FOR INSERT WITH CHECK (tenant_id IN (SELECT get_user_tenant_ids()));

-- Messages: Users can view/insert messages of their own tenant
CREATE POLICY "Users can view own messages" ON public.messages
    FOR SELECT USING (tenant_id IN (SELECT get_user_tenant_ids()));

CREATE POLICY "Users can insert own messages" ON public.messages
    FOR INSERT WITH CHECK (tenant_id IN (SELECT get_user_tenant_ids()));

-- Note for Backend: 
-- The backend API will use the Supabase Service Role Key which bypasses RLS.
-- This allows the webhook to freely query the tenants table by `ws_phone_id`,
-- insert contacts, and append messages without needing an auth context under the 3-second limit.
