# Arquitectura de Frontend

Frontend/
├── app
│   ├── api
│   │   └── simulate
│   │       └── route.ts
│   ├── config
│   │   └── page.tsx
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
├── lib
│   └── supabase.ts
├── next-env.d.ts
├── package.json
├── postcss.config.js
├── tailwind.config.js
└── tsconfig.json

---

# Contenido de Archivos

--- INICIO DE ARCHIVO: route.ts (Ruta: Frontend/app/api/simulate/route.ts) ---

```typescript
import { NextResponse } from 'next/server'

export async function POST(req: Request) {
    try {
        const { phone, message, tenantId } = await req.json()

        const payload = {
            object: "whatsapp_business_account",
            entry: [{
                changes: [{
                    value: {
                        metadata: {
                            phone_number_id: "123456789012345" // ID semilla
                        },
                        messages: [{
                            from: phone,
                            text: { body: message }
                        }]
                    }
                }]
            }]
        }

        const res = await fetch(process.env.BACKEND_URL || 'http://127.0.0.1:8000/webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            throw new Error('Failed to reach backend')
        }

        return NextResponse.json({ success: true })
    } catch (error) {
        return NextResponse.json({ success: false, error: 'Simulation failed' }, { status: 500 })
    }
}

```

--- FIN DE ARCHIVO: route.ts ---

--- INICIO DE ARCHIVO: page.tsx (Ruta: Frontend/app/config/page.tsx) ---

```typescript
'use client'

import React, { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { Save, Bot } from 'lucide-react'

export default function ConfigPanel() {
    const supabase = createClient()
    const [tenant, setTenant] = useState<any>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchTenant()
    }, [])

    const fetchTenant = async () => {
        const { data } = await supabase.from('tenants').select('*').limit(1).single()
        if (data) setTenant(data)
        setLoading(false)
    }

    const handleSave = async () => {
        if (!tenant) return
        const { error } = await supabase.from('tenants').update({
            llm_provider: tenant.llm_provider,
            llm_model: tenant.llm_model,
            system_prompt: tenant.system_prompt
        }).eq('id', tenant.id)

        if (!error) alert('Configuración guardada exitosamente')
    }

    if (loading) return <div>Cargando...</div>

    return (
        <div className="p-8 max-w-4xl mx-auto bg-white rounded-xl shadow-lg mt-10">
            <div className="flex items-center gap-3 mb-8 border-b pb-4">
                <Bot size={32} className="text-blue-600" />
                <h1 className="text-2xl font-bold">Configuración del Asistente (Tenant)</h1>
            </div>

            <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Proveedor de IA</label>
                        <select
                            value={tenant.llm_provider}
                            onChange={(e) => setTenant({ ...tenant, llm_provider: e.target.value })}
                            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            <option value="openai">OpenAI (GPT-5.4)</option>
                            <option value="gemini">Google Gemini (3.1)</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Modelo Seleccionado</label>
                        <select
                            value={tenant.llm_model}
                            onChange={(e) => setTenant({ ...tenant, llm_model: e.target.value })}
                            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            {tenant.llm_provider === 'openai' ? (
                                <>
                                    <option value="o4-mini">o4-mini (Reasoning/CoT)</option>
                                    <option value="gpt-5-mini">GPT-5 Mini (Current/Reasoning)</option>
                                    <option value="gpt-4o-mini">GPT-4o Mini (Legacy)</option>
                                </>
                            ) : (
                                <>
                                    <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro (Smart)</option>
                                    <option value="gemini-3.1-flash-lite-preview">Gemini 3.1 Flash-Lite (Fast)</option>
                                </>
                            )}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">System Prompt (Instrucciones)</label>
                    <textarea
                        rows={8}
                        value={tenant.system_prompt}
                        onChange={(e) => setTenant({ ...tenant, system_prompt: e.target.value })}
                        className="w-full p-4 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm bg-gray-50"
                        placeholder="Introduce las instrucciones del bot..."
                    />
                </div>

                <div className="pt-4 flex justify-end">
                    <button
                        onClick={handleSave}
                        className="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-700 transition"
                    >
                        <Save size={20} />
                        Guardar Configuración
                    </button>
                </div>
            </div>
        </div>
    )
}

```

--- FIN DE ARCHIVO: page.tsx ---

