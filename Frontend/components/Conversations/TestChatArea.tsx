'use client'

import React from 'react'
import { ArrowLeft, User, Pause, Play, MoreVertical, Sparkles, Send, MessageCircle, X, Trash2, Settings, MoreHorizontal } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useCrm } from '@/contexts/CrmContext'
import { createClient } from '@/lib/supabase'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Button } from "@/components/ui/button"

const supabase = createClient()

export default function TestChatArea() {
    const { 
        selectedContact, setSelectedContact, messages, setMessages, 
        mobileView, setMobileView, showDesktopInfo, setShowDesktopInfo,
        isIAProcessing, setIsIAProcessing, newMessage, setNewMessage, contacts, setContacts,
        simulationMode, setToasts
    } = useCrm()

    const messagesEndRef = React.useRef<HTMLDivElement>(null)
    const [noteInputId, setNoteInputId] = React.useState<string | null>(null)
    const [noteValue, setNoteValue] = React.useState("")
    const [localNotes, setLocalNotes] = React.useState<Record<string, string>>({})

    // Load notes from localStorage on mount
    React.useEffect(() => {
        const saved = localStorage.getItem('sandbox_notes')
        if (saved) {
            try {
                setLocalNotes(JSON.parse(saved))
            } catch (e) {
                console.error("Error parsing saved notes", e)
            }
        }
    }, [])

    // Sync messages with local notes
    const augmentedMessages = React.useMemo(() => {
        return messages.map(m => ({
            ...m,
            note: localNotes[m.id] || m.note || ""
        }))
    }, [messages, localNotes])

    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    if (!selectedContact) return null

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newMessage.trim()) return
        
        const text = newMessage.trim()
        setNewMessage('')
        
        // Aislamiento: El CrmContext maneja la inserción vía Realtime.
        // No agregamos localmente para evitar el doble registro.
        
        // Persistencia Sandbox
        try {
            const { error } = await supabase.from('messages').insert({
                contact_id: selectedContact.id,
                tenant_id: selectedContact.tenant_id,
                content: text,
                sender_role: 'user'
            })
            if (error) console.error("Error inserting message:", error)
        } catch (err) {
            console.error("Supabase error:", err)
        }

        // Trigger Simulation
        setIsIAProcessing(true)
        
        // Safety timeout to clear "generating" state after 30s 
        const timeout = setTimeout(() => {
            setIsIAProcessing(false)
        }, 30000)

        try {
            const baseUrl = 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'
            await fetch(`${baseUrl}/api/simulate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    phone: selectedContact.phone_number,
                    message: text,
                    tenantId: selectedContact.tenant_id
                })
            })
        } catch (err) {
            console.error(err)
            setIsIAProcessing(false)
        } finally {
            clearTimeout(timeout)
        }
    }

    const toggleBot = async () => {
        const newState = !selectedContact.bot_active
        const { error } = await supabase.from('contacts').update({ bot_active: newState }).eq('id', selectedContact.id)
        if (!error) {
            setSelectedContact({ ...selectedContact, bot_active: newState })
            setContacts(contacts.map((c: any) => c.id === selectedContact.id ? { ...c, bot_active: newState } : c))
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: newState ? 'Asistente reanudado ▶️' : 'Asistente pausado ⏸️' } }])
        } else {
            console.error("Error toggling bot:", error)
        }
    }

    const handleSendTest = async () => {
        console.log("[Sandbox] Preparando envío de prueba al equipo de desarrollo...");
        
        // Recopilar feedbacks y mensajes íntegros
        const history = augmentedMessages.map(m => ({
            role: m.sender_role,
            content: m.content
        }))
        
        const notes = augmentedMessages.filter(m => m.note).map(m => ({
            id: m.id,
            content: m.content,
            note: m.note
        }))

        try {
            const baseUrl = 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'
            const response = await fetch(`${baseUrl}/api/test-feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tenant_id: selectedContact.tenant_id,
                    patient_phone: selectedContact.phone_number,
                    history: history,
                    notes: notes,
                    tester_email: 'tomasgemes@gmail.com'
                })
            })
            
            const result = await response.json()
            console.log("[Sandbox] Respuesta exitosa del backend:", result);
            if (!response.ok) throw new Error(result.message || 'Error en el servidor')

            // Reset
            setMessages([])
            setLocalNotes({})
            localStorage.removeItem('sandbox_notes')
            // Limpiar historial en DB para este contacto (Opcional, pero para sandbox es mejor)
            await supabase.from('messages').delete().eq('contact_id', selectedContact.id)
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: 'Prueba enviada y sandbox reseteado ✅' } }])
        } catch (err) {
            console.error("[Sandbox] Hubo un error procesando el feedback:", err);
            const msg = (err as Error).message;
            if (msg.includes('relation "public.test_feedback" does not exist') || msg.includes('test_feedback')) {
                 setToasts(prev => [...prev, { id: Date.now(), payload: { content: '❌ Falla crítica: La tabla test_feedback no existe en la BD. Debes ejecutar el script SQL.' } }]);
            } else {
                 setToasts(prev => [...prev, { id: Date.now(), payload: { content: `Error enviando prueba: ${msg}` } }]);
            }
        }
    }

    const handleDiscard = () => {
        if(confirm("¿Seguro que quieres descartar esta prueba?")) {
            setMessages([])
        }
    }

    const handleNoteSave = (msgId: string) => {
        const newNotes = { ...localNotes, [msgId]: noteValue }
        setLocalNotes(newNotes)
        localStorage.setItem('sandbox_notes', JSON.stringify(newNotes))
        console.log(`[Sandbox] Nota agregada localmente al msj ${msgId}: ${noteValue}`);
        setToasts(prev => [...prev, { id: Date.now(), payload: { content: 'Nota agregada al registro 📝' } }])
        setNoteInputId(null)
        setNoteValue("")
    }

    const formatWhatsAppText = (text: string) => {
        if (!text) return '';
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
        <div className="flex-col relative bg-[#efeae2] flex-1 flex h-full overflow-hidden">
            {/* Globo Flotante de Rol */}
            <div className="absolute top-20 left-1/2 -translate-x-1/2 z-[50]">
                <div className="bg-indigo-600 text-white text-[10px] font-black px-4 py-1 rounded-full shadow-xl border border-indigo-400/30 tracking-widest animate-in fade-in slide-in-from-top-1">
                    {selectedContact.role ? selectedContact.role.toUpperCase() : 'CLIENTE'}
                </div>
            </div>

            {/* Header Mini */}
            <div className="h-[72px] bg-white border-b flex items-center px-4 md:px-6 justify-between shrink-0 z-10">
                <div className="flex items-center gap-2 md:gap-3">
                    {/* Botón Volver (Mobile) */}
                    <button 
                        onClick={() => setMobileView('list')}
                        className="lg:hidden p-2 hover:bg-slate-100 rounded-full text-slate-600"
                    >
                        <ArrowLeft size={20} />
                    </button>

                    <div className="w-9 h-9 md:w-10 md:h-10 bg-indigo-600 rounded-full flex items-center justify-center text-white font-bold">
                        <Sparkles size={18} />
                    </div>
                    <div>
                        <h3 className="font-bold text-slate-800 text-sm md:text-base whitespace-nowrap">Sandbox Auditoría</h3>
                        <div className="text-[9px] md:text-[10px] text-slate-400 font-bold uppercase tracking-tighter">Entorno Aislado</div>
                    </div>
                </div>

                <div className="flex items-center gap-1">
                    {/* Botón Pausa/Reanudar */}
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            toggleBot();
                        }}
                        className={`
                            hide-on-mobile flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-black uppercase transition-all border
                            ${selectedContact.bot_active
                                ? 'bg-amber-50 text-amber-600 border-amber-200 hover:bg-amber-100'
                                : 'bg-emerald-50 text-emerald-600 border-emerald-200 hover:bg-emerald-100'
                            }
                        `}
                    >
                        {selectedContact.bot_active ? <Pause size={16} className="fill-current" /> : <Play size={16} className="fill-current" />}
                        <span className="hidden sm:inline">{selectedContact.bot_active ? 'Pausar IA' : 'Activar IA'}</span>
                    </button>

                    {/* Botón Config (Mobile/Desktop Toggle) */}
                    <button 
                        onClick={() => {
                            if (window.innerWidth < 1024) {
                                setMobileView('info')
                            } else {
                                setShowDesktopInfo(!showDesktopInfo)
                            }
                        }}
                        className="p-2.5 hover:bg-slate-100 rounded-xl text-slate-600 flex items-center gap-2 transition-colors border border-transparent hover:border-slate-200"
                    >
                        <Settings size={20} />
                        <span className="hidden md:inline text-xs font-black uppercase tracking-widest">Config</span>
                    </button>
                    
                    <button className="p-2.5 hover:bg-slate-100 rounded-xl text-slate-400">
                        <MoreVertical size={20} />
                    </button>
                </div>
            </div>

            {/* Area de Mensajes */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {augmentedMessages.map((m, idx) => {
                    const isAI = m.sender_role === 'assistant'
                    const isUser = m.sender_role === 'user'
                    
                    return (
                        <div key={m.id || idx} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                            <div className={`relative group max-w-[75%] px-4 py-3 rounded-2xl shadow-sm text-[14px] 
                                ${isUser ? 'bg-[#d9fdd3] rounded-tr-none' : 'bg-white rounded-tl-none'}
                            `}>
                                {/* Indicador Visual de Nota */}
                                {m.note && (
                                    <TooltipProvider>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <div className="absolute bottom-[-4px] right-[-4px] w-4 h-4 bg-yellow-400 border-2 border-white rounded-full cursor-pointer shadow-sm hover:scale-110 transition-transform" />
                                            </TooltipTrigger>
                                            <TooltipContent className="bg-slate-900 text-white max-w-xs p-2 text-xs">
                                                {m.note}
                                            </TooltipContent>
                                        </Tooltip>
                                    </TooltipProvider>
                                )}

                                <div className="break-words" onClick={() => {
                                    if(isAI) {
                                        setNoteInputId(m.id)
                                        setNoteValue(m.note || "")
                                    }
                                }}>
                                    {formatWhatsAppText(m.content)}
                                    <div className="text-[9px] text-slate-500/70 text-right mt-1 font-medium tracking-tighter">
                                        {m.timestamp ? new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
                                    </div>
                                </div>

                                {noteInputId === m.id && (
                                    <div className="mt-2 pt-2 border-t flex flex-col gap-2">
                                        <textarea 
                                            className="w-full text-xs p-2 border rounded outline-none focus:ring-1 ring-yellow-400"
                                            value={noteValue}
                                            onChange={(e) => setNoteValue(e.target.value)}
                                            placeholder="Escribe una observación para el equipo dev..."
                                            autoFocus
                                        />
                                        <div className="flex gap-2 justify-end">
                                            <Button size="sm" variant="ghost" onClick={() => setNoteInputId(null)}>Cerrar</Button>
                                            <Button size="sm" className="bg-yellow-500 hover:bg-yellow-600 text-white" onClick={() => handleNoteSave(m.id)}>Guardar Nota</Button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )
                })}
                {isIAProcessing && (
                    <div className="flex justify-start">
                        <div className="bg-white px-4 py-3 rounded-2xl border flex items-center gap-2">
                            <div className="flex gap-1">
                                <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce"></div>
                                <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                                <div className="w-1.5 h-1.5 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                            </div>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">IA Generando...</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Barra Inferior Sandbox */}
            <div className="bg-[#f0f2f5] p-5 pb-24 lg:pb-5 space-y-4 shrink-0 border-t z-20">
                <form onSubmit={handleSendMessage} className="flex gap-3 items-center">
                    <div className="flex-1 bg-white rounded-xl shadow-sm border focus-within:ring-2 ring-indigo-500 transition-all overflow-hidden">
                        <input 
                            value={newMessage}
                            onChange={e => setNewMessage(e.target.value)}
                            placeholder="Escribe como si fueras el CLIENTE..."
                            className="w-full px-4 py-3 text-sm outline-none"
                        />
                    </div>
                    <button type="submit" className="w-12 h-12 bg-indigo-600 text-white rounded-full flex items-center justify-center shadow-lg hover:scale-105 transition-transform active:scale-95">
                        <Send size={18} />
                    </button>
                </form>

                {/* Fila de Acciones Rápidas */}
                <div className="flex flex-wrap gap-2 justify-center">
                    <Button variant="outline" size="sm" className="bg-white border-red-200 text-red-600 hover:bg-red-50 text-[10px] h-8 font-bold" onClick={handleDiscard}>
                        <Trash2 size={14} className="mr-1" /> DESCARTAR PRUEBA
                    </Button>
                    <Button variant="outline" size="sm" className="bg-white border-green-200 text-green-600 hover:bg-green-50 text-[10px] h-8 font-bold" onClick={handleSendTest}>
                        <Send size={14} className="mr-1" /> ENVIAR PRUEBA (FINALIZAR)
                    </Button>
                    <Button variant="outline" size="sm" className="bg-white text-indigo-600 text-[10px] h-8 font-bold">
                        <Sparkles size={14} className="mr-1" /> CAMBIAR MODELO
                    </Button>
                    <Button variant="outline" size="sm" className="bg-white text-slate-600 text-[10px] h-8 font-bold" onClick={() => setShowDesktopInfo(true)}>
                        <Settings size={14} className="mr-1" /> CONFIGURACIÓN
                    </Button>
                    <Button variant="outline" size="sm" className="bg-white text-slate-600 text-[10px] h-8 font-bold">
                        <MoreHorizontal size={14} className="mr-1" /> MÁS OPCIONES
                    </Button>
                </div>
            </div>
        </div>
    )
}
