'use client'

import React from 'react'
import { ArrowLeft, User, Pause, Play, MoreVertical, Sparkles, Send, MessageCircle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useCrm } from '@/contexts/CrmContext'
import { createClient } from '@/lib/supabase'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

export default function ChatArea() {
    const { 
        selectedContact, setSelectedContact, messages, setMessages, 
        mobileView, setMobileView, showDesktopInfo, setShowDesktopInfo,
        isIAProcessing, setIsIAProcessing, newMessage, setNewMessage, contacts, setContacts,
        simulationMode
    } = useCrm()

    const messagesEndRef = React.useRef<HTMLDivElement>(null)

    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    if (!selectedContact) return (
        <div className="flex-1 hidden md:flex items-center justify-center bg-[#efeae2] relative overflow-hidden">
             <div className="absolute inset-0 opacity-5 pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/pinstripe-dark.png')]"></div>
             <div className="text-center space-y-4 relative z-10">
                 <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mx-auto shadow-sm">
                    <MessageCircle className="text-slate-200 w-12 h-12" />
                 </div>
                 <h2 className="text-slate-400 font-bold text-xl">Selecciona un chat para comenzar</h2>
             </div>
        </div>
    )

    const isTestContact = selectedContact.phone_number === '56912345678'

    const toggleBot = async () => {
        const newState = !selectedContact.bot_active
        const { error } = await supabase.from('contacts').update({ bot_active: newState }).eq('id', selectedContact.id)
        if (!error) {
            setSelectedContact({ ...selectedContact, bot_active: newState })
            setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, bot_active: newState } : c))
        }
    }

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newMessage.trim()) return
        
        const text = newMessage.trim()
        setNewMessage('')
        
        // Optimistic update
        const tempMsg = { 
            id: 'temp-' + Date.now(), 
            content: text, 
            sender_role: (simulationMode && isTestContact) ? 'user' : 'human_agent', 
            timestamp: new Date().toISOString() 
        }
        setMessages([...messages, tempMsg])

        const sender_role = (simulationMode && isTestContact) ? 'user' : 'human_agent'

        // DB Insert (PERMANENCE)
        const { error: dbErr } = await supabase.from('messages').insert({
            contact_id: selectedContact.id,
            tenant_id: selectedContact.tenant_id,
            content: text,
            sender_role: sender_role
        })

        if (dbErr) {
            console.error("Error saving message:", dbErr)
            Sentry.captureMessage(`Error saving message to DB: ${JSON.stringify(dbErr)}`, 'error')
            return
        }

        if (simulationMode && isTestContact) {
            // Trigger Backend Simulation
            setIsIAProcessing(true)
            try {
                const baseUrl = 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'
                const res = await fetch(`${baseUrl}/api/simulate`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        phone: selectedContact.phone_number,
                        message: text,
                        tenantId: selectedContact.tenant_id
                    })
                })
                if (!res.ok) throw new Error("Simulation failed")
            } catch (err) {
                console.error("Simulation trigger failed:", err)
                Sentry.captureException(err as Error)
                setIsIAProcessing(false)
            }
        }
    }

    const formatWhatsAppText = (text: string) => {
        if (!text) return '';
        // Convert Markdown ** to WhatsApp *
        let processedText = text.replace(/\*\*/g, '*');
        
        const lines = processedText.split('\n').map((line, i) => {
            if (line.trim().startsWith('>')) {
                return (
                    <blockquote key={i} className="border-l-4 border-slate-300 pl-3 py-1 my-2 bg-slate-50/50 italic text-slate-600 rounded-r">
                        {line.trim().substring(1).trim()}
                    </blockquote>
                );
            }
            if (line.trim().startsWith('* ') || line.trim().startsWith('- ')) {
                 return <li key={i} className="ml-4 list-disc marker:text-emerald-500">{line.trim().substring(2).trim()}</li>
            }
            
            // Handle *, _, ~ inline
            const parts = line.split(/(\*[^*]+\*|_[^_]+_|~[^~]+~)/g);
            return (
                <div key={i} className="min-h-[1em]">
                    {parts.map((part, j) => {
                        if (part.startsWith('*') && part.endsWith('*')) {
                            return <strong key={j} className="font-bold text-inherit">{part.slice(1, -1)}</strong>;
                        }
                        if (part.startsWith('_') && part.endsWith('_')) {
                            return <em key={j}>{part.slice(1, -1)}</em>;
                        }
                        if (part.startsWith('~') && part.endsWith('~')) {
                            return <del key={j} className="opacity-70">{part.slice(1, -1)}</del>;
                        }
                        return part;
                    })}
                </div>
            );
        });
        return lines;
    };

    return (
        <div
            className={`
                flex-col relative bg-cover bg-center flex-1 h-full
                ${mobileView === 'chat' ? 'flex w-full absolute inset-0 z-[60] md:static md:w-auto md:z-auto md:inset-auto' : 'hidden md:flex'}
            `}
            style={{ backgroundColor: '#efeae2' }}
        >
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
                        ${isTestContact ? 'bg-indigo-600' : 'bg-emerald-500'}
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
                    {isTestContact && simulationMode && (
                        <div className="flex justify-center mb-6">
                            <button 
                                onClick={async () => {
                                    const roles = ['cliente', 'staff', 'admin'];
                                    const currentIdx = roles.indexOf(selectedContact.role || 'cliente');
                                    const nextRole = roles[(currentIdx + 1) % roles.length];
                                    const { error } = await supabase.from('contacts').update({ role: nextRole }).eq('id', selectedContact.id);
                                    if (!error) {
                                        const updated = { ...selectedContact, role: nextRole };
                                        setSelectedContact(updated);
                                        setContacts(contacts.map(c => c.id === selectedContact.id ? updated : c));
                                    }
                                }}
                                className="bg-indigo-600 text-white text-[11px] px-6 py-2 rounded-full shadow-lg font-black uppercase tracking-widest flex items-center gap-3 border-2 border-indigo-400/50 hover:bg-indigo-700 hover:scale-105 active:scale-95 transition-all"
                            >
                                <Sparkles size={16} className="text-white animate-pulse" />
                                TU ROL: {selectedContact.role === 'admin' ? 'ADMINISTRADOR' : selectedContact.role === 'staff' ? 'STAFF' : 'USUARIO / PACIENTE'}
                                <Badge className="bg-white/20 text-[9px] hover:bg-white/30 border-none shrink-0 ml-2">TAP PARA CAMBIAR</Badge>
                            </button>
                        </div>
                    )}

                    {messages.map((m, idx) => {
                        const isUserMessage = m.sender_role === 'user' || m.sender_role === 'cliente'
                        const isAI = m.sender_role === 'assistant'
                        const isHumanAgent = m.sender_role === 'human_agent' || m.sender_role === 'staff' || m.sender_role === 'admin'
                        const isSystemAlert = m.sender_role === 'system_alert'

                        const isTestingChat = selectedContact?.phone_number === '56912345678'
                        const isAlertChat = selectedContact?.name === 'Alertas Sistema 🚨' || selectedContact?.phone_number === '+56999999999'

                        let bubbleClasses = "max-w-[75%] px-4 py-2.5 rounded-2xl shadow-sm text-[15px] relative "
                        let alignments = ""

                        if (isTestingChat || isAlertChat) {
                            if (isUserMessage || isHumanAgent) {
                                alignments = "justify-end"
                                bubbleClasses += isHumanAgent ? "bg-blue-100 text-blue-900 border border-blue-200 rounded-tr-[4px]" : "bg-[#d9fdd3] text-[#111b21] rounded-tr-[4px] border border-green-100/50"
                            } else if (isAI || isSystemAlert) {
                                alignments = "justify-start"
                                bubbleClasses += "bg-white text-slate-800 rounded-tl-[4px] border border-slate-100"
                                if (isSystemAlert) {
                                    bubbleClasses += " border-l-4 border-l-red-500 bg-red-50 text-red-900"
                                }
                            } else {
                                alignments = "justify-start"
                                bubbleClasses += "bg-white text-slate-800 rounded-tl-[4px] border border-slate-100"
                            }
                        } else {
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
                                    <div className={`text-[10px] font-bold uppercase tracking-wider ${alignments === 'justify-end' ? 'mr-1' : 'ml-1'}
                                        ${isAI ? 'text-emerald-600' : isHumanAgent ? 'text-blue-500' : isSystemAlert ? 'text-red-500' : 'text-slate-400'}
                                    `}>
                                        {isAI ? '🤖 Asistente' : isHumanAgent ? '👨‍💻 Staff' : isSystemAlert ? '🚨 Alerta del Sistema' : '👤 ' + (selectedContact.name || 'Paciente')}
                                    </div>
                                    <div className={bubbleClasses}>
                                        <div className="whitespace-pre-wrap leading-relaxed">
                                            {formatWhatsAppText(m.content)}
                                        </div>
                                        <span className={`text-[10px] block mt-1.5 opacity-60 text-right ${alignments === 'justify-end' ? 'text-emerald-900' : 'text-slate-500'}`}>
                                            {m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )
                    })}

                    {isIAProcessing && selectedContact.bot_active && (
                         <div className="flex w-full justify-start">
                             <div className="flex flex-col gap-1 items-start">
                                 <div className="text-[10px] font-bold uppercase tracking-wider ml-1 text-emerald-600">🤖 Asistente</div>
                                 <div className="bg-white px-4 py-3 rounded-2xl shadow-sm border border-slate-100 flex items-center gap-2">
                                     <div className="flex gap-1.5 h-2 items-center">
                                         <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                                         <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                         <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce"></div>
                                     </div>
                                     <span className="text-xs font-bold text-slate-400">Pensando...</span>
                                 </div>
                             </div>
                         </div>
                    )}

                    <div ref={messagesEndRef} className="h-4" />
                </div>
            </div>

            {/* Input Bar */}
            <form onSubmit={handleSendMessage} className={`
                bg-[#f0f2f5] px-3 md:px-5 py-3 md:py-4 flex gap-2 md:gap-3 items-center z-20 pb-safe relative flex-shrink-0
                ${!selectedContact.bot_active && !isTestContact ? 'border-t-4 border-amber-400' : ''}
                pb-[env(safe-area-inset-bottom,16px)] md:pb-4
            `}>
                {!selectedContact.bot_active && !isTestContact && (
                    <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-amber-400 text-amber-900 text-[10px] font-bold px-4 py-1 rounded-t-lg flex items-center gap-1 shadow-sm">
                        <Pause size={10} className="fill-current" /> INTERVENCIÓN MANUAL ACTIVADA
                    </div>
                )}
                <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden outline-none focus-within:ring-2 focus-within:ring-emerald-500 transition-shadow">
                    <input
                        type="text"
                        value={newMessage}
                        onChange={(e) => setNewMessage(e.target.value)}
                        placeholder={isTestContact && simulationMode ? "Escribe como si fueras el PACIENTE..." : "Escribe un mensaje al paciente..."}
                        className="w-full bg-transparent px-4 py-3 md:py-3.5 text-sm md:text-[15px] outline-none placeholder:text-slate-400"
                    />
                </div>
                <button
                    type="submit"
                    disabled={!newMessage.trim()}
                    className={`w-12 h-12 md:w-12 md:h-12 text-white rounded-full flex items-center justify-center shadow-lg transition-transform active:scale-95 disabled:opacity-50 disabled:active:scale-100 flex-shrink-0
                        ${simulationMode && isTestContact ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-emerald-600 hover:bg-emerald-700'}
                    `}
                >
                    <Send size={18} className="translate-x-[-1px] translate-y-[1px]" />
                </button>
            </form>
        </div>
    )
}