--- INICIO DE ARCHIVO: globals.css (Ruta: Frontend/app/globals.css) ---

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --background: #f0f2f5;
  --whatsapp-green: #00a884;
  --whatsapp-panel: #ffffff;
  --whatsapp-bubble-user: #dcf8c6;
  --whatsapp-bubble-ai: #ffffff;
}

body {
  background-color: var(--background);
  color: #111b21;
}

.chat-height {
  height: calc(100vh - 60px);
}

```

--- FIN DE ARCHIVO: globals.css ---

--- INICIO DE ARCHIVO: layout.tsx (Ruta: Frontend/app/layout.tsx) ---

```typescript
import './globals.css';

export const metadata = {
  title: 'AI CRM',
  description: 'Generated by Next.js',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

```

--- FIN DE ARCHIVO: layout.tsx ---

--- INICIO DE ARCHIVO: page.tsx (Ruta: Frontend/app/page.tsx) ---

```typescript
'use client'

import React, { useState, useEffect, useRef } from 'react'
import { createClient } from '@/lib/supabase'
import { MessageCircle, Settings, User, Send, Bot, Pause, Play, Sparkles, Check, Phone, Clock, AlertTriangle, ArrowLeft, MoreVertical, Info } from 'lucide-react'
import Link from 'next/link'

const formatWhatsAppText = (text: string) => {
    if (!text) return '';
    let html = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // WhatsApp formatting rules (2026 specs, also covers LLM common ** uses)
    html = html.replace(/```([\s\S]*?)```/g, '<span class="font-mono bg-black/5 p-1 rounded">$1</span>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    html = html.replace(/~([^~]+)~/g, '<del>$1</del>');

    return html;
}

const supabase = createClient()

export default function CRMDashboard() {
    const [selectedContact, setSelectedContact] = useState<any>(null)
    const [contacts, setContacts] = useState<any[]>([])
    const [messages, setMessages] = useState<any[]>([])
    const [newMessage, setNewMessage] = useState('')
    const [simulationMode, setSimulationMode] = useState(false)
    const [mobileView, setMobileView] = useState<'list' | 'chat' | 'info'>('list')
    const [showDesktopInfo, setShowDesktopInfo] = useState(false)
    const [toasts, setToasts] = useState<any[]>([])
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const selectedContactRef = useRef<any>(null)

    useEffect(() => {
        selectedContactRef.current = selectedContact
    }, [selectedContact])

    useEffect(() => {
        fetchContacts()

        // Ensure standard DB seed test contact exists
        seedTestContact()

        const uniqueChannelName = `schema-db-changes-${Date.now()}`;
        const sub = supabase
            .channel(uniqueChannelName)
            .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' }, (payload) => {
                console.log('🔥 NEW REALTIME PAYLOAD ARRIVED:', payload)
                const newMessage = payload.new as any
                
                // 🌟 Global Toast for System Alerts
                if (newMessage.sender_role === 'system_alert') {
                     const toastId = Date.now();
                     setToasts((prev) => [...prev, { id: toastId, payload: newMessage }]);
                     setTimeout(() => {
                         setToasts((prev) => prev.filter(t => t.id !== toastId));
                     }, 30000); // 30 seconds
                }

                // 🛡️ Protect active chat view (DO NOT leak messages from other contacts into the open chat)
                if (selectedContactRef.current && newMessage.contact_id !== selectedContactRef.current.id) {
                    fetchContacts(); // Update contacts list to show unread/last message
                    return; // Abort adding to current messages array
                }

                setMessages((prev) => {
                    // 1. Exact ID check (most reliable)
                    if (prev.find(m => m.id === newMessage.id)) return prev;

                    // 2. Optimistic Update deduplication:
                    // If we have a temporary message (starts with "temp-") with the same content sent recently,
                    // replace it with the real one from the DB or filter it out.
                    const isDuplicateContent = prev.some(m =>
                        String(m.id).startsWith('temp-') &&
                        m.content === newMessage.content &&
                        m.sender_role === newMessage.sender_role
                    );

                    if (isDuplicateContent) {
                        return prev.map(m =>
                            (String(m.id).startsWith('temp-') && m.content === newMessage.content)
                                ? newMessage
                                : m
                        );
                    }

                    return [...prev, newMessage].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
                })
                fetchContacts()
            })
            .subscribe((status, err) => {
                console.log('📡 Realtime subscription status:', status, err ? err : '')
            })

        return () => {
            console.log('🧹 Cleaning up channel:', uniqueChannelName);
            supabase.removeChannel(sub)
        }
    }, [])

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    const seedTestContact = async () => {
        const { data: tenant } = await supabase.from('tenants').select('id').limit(1).single()
        if (!tenant) return

        const testPhone = "56912345678"
        const { data: existing } = await supabase.from('contacts').select('*').eq('phone_number', testPhone).single()

        if (!existing) {
            await supabase.from('contacts').insert({
                tenant_id: tenant.id,
                phone_number: testPhone,
                name: "Chat de Prueba (Tú)",
                bot_active: true,
                status: "lead"
            })
            fetchContacts()
        }
    }

    const fetchContacts = async () => {
        const { data } = await supabase.from('contacts').select('*').order('last_message_at', { ascending: false })
        if (data) setContacts([...data].sort((a, b) => a.phone_number === '56912345678' ? -1 : b.phone_number === '56912345678' ? 1 : 0))
    }

    const fetchMessages = async (contactId: string) => {
        const { data } = await supabase.from('messages').select('*').eq('contact_id', contactId).order('timestamp', { ascending: true })
        if (data) setMessages(data)
    }

    const toggleBot = async () => {
        if (!selectedContact) return
        const newState = !selectedContact.bot_active
        await supabase.from('contacts').update({ bot_active: newState }).eq('id', selectedContact.id)
        setSelectedContact({ ...selectedContact, bot_active: newState })
        setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, bot_active: newState } : c))
    }

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newMessage.trim() || !selectedContact) return

        const messageContent = newMessage
        setNewMessage('') // clear instant

        // Optimistic Update so the message registers on screen immediately
        const tempMsg = {
            id: `temp-${Date.now()}`,
            contact_id: selectedContact.id,
            tenant_id: selectedContact.tenant_id,
            sender_role: (simulationMode && selectedContact.phone_number === "56912345678") ? 'user' : 'human_agent',
            content: messageContent,
            timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, tempMsg])

        if (simulationMode && selectedContact.phone_number === "56912345678") {
            // Send as "User" bypassing Supabase client-side insert, hits Webhook instead
            await fetch('/api/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone: selectedContact.phone_number,
                    message: messageContent,
                    tenantId: selectedContact.tenant_id
                })
            })
        } else {
            // Send as "Agent" normally
            await supabase.from('messages').insert({
                contact_id: selectedContact.id,
                tenant_id: selectedContact.tenant_id,
                sender_role: 'human_agent',
                content: messageContent
            })
        }
    }

    const isTestContact = selectedContact?.phone_number === "56912345678"

    return (
        <div className="flex h-screen w-full bg-[#f4f7f6] overflow-hidden text-[#1e293b] font-sans antialiased relative">
            
            {/* 🌟 Global Toasts Overlay */}
            <div className="fixed top-4 right-4 z-50 flex flex-col gap-3 max-w-sm w-full px-4 md:px-0">
                {toasts.map(toast => (
                    <div key={toast.id} className="bg-white border-l-4 border-rose-500 shadow-2xl rounded-lg p-4 flex flex-col gap-2 animate-in slide-in-from-top-4 fade-in duration-300">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-2 text-rose-600 font-bold text-sm uppercase tracking-wide">
                                <AlertTriangle size={16} /> Alerta de Sistema
                            </div>
                            <button onClick={() => setToasts(prev => prev.filter(t => t.id !== toast.id))} className="text-slate-400 hover:text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-full p-1 transition-colors">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            </button>
                        </div>
                        <p className="text-sm text-slate-700 font-medium whitespace-pre-wrap">{toast.payload.content}</p>
                        <button 
                            onClick={() => {
                                const systemContact = contacts.find(c => c.name?.includes('Alertas') || c.phone_number?.includes('999999999'));
                                if (systemContact) {
                                    setSelectedContact(systemContact);
                                    fetchMessages(systemContact.id);
                                    setSimulationMode(false);
                                    setMobileView('chat');
                                }
                                setToasts(prev => prev.filter(t => t.id !== toast.id));
                            }} 
                            className="bg-indigo-50 text-indigo-600 px-3 py-1.5 rounded-md font-bold hover:bg-indigo-100 transition-colors text-xs self-start mt-1 cursor-pointer"
                        >
                            Ir al chat de Alertas →
                        </button>
                    </div>
                ))}
            </div>

            {/* LEFT BAR: Navigation & Contacts */}
            <div className={`
                bg-white border-r border-slate-200 flex flex-col shadow-sm z-10 transition-all
                ${mobileView === 'list' ? 'w-full' : 'hidden md:flex md:w-[320px] lg:w-[380px]'}
            `}>
                {/* Header */}
                <div className="h-[72px] px-5 flex justify-between items-center border-b border-slate-100 bg-white">
                    <div className="flex items-center gap-3 text-emerald-600">
                        <MessageCircle size={28} className="fill-emerald-100" />
                        <h1 className="font-bold text-xl tracking-tight">Testing Javiera IA</h1>
                    </div>
                    <Link href="/config">
                        <button className="p-2 text-slate-400 hover:text-emerald-500 hover:bg-emerald-50 rounded-full transition-colors">
                            <Settings size={20} />
                        </button>
                    </Link>
                </div>

                {/* Sub Header & Search (Visual Only) */}
                <div className="p-4 bg-slate-50/50">
                    <div className="relative">
                        <input
                            placeholder="Buscar chats..."
                            className="w-full bg-slate-100 text-sm rounded-lg pl-10 pr-4 py-2.5 outline-none focus:ring-2 focus:ring-emerald-500 border-transparent transition-all"
                        />
                        <svg className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                    </div>
                </div>

                {/* Contacts List */}
                <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
                    {contacts.map((c) => {
                        const isSelected = selectedContact?.id === c.id
                        const isSimulation = c.phone_number === "56912345678"

                        return (
                            <div
                                key={c.id}
                                onClick={() => {
                                    setSelectedContact(c);
                                    fetchMessages(c.id);
                                    setSimulationMode(isSimulation);
                                    setMobileView('chat');
                                }}
                                className={`
                                    p-3 rounded-xl cursor-pointer transition-all border relative
                                    ${isSelected
                                        ? 'bg-emerald-50 border-emerald-200 shadow-sm'
                                        : 'bg-white border-transparent hover:bg-slate-50'
                                    }
                                `}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3 truncate">
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm
                                            ${isSimulation ? 'bg-indigo-100 text-indigo-600' : 'bg-slate-200 text-slate-600'}
                                        `}>
                                            {isSimulation ? 'T' : c.phone_number.slice(-2)}
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-2">
                                                <span className={`font-semibold ${isSelected ? 'text-emerald-900' : 'text-slate-700'}`}>
                                                    {c.name || c.phone_number}
                                                </span>
                                                {isSimulation && <span className="bg-indigo-100 text-indigo-700 text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wide">Test</span>}
                                            </div>
                                            <p className="text-xs text-slate-400 mt-0.5 capitalize">{c.status} • {c.bot_active ? '🤖 IA Activa' : '👤 Humano'}</p>
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-slate-400 font-medium">
                                        {c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                    </span>
                                </div>
                                <button
                                    onClick={async (e) => {
                                        e.stopPropagation();
                                        const newState = !c.bot_active;
                                        await supabase.from('contacts').update({ bot_active: newState }).eq('id', c.id);
                                        setContacts(contacts.map(cont => cont.id === c.id ? { ...cont, bot_active: newState } : cont));
                                        if (selectedContact?.id === c.id) {
                                            setSelectedContact({ ...selectedContact, bot_active: newState });
                                        }
                                    }}
                                    className={`absolute bottom-3 right-3 w-[1.125rem] h-[1.125rem] rounded-full flex items-center justify-center shadow-md transition-transform flex-shrink-0 hover:scale-110 active:scale-95
                                        ${c.bot_active ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-white'}
                                    `}
                                    title={c.bot_active ? "IA Activa (Clic para pausar)" : "IA Pausada (Clic para activar)"}
                                >
                                    {c.bot_active ? <Play size={8} className="fill-current ml-[1px]" /> : <Pause size={8} className="fill-current" />}
                                </button>
                            </div>
                        )
                    })}
                </div>
            </div>

            {/* CENTER: Chat Interface */}
            <div
                className={`
                    flex-col relative bg-cover bg-center flex-1
                    ${mobileView === 'chat' ? 'flex w-full absolute inset-0 z-20 md:static md:w-auto md:z-auto' : 'hidden md:flex'}
                `}
                style={{ backgroundColor: '#efeae2' }}
            >
                {selectedContact ? (
                    <>
                        {/* Chat Header */}
                        <div
                            className="h-[72px] bg-white/95 backdrop-blur-md px-4 md:px-6 flex justify-between items-center shadow-sm z-10 border-b border-slate-200 cursor-pointer hover:bg-slate-50 transition-colors"
                            onClick={() => {
                                setMobileView('info');
                                setShowDesktopInfo(!showDesktopInfo);
                            }}
                        >
                            <div className="flex items-center gap-3 md:gap-4 flex-1 overflow-hidden">
                                <button
                                    className="p-2 -ml-2 text-slate-500 hover:bg-slate-100 rounded-full md:hidden"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setMobileView('list');
                                    }}
                                >
                                    <ArrowLeft size={20} />
                                </button>
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-white shadow-sm flex-shrink-0
                                    ${isTestContact ? 'bg-indigo-500' : 'bg-emerald-500'}
                                `}>
                                    <User size={20} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-slate-800 text-base md:text-lg truncate">{selectedContact.name || selectedContact.phone_number}</h3>
                                    <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-600">
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0"></span>
                                        En Línea
                                    </div>
                                </div>
                            </div>

                            <div className="flex gap-2 md:gap-3 flex-shrink-0">
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        toggleBot();
                                    }}
                                    className={`
                                        flex items-center gap-1.5 md:gap-2 px-3 py-1.5 md:px-5 md:py-2 rounded-lg text-xs md:text-sm font-bold transition-all shadow-sm
                                        ${selectedContact.bot_active
                                            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                                            : 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200'
                                        }
                                    `}
                                >
                                    {selectedContact.bot_active ? <Pause size={16} className="fill-current w-4 h-4" /> : <Play size={16} className="fill-current w-4 h-4" />}
                                    <span className="hidden md:inline">{selectedContact.bot_active ? 'Pausar IA' : 'Reanudar IA'}</span>
                                    <span className="md:hidden">{selectedContact.bot_active ? 'Pausar' : 'Activar'}</span>
                                </button>
                                <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full hidden md:flex">
                                    <MoreVertical size={20} />
                                </button>
                            </div>
                        </div>

                        {/* Chat Messages */}
                        <div className="flex-1 overflow-y-auto w-full overflow-x-hidden scroll-smooth" style={{ scrollbarGutter: 'stable' }}>
                            <div className="max-w-4xl mx-auto w-full px-4 md:px-6 py-6 space-y-4">
                                {isTestContact && (
                                    <div className="flex justify-center mb-6">
                                        <span className="bg-indigo-100/90 text-indigo-800 text-xs px-4 py-1.5 rounded-full shadow-sm font-medium flex items-center gap-2">
                                            <Sparkles size={14} />
                                            Chat de Prueba: Todo lo que envíes aquí simulará a un paciente conversando con la IA.
                                        </span>
                                    </div>
                                )}

                                {messages.map((m, idx) => {
                                    const isUserMessage = m.sender_role === 'user' || m.sender_role === 'cliente'
                                    const isAI = m.sender_role === 'assistant'
                                    const isHumanAgent = m.sender_role === 'human_agent' || m.sender_role === 'staff' || m.sender_role === 'admin'
                                    const isSystemAlert = m.sender_role === 'system_alert'

                                    // Check if this is an internal/testing chat that uses inverted POVs
                                    const isTestingChat = selectedContact?.phone_number === '56912345678'
                                    const isAlertChat = selectedContact?.name === 'Alertas Sistema 🚨' || selectedContact?.phone_number === '+56999999999'

                                    // Bubble logic
                                    let bubbleClasses = "max-w-[75%] px-4 py-2.5 rounded-2xl shadow-sm text-[15px] relative "
                                    let alignments = ""

                                    if (isTestingChat || isAlertChat) {
                                        // INTERNAL POV: We are the "User/Receivers", so external/bot voices are on the left.
                                        if (isUserMessage || isHumanAgent) {
                                            alignments = "justify-end"
                                            bubbleClasses += "bg-[#d9fdd3] text-[#111b21] rounded-tr-[4px] border border-green-100/50"
                                        } else if (isAI || isSystemAlert) {
                                            alignments = "justify-start"
                                            bubbleClasses += "bg-white text-slate-800 rounded-tl-[4px] border border-slate-100"
                                            if (isSystemAlert) {
                                                // Stronger visual for system alerts
                                                bubbleClasses += " border-l-4 border-l-red-500 bg-red-50 text-red-900"
                                            }
                                        } else {
                                            alignments = "justify-start"
                                            bubbleClasses += "bg-white text-slate-800 rounded-tl-[4px] border border-slate-100"
                                        }
                                    } else {
                                        // NORMAL CRM POV
                                        // What the external WhatsApp user says -> Left
                                        // What our Assistant or Human Agent says -> Right
                                        if (isUserMessage) {
                                            alignments = "justify-start"
                                            bubbleClasses += "bg-white text-slate-800 rounded-tl-[4px] border border-slate-100"
                                        } else if (isAI || isSystemAlert || isHumanAgent) {
                                            alignments = "justify-end"
                                            if (isHumanAgent) {
                                                bubbleClasses += "bg-[#cce4ff] text-[#002f6c] rounded-tr-[4px] border border-blue-100/50"
                                            } else {
                                                bubbleClasses += "bg-[#d9fdd3] text-[#111b21] rounded-tr-[4px] border border-green-100/50"
                                            }
                                        } else {
                                            alignments = "justify-start"
                                            bubbleClasses += "bg-slate-100 text-slate-800"
                                        }
                                    }

                                    return (
                                        <div key={m.id || idx} className={`flex w-full ${alignments}`}>
                                            <div className={`flex flex-col gap-1 max-w-[85%] md:max-w-[75%] ${alignments === 'justify-end' ? 'items-end' : 'items-start'}`}>
                                                <div className={bubbleClasses.replace("max-w-[75%]", "") + " break-words break-all"}>
                                                    {isAI && <div className="flex items-center gap-1 mb-1 text-[11px] font-bold text-emerald-600"><Sparkles size={12} /> AI AGENT</div>}
                                                    {isSystemAlert && <div className="flex items-center gap-1 mb-1 text-[11px] font-bold text-red-600"><AlertTriangle size={12} /> ALERTA DE SISTEMA</div>}
                                                    {isHumanAgent && <div className="flex items-center gap-1 mb-1 text-[11px] font-bold text-blue-600"><User size={12} /> TÚ (STAFF)</div>}
                                                    <div
                                                        className="leading-relaxed whitespace-pre-wrap"
                                                        dangerouslySetInnerHTML={{ __html: formatWhatsAppText(m.content) }}
                                                    />
                                                    <div className="flex items-center justify-end gap-1.5 mt-1 opacity-70">
                                                        <span className="text-[10px] font-medium uppercase">
                                                            {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                        </span>
                                                        {(isUserMessage || isHumanAgent || isAI || isSystemAlert) && <Check size={14} className={alignments === 'justify-end' ? 'text-blue-500' : 'text-slate-400'} />}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })}
                                <div ref={messagesEndRef} />
                            </div>
                        </div>

                        {/* Input Area */}
                        <div className="bg-white/95 backdrop-blur-md border-t border-slate-200">
                            <form onSubmit={handleSendMessage} className="p-4 flex gap-3 max-w-4xl mx-auto w-full">
                                <input
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    value={newMessage}
                                    className={`flex-1 rounded-xl px-5 py-3.5 outline-none border-2 text-[15px] transition-colors
                                        ${simulationMode && isTestContact
                                            ? 'bg-indigo-50 border-indigo-200 focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100 text-indigo-900 placeholder-indigo-300'
                                            : 'bg-slate-50 border-slate-200 focus:border-emerald-400 focus:ring-4 focus:ring-emerald-100 text-slate-800'
                                        }
                                    `}
                                    placeholder={simulationMode && isTestContact ? "Escribe como si fueras un paciente..." : "Escribe un mensaje al cliente..."}
                                />
                                <button
                                    type="submit"
                                    disabled={!newMessage.trim()}
                                    className={`p-3.5 rounded-xl text-white shadow-md transition-transform active:scale-95 disabled:opacity-50 flex items-center justify-center w-14
                                        ${simulationMode && isTestContact ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-emerald-600 hover:bg-emerald-700'}
                                    `}
                                >
                                    <Send size={20} className="ml-1" />
                                </button>
                            </form>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center bg-slate-50">
                        <div className="w-24 h-24 bg-white rounded-full shadow-sm flex items-center justify-center mb-6">
                            <Bot size={48} className="text-emerald-500" />
                        </div>
                        <h2 className="text-2xl font-bold text-slate-800 mb-2">Testing Javiera IA</h2>
                        <p className="text-slate-500 max-w-sm text-center">Selecciona un chat en el panel izquierdo o usa el chat de prueba para ver el CRM en acción.</p>
                    </div>
                )}
            </div>

            {/* RIGHT BAR: Contact CRM Info */}
            {
                selectedContact && (
                    <div className={`
                    bg-white border-l border-slate-200 shadow-sm z-30 flex-col
                    ${mobileView === 'info' ? 'flex w-full absolute inset-0 md:static md:w-[320px] lg:w-[360px]' : 'hidden'}
                    ${showDesktopInfo ? 'xl:flex xl:w-[360px]' : ''}
                `}>
                        <div className="h-[72px] px-4 md:px-6 flex items-center border-b border-slate-100 gap-3">
                            <button
                                className="p-2 -ml-2 text-slate-500 hover:bg-slate-100 rounded-full md:hidden"
                                onClick={() => setMobileView('chat')}
                            >
                                <ArrowLeft size={20} />
                            </button>
                            <button
                                className="p-2 -ml-2 text-slate-500 hover:bg-slate-100 rounded-full hidden md:flex"
                                onClick={() => {
                                    setShowDesktopInfo(false);
                                    if (mobileView === 'info') setMobileView('chat');
                                }}
                            >
                                <ArrowLeft size={20} />
                            </button>
                            <h2 className="font-bold text-lg text-slate-800">Ficha del Cliente</h2>
                        </div>

                        <div className="p-6 overflow-y-auto space-y-8">
                            {/* Profile Hero */}
                            <div className="flex flex-col items-center pb-6 border-b border-slate-100 text-center">
                                <div className={`w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold text-white shadow-md mb-4
                                ${isTestContact ? 'bg-indigo-500' : 'bg-slate-300'}
                            `}>
                                    {isTestContact ? 'T' : <User size={40} />}
                                </div>
                                <h3 className="text-xl font-bold text-slate-900">{selectedContact.name || 'Sin Nombre'}</h3>
                                <p className="text-slate-500 flex items-center gap-2 mt-1"><Phone size={14} /> {selectedContact.phone_number}</p>
                            </div>

                            {/* Status Pipeline */}
                            <div>
                                <label className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-2.5 block">Pipeline de Ventas</label>
                                <select
                                    value={selectedContact.status}
                                    onChange={async (e) => {
                                        const s = e.target.value
                                        await supabase.from('contacts').update({ status: s }).eq('id', selectedContact.id)
                                        setSelectedContact({ ...selectedContact, status: s })
                                        setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, status: s } : c))
                                    }}
                                    className="w-full bg-slate-50 border border-slate-200 p-3 rounded-lg text-sm font-semibold text-slate-700 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-200 cursor-pointer hover:bg-slate-100 transition-colors"
                                >
                                    <option value="lead">🔵 Lead Nuevo</option>
                                    <option value="appointment">🟡 Cita Agendada</option>
                                    <option value="customer">🟢 Cliente Cerrado</option>
                                    <option value="lost">🔴 Perdido</option>
                                </select>
                            </div>

                            {/* Role Selector (TESTING ONLY) */}
                            {isTestContact && (
                                <div className="bg-indigo-50/50 rounded-xl p-4 border border-indigo-100">
                                    <label className="text-xs uppercase font-bold text-indigo-400 tracking-wider mb-2.5 block flex items-center gap-1.5">
                                        <Sparkles size={12} /> Rol del Contacto (Testeo)
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {['cliente', 'staff', 'admin'].map((r) => (
                                            <button
                                                key={r}
                                                onClick={async () => {
                                                    await supabase.from('contacts').update({ role: r }).eq('id', selectedContact.id)
                                                    setSelectedContact({ ...selectedContact, role: r })
                                                    setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, role: r } : c))
                                                }}
                                                className={`
                                                px-3 py-1.5 rounded-full text-[11px] font-bold uppercase transition-all border
                                                ${selectedContact.role === r
                                                        ? 'bg-indigo-600 text-white border-indigo-700 shadow-sm'
                                                        : 'bg-white text-indigo-600 border-indigo-200 hover:bg-indigo-50'
                                                    }
                                            `}
                                            >
                                                {r}
                                            </button>
                                        ))}
                                    </div>
                                    <p className="text-[10px] text-indigo-400 mt-2 font-medium">Define cómo responderá la IA (30 min vs 60 min).</p>
                                </div>
                            )}

                            {/* Bot Status */}
                            <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                                <label className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-3 block">Estado del Agente AI</label>
                                <div className="flex items-center justify-between">
                                    <span className={`flex items-center gap-2 text-sm font-bold ${selectedContact.bot_active ? 'text-emerald-600' : 'text-amber-600'}`}>
                                        {selectedContact.bot_active ? <Sparkles size={16} /> : <Pause size={16} />}
                                        {selectedContact.bot_active ? '🤖 Activo (Automático)' : '👨‍💻 Pausado (Manual)'}
                                    </span>
                                </div>
                                <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                                    {selectedContact.bot_active ? "La inteligencia artificial responderá los mensajes automáticamente." : "El bot ha sido interrumpido. Solo tú enviarás mensajes a la cuenta."}
                                </p>
                            </div>

                            {/* Meta Info */}
                            <div>
                                <label className="text-xs uppercase font-bold text-slate-400 tracking-wider mb-2 block">Metadatos</label>
                                <div className="bg-slate-50 rounded-lg p-3 space-y-2 border border-slate-100">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-slate-500">ID Fila</span>
                                        <span className="font-mono text-slate-700 truncate w-32 text-right">{selectedContact.id.split('-')[0]}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-slate-500 flex items-center gap-1"><Clock size={12} /> Última Actividad</span>
                                        <span className="font-medium text-slate-700">
                                            {selectedContact.last_message_at ? new Date(selectedContact.last_message_at).toLocaleDateString() : 'Nunca'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    )
}

