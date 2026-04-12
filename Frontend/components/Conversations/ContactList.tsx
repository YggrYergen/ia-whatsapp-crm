'use client'

import React, { useState, useMemo } from 'react'
import { Search, Sparkles, User, Play, Pause, Inbox, AlertTriangle, Filter, MessageCircle } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { useCrm } from '@/contexts/CrmContext'

const supabase = createClient()

type FilterTab = 'all' | 'escalated' | 'active'

export default function ContactList() {
    const { 
        contacts, setContacts, selectedContact, setSelectedContact, 
        simulationMode, setSimulationMode, mobileView, setMobileView,
        isLoadingAuth, setMessages, dashboardRole
    } = useCrm()

    const [searchQuery, setSearchQuery] = useState('')
    const [activeFilter, setActiveFilter] = useState<FilterTab>('all')

    const fetchMessages = async (id: string) => {
        const { data } = await supabase.from('messages').select('*').eq('contact_id', id).order('timestamp', { ascending: true })
        if (data) setMessages(data)
    }

    // Sort: escalated first (bot_active=false), then by last_message_at descending
    const sortedContacts = useMemo(() => {
        let filtered = contacts.filter(c => c.phone_number !== '56912345678')
        
        // Search filter
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase()
            filtered = filtered.filter(c => 
                (c.name || '').toLowerCase().includes(q) || 
                c.phone_number.includes(q)
            )
        }

        // Tab filter
        if (activeFilter === 'escalated') {
            filtered = filtered.filter(c => !c.bot_active)
        } else if (activeFilter === 'active') {
            filtered = filtered.filter(c => c.bot_active)
        }

        return filtered.sort((a, b) => {
            // Escalated contacts ALWAYS on top
            if (!a.bot_active && b.bot_active) return -1
            if (a.bot_active && !b.bot_active) return 1
            // Within same group, sort by last message (most recent first)
            const aTime = a.last_message_at ? new Date(a.last_message_at).getTime() : 0
            const bTime = b.last_message_at ? new Date(b.last_message_at).getTime() : 0
            return bTime - aTime
        })
    }, [contacts, searchQuery, activeFilter])

    const escalatedCount = contacts.filter(c => c.phone_number !== '56912345678' && !c.bot_active).length

    if (isLoadingAuth) {
        return (
            <div className="bg-white border-r border-slate-200 flex-col flex-shrink-0 z-10 w-full h-full relative flex">
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
        <div className="bg-white border-r border-slate-200 flex-col flex-shrink-0 z-10 w-full h-full relative flex">
            {/* Header / Search */}
            <div className="bg-white px-4 md:px-5 pt-4 pb-2 border-b border-slate-100 flex-shrink-0 sticky top-0 z-20 space-y-3">
                <div className="relative w-full">
                    <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input 
                        type="text" 
                        placeholder="Buscar conversaciones..." 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full bg-slate-100/80 border-none rounded-xl pl-10 pr-4 py-2.5 outline-none focus:ring-2 focus:ring-emerald-500 text-sm font-medium transition-shadow placeholder:text-slate-400" 
                    />
                </div>
                
                {/* Filter Tabs */}
                <div className="flex gap-1.5">
                    <button 
                        onClick={() => setActiveFilter('all')}
                        className={`flex-1 py-1.5 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all
                            ${activeFilter === 'all' ? 'bg-slate-900 text-white shadow-sm' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                    >
                        Todos
                    </button>
                    <button 
                        onClick={() => setActiveFilter('escalated')}
                        className={`flex-1 py-1.5 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5
                            ${activeFilter === 'escalated' ? 'bg-rose-500 text-white shadow-sm' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                    >
                        <AlertTriangle size={12} />
                        Pendientes
                        {escalatedCount > 0 && (
                            <span className={`min-w-[18px] h-[18px] rounded-full text-[10px] font-black flex items-center justify-center animate-badge-pop
                                ${activeFilter === 'escalated' ? 'bg-white text-rose-500' : 'bg-rose-500 text-white'}`}>
                                {escalatedCount}
                            </span>
                        )}
                    </button>
                    <button 
                        onClick={() => setActiveFilter('active')}
                        className={`flex-1 py-1.5 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all
                            ${activeFilter === 'active' ? 'bg-emerald-500 text-white shadow-sm' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                    >
                        Activos
                    </button>
                </div>
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto w-full custom-scrollbar pb-4">
                
                {/* CHAT DE PRUEBAS AISLADO (Solo Admins) */}
                {dashboardRole === 'admin' && activeFilter !== 'escalated' && contacts.find(c => c.phone_number === '56912345678') && (
                    <div className="mb-1 border-b-2 border-slate-100">
                        {(() => {
                            const testContact = contacts.find(c => c.phone_number === '56912345678');
                            if (!testContact) return null;
                            const isSelected = selectedContact?.id === testContact.id;
                            return (
                                <div onClick={() => { setSelectedContact(testContact); fetchMessages(testContact.id); setMobileView('chat'); setSimulationMode(true); }}
                                     className={`flex items-center p-3 md:p-4 cursor-pointer transition-all relative overflow-hidden ${isSelected ? 'bg-indigo-100 border-l-4 border-l-indigo-600' : 'bg-white hover:bg-indigo-50 border-l-4 border-l-transparent'}`}>
                                    <div className="w-11 h-11 rounded-full flex items-center justify-center font-bold text-lg text-white shadow-sm bg-indigo-600 flex-shrink-0">T</div>
                                    <div className="ml-3 flex-1 min-w-0 pr-6">
                                        <span className="font-black text-[15px] text-indigo-900 truncate block">Chat de pruebas</span>
                                        <p className="text-xs text-indigo-500 font-medium tracking-tight">Simulador de Agendamiento</p>
                                    </div>
                                    <Sparkles size={20} className="absolute right-4 text-indigo-300 opacity-50" />
                                </div>
                            )
                        })()}
                    </div>
                )}

                {/* Section Label */}
                {escalatedCount > 0 && activeFilter !== 'active' && (
                    <div className="px-4 py-2 text-[10px] font-black text-rose-500 uppercase tracking-widest bg-rose-50/50 sticky top-0 z-10 border-b border-rose-100 flex items-center gap-2">
                        <AlertTriangle size={11} />
                        {activeFilter === 'escalated' ? `${escalatedCount} conversaciones pendientes` : `${escalatedCount} requieren atención`}
                    </div>
                )}

                {sortedContacts.length === 0 ? (
                    <div className="p-8 text-center text-slate-400 text-sm space-y-4">
                        <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto text-slate-300">
                            {activeFilter === 'escalated' ? <AlertTriangle size={32} /> : <Inbox size={32} />}
                        </div>
                        <p>{activeFilter === 'escalated' ? 'No hay conversaciones pendientes 🎉' : 'No hay conversaciones activas.'}</p>
                    </div>
                ) : (
                    <div className="flex flex-col">
                        {sortedContacts.map((c) => {
                            const isSelected = selectedContact?.id === c.id
                            const isAlertSystem = c.name === 'Alertas Sistema 🚨' || c.phone_number === '+56999999999'
                            const isEscalated = !c.bot_active
                            const timeSinceLastMessage = c.last_message_at 
                                ? Math.floor((Date.now() - new Date(c.last_message_at).getTime()) / 60000)
                                : null

                            return (
                                <div 
                                    key={c.id} 
                                    onClick={() => { setSelectedContact(c); fetchMessages(c.id); setMobileView('chat'); setSimulationMode(false); }}
                                    className={`
                                        flex items-center p-3 md:p-4 cursor-pointer transition-all border-b border-slate-50 group hover:bg-slate-50 relative overflow-hidden
                                        ${isEscalated 
                                            ? `${isSelected ? 'bg-rose-50 border-l-4 border-l-rose-500' : 'bg-rose-50/30 border-l-4 animate-border-glow hover:bg-rose-50'}`
                                            : `${isSelected ? 'bg-emerald-50/50 border-l-4 border-l-emerald-500' : 'border-l-4 border-l-transparent'}`
                                        }
                                    `}
                                >
                                    {/* Avatar */}
                                    <div className="relative flex-shrink-0">
                                        <div className={`w-11 h-11 rounded-full flex items-center justify-center font-bold text-lg text-white shadow-sm
                                            ${isAlertSystem ? 'bg-rose-500' : isEscalated ? 'bg-amber-500' : 'bg-slate-200 text-slate-500'}
                                        `}>
                                            {isAlertSystem ? '🚨' : <User size={22} />}
                                        </div>
                                        {/* Escalation indicator dot */}
                                        {isEscalated && !isAlertSystem && (
                                            <div className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-rose-500 rounded-full border-2 border-white flex items-center justify-center animate-gentle-pulse">
                                                <AlertTriangle size={8} className="text-white" />
                                            </div>
                                        )}
                                    </div>

                                    {/* Info */}
                                    <div className="ml-3 flex-1 min-w-0 pr-8">
                                        <div className="flex justify-between items-center mb-0.5">
                                            <span className={`font-bold text-[15px] truncate ${isEscalated ? 'text-rose-900' : isSelected ? 'text-emerald-900' : 'text-slate-800'}`}>
                                                {c.name || c.phone_number}
                                            </span>
                                            <span className="text-[11px] font-bold text-slate-400 flex-shrink-0 ml-2">
                                                {c.last_message_at ? new Date(c.last_message_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            {isEscalated ? (
                                                <Badge className="bg-rose-100 text-rose-700 border-none text-[10px] px-1.5 py-0 font-bold h-5 hover:bg-rose-100 flex-shrink-0">
                                                    ⚠️ Requiere atención
                                                </Badge>
                                            ) : (
                                                <>
                                                    <span className="text-[13px] text-slate-500 truncate font-medium capitalize">{c.status}</span>
                                                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse flex-shrink-0"></span>
                                                </>
                                            )}
                                            {timeSinceLastMessage !== null && timeSinceLastMessage < 5 && !isEscalated && (
                                                <Badge className="bg-blue-50 text-blue-600 border-none text-[9px] px-1 py-0 font-bold h-4 hover:bg-blue-50">
                                                    Activo
                                                </Badge>
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* Bot Toggle Shortcut */}
                                    <button
                                        onClick={async (e) => {
                                            e.stopPropagation()
                                            const newState = !c.bot_active
                                            await supabase.from('contacts').update({ bot_active: newState }).eq('id', c.id);
                                            // Optimistic update
                                            const updated = contacts.map(ct => ct.id === c.id ? { ...ct, bot_active: newState } : ct)
                                            setContacts(updated)
                                        }}
                                        className={`absolute bottom-3 right-3 w-6 h-6 rounded-full flex items-center justify-center shadow-md transition-transform flex-shrink-0 hover:scale-110 active:scale-95
                                            ${c.bot_active ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-white'}
                                        `}
                                        title={c.bot_active ? 'Pausar IA' : 'Reactivar IA'}
                                    >
                                        {c.bot_active ? <Play size={10} className="fill-current ml-[1px]" /> : <Pause size={10} className="fill-current" />}
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
