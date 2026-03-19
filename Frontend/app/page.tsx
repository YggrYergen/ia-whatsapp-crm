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
    const messagesEndRef = useRef<HTMLDivElement>(null)

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