```

--- FIN DE ARCHIVO: page.tsx ---

--- INICIO DE ARCHIVO: supabase.ts (Ruta: Frontend/lib/supabase.ts) ---

```typescript
import { createBrowserClient } from '@supabase/ssr'

export const createClient = () =>
    createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

```

--- FIN DE ARCHIVO: supabase.ts ---

--- INICIO DE ARCHIVO: next-env.d.ts (Ruta: Frontend/next-env.d.ts) ---

```typescript
/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/basic-features/typescript for more information.

```

--- FIN DE ARCHIVO: next-env.d.ts ---

--- INICIO DE ARCHIVO: package.json (Ruta: Frontend/package.json) ---

```json
{
  "name": "ai-whatsapp-crm",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@supabase/ssr": "^0.1.0",
    "@supabase/supabase-js": "^2.98.0",
    "clsx": "^2.1.0",
    "lucide-react": "^0.364.0",
    "next": "14.1.4",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "tailwind-merge": "^2.2.2"
  },
  "devDependencies": {
    "@types/node": "^20.11.30",
    "@types/react": "^18.2.73",
    "@types/react-dom": "^18.2.22",
    "autoprefixer": "^10.4.19",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.1.4",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5.4.3"
  }
}

```

--- FIN DE ARCHIVO: package.json ---

--- INICIO DE ARCHIVO: postcss.config.js (Ruta: Frontend/postcss.config.js) ---

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}

```

--- FIN DE ARCHIVO: postcss.config.js ---

--- INICIO DE ARCHIVO: tailwind.config.js (Ruta: Frontend/tailwind.config.js) ---

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}


```

--- FIN DE ARCHIVO: tailwind.config.js ---

--- INICIO DE ARCHIVO: tsconfig.json (Ruta: Frontend/tsconfig.json) ---

```json
{
  "compilerOptions": {
    "lib": [
      "dom",
      "dom.iterable",
      "esnext"
    ],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": false,
    "noEmit": true,
    "incremental": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": [
        "./*"
      ]
    }
  },
  "include": [
    "next-env.d.ts",
    ".next/types/**/*.ts",
    "**/*.ts",
    "**/*.tsx"
  ],
  "exclude": [
    "node_modules"
  ]
}
```

--- FIN DE ARCHIVO: tsconfig.json ---

