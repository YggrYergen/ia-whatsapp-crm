'use client'

import React from 'react'
import { Search, Sparkles, User, Play, Pause, Inbox } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { useCrm } from '@/contexts/CrmContext'

const supabase = createClient()

export default function ContactList() {
    const { 
        contacts, setContacts, selectedContact, setSelectedContact, 
        simulationMode, setSimulationMode, mobileView, setMobileView,
        isLoadingAuth, setMessages, dashboardRole
    } = useCrm()

    const fetchMessages = async (id: string) => {
        const { data } = await supabase.from('messages').select('*').eq('contact_id', id).order('timestamp', { ascending: true })
        if (data) setMessages(data)
    }

    if (isLoadingAuth) {
        return (
            <div className={`
                bg-white border-r border-slate-200 flex-col flex-shrink-0 z-10 w-full h-full relative
                ${mobileView === 'list' ? 'flex absolute inset-0 md:static md:w-[320px] lg:w-[380px]' : 'hidden md:flex md:w-[320px] lg:w-[380px]'}
            `}>
                <div className="h-[72px] bg-white px-4 md:px-5 flex items-center border-b border-slate-100 flex-shrink-0">
                    <Skeleton className="h-10 w-full rounded-xl" />
                </div>
                <div className="flex-1 p-4 space-y-4">
                    {[1, 2, 3, 4, 5, 6].map(i => (
                        <div key={i} className="flex items-center gap-4">
                            <Skeleton className="h-12 w-12 rounded-full" />
                            <div className="space-y-2 flex-1">
                                <Skeleton className="h-4 w-[60%]" />
                                <Skeleton className="h-3 w-[40%]" />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className={`
            bg-white border-r border-slate-200 flex-col flex-shrink-0 z-10 w-full h-full relative
            ${mobileView === 'list' ? 'flex absolute inset-0 md:static md:w-[320px] lg:w-[380px]' : 'hidden md:flex md:w-[320px] lg:w-[380px]'}
        `}>
            {/* Header / Search */}
            <div className="h-[72px] bg-white px-4 md:px-5 flex items-center justify-between border-b border-slate-100 flex-shrink-0 sticky top-0 z-20">
                <div className="relative w-full">
                    <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input type="text" placeholder="Buscar conversaciones..." className="w-full bg-slate-100/80 border-none rounded-xl pl-10 pr-4 py-2.5 outline-none focus:ring-2 focus:ring-emerald-500 text-sm font-medium transition-shadow placeholder:text-slate-400" />
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto w-full custom-scrollbar pb-[80px] md:pb-0">
                
                {/* CHAT DE PRUEBAS AISLADO (Solo Admins) */}
                {dashboardRole === 'admin' && contacts.find(c => c.phone_number === '56912345678') && (
                    <div className="mb-2 border-b-4 border-slate-100">
                        {(() => {
                            const testContact = contacts.find(c => c.phone_number === '56912345678');
                            if (!testContact) return null;
                            const isSelected = selectedContact?.id === testContact.id;
                            return (
                                <div onClick={() => { setSelectedContact(testContact); fetchMessages(testContact.id); setMobileView('chat'); setSimulationMode(true); }}
                                     className={`flex items-center p-3 md:p-4 cursor-pointer transition-all relative overflow-hidden ${isSelected ? 'bg-indigo-100 border-l-4 border-l-indigo-600' : 'bg-white hover:bg-indigo-50 border-l-4 border-l-transparent'}`}>
                                    <div className="w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg text-white shadow-sm bg-indigo-600 flex-shrink-0">T</div>
                                    <div className="ml-3 flex-1 min-w-0 pr-6">
                                        <span className="font-black text-[15px] text-indigo-900 truncate">Chat de pruebas</span>
                                        <p className="text-xs text-indigo-500 font-medium tracking-tight">Simulador de Agendamiento</p>
                                    </div>
                                    <Sparkles size={20} className="absolute right-4 text-indigo-300 opacity-50" />
                                </div>
                            )
                        })()}
                    </div>
                )}

                {/* LISTA NORMAL DE CLIENTES */}
                <div className="px-4 py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest bg-white sticky top-0 z-10 border-b border-slate-50">
                    Pacientes y Leads
                </div>

                {contacts.filter(c => c.phone_number !== '56912345678').length === 0 ? (
                    <div className="p-8 text-center text-slate-400 text-sm space-y-4">
                        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto text-slate-300">
                            <Inbox size={32} />
                        </div>
                        <p>No hay conversaciones activas.</p>
                    </div>
                ) : (
                    <div className="flex flex-col">
                        {contacts.filter(c => c.phone_number !== '56912345678').map((c) => {
                            const isSelected = selectedContact?.id === c.id
                            const isAlertSystem = c.name === 'Alertas Sistema 🚨' || c.phone_number === '+56999999999'
                            return (
                                <div 
                                    key={c.id} 
                                    onClick={() => { setSelectedContact(c); fetchMessages(c.id); setMobileView('chat'); setSimulationMode(false); }}
                                    className={`
                                        flex items-center p-3 md:p-4 cursor-pointer transition-all border-b border-slate-50 group hover:bg-slate-50 relative overflow-hidden
                                        ${isSelected ? 'bg-emerald-50/50 border-l-4 border-l-emerald-500' : 'border-l-4 border-l-transparent'}
                                    `}
                                >
                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center font-bold text-lg text-white shadow-sm flex-shrink-0
                                        ${isAlertSystem ? 'bg-rose-500' : 'bg-slate-200 text-slate-500'}
                                    `}>
                                        {isAlertSystem ? '🚨' : <User size={24} />}
                                    </div>
                                    <div className="ml-3 flex-1 min-w-0 pr-6">
                                        <div className="flex justify-between items-center mb-0.5">
                                            <span className={`font-bold text-[15px] truncate ${isSelected ? 'text-emerald-900' : 'text-slate-800'}`}>{c.name || c.phone_number}</span>
                                            <span className="text-[11px] font-bold text-slate-400 flex-shrink-0">
                                                {c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                            </span>
                                        </div>
                                        <div className="text-[13px] text-slate-500 truncate font-medium capitalize flex items-center gap-2">
                                            {c.status}
                                            {c.bot_active && <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>}
                                        </div>
                                    </div>
                                    
                                    {/* Bot Toggle Shortcut */}
                                    <button
                                        onClick={async (e) => {
                                            e.stopPropagation()
                                            const newState = !c.bot_active
                                            await supabase.from('contacts').update({ bot_active: newState }).eq('id', c.id);
                                        }}
                                        className={`absolute bottom-3 right-3 w-5 h-5 rounded-full flex items-center justify-center shadow-md transition-transform flex-shrink-0 hover:scale-110 active:scale-95
                                            ${c.bot_active ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-white'}
                                        `}
                                    >
                                        {c.bot_active ? <Play size={8} className="fill-current ml-[1px]" /> : <Pause size={8} className="fill-current" />}
                                    </button>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
