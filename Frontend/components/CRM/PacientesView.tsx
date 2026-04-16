'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Filter, Plus, Search, Sparkles, Pause, ChevronLeft, ChevronRight, User, Phone, Calendar, MessageCircle, AlertTriangle, Star, Clock, ArrowLeft, Edit3, Save, X, Activity, TrendingUp } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { useTenant } from '@/contexts/TenantContext'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

const supabase = createClient()

interface Contact {
    id: string;
    name: string;
    phone_number: string;
    role: string;
    bot_active: boolean;
    last_message_at: string | null;
    created_at: string;
    tenant_id: string;
    notes?: string;
}

const PAGE_SIZE = 20

export default function PacientesView() {
    const { currentTenantId } = useTenant()
    const [contacts, setContacts] = useState<Contact[]>([])
    const [totalCount, setTotalCount] = useState(0)
    const [page, setPage] = useState(0)
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [filterStatus, setFilterStatus] = useState<string | null>(null)
    const [selectedPatient, setSelectedPatient] = useState<Contact | null>(null)
    const [editingNotes, setEditingNotes] = useState(false)
    const [notesValue, setNotesValue] = useState('')

    const fetchContacts = async () => {
        if (!currentTenantId) return
        setLoading(true)
        let query = supabase.from('contacts').select('*', { count: 'exact' }).eq('tenant_id', currentTenantId)

        if (searchQuery) {
            query = query.or(`name.ilike.%${searchQuery}%,phone_number.ilike.%${searchQuery}%`)
        }
        if (filterStatus === 'active') {
            query = query.eq('bot_active', true)
        } else if (filterStatus === 'paused') {
            query = query.eq('bot_active', false)
        }

        const { data, count, error } = await query
            .order('last_message_at', { ascending: false, nullsFirst: false })
            .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)

        if (!error && data) {
            setContacts(data)
            setTotalCount(count || 0)
        }
        setLoading(false)
    }

    useEffect(() => { fetchContacts() }, [page, searchQuery, filterStatus, currentTenantId])

    useEffect(() => {
        if (!currentTenantId) return
        const sub = supabase
            .channel(`clientes_view_${currentTenantId.slice(0, 8)}`)
            .on('postgres_changes' as any, {
                event: '*', schema: 'public', table: 'contacts',
                filter: `tenant_id=eq.${currentTenantId}`
            }, () => {
                fetchContacts()
            })
            .subscribe()
        return () => { supabase.removeChannel(sub) }
    }, [page, searchQuery, filterStatus, currentTenantId])

    const totalPages = Math.ceil(totalCount / PAGE_SIZE)

    const getStatusLabel = (contact: Contact) => {
        if (!contact.last_message_at) return { label: 'Nuevo', color: 'bg-amber-500/20 text-amber-400' }
        const daysSince = Math.floor((Date.now() - new Date(contact.last_message_at).getTime()) / (1000 * 60 * 60 * 24))
        if (daysSince <= 7) return { label: 'Activo', color: 'bg-emerald-500/20 text-emerald-400' }
        if (daysSince <= 30) return { label: 'Reciente', color: 'bg-blue-500/20 text-blue-400' }
        return { label: 'Inactivo', color: 'bg-slate-500/20 text-slate-400' }
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '—'
        return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: es })
    }

    const getLeadScore = (contact: Contact) => {
        let score = 30
        if (contact.name && contact.name !== 'Sin nombre') score += 15
        if (contact.last_message_at) {
            const daysSince = Math.floor((Date.now() - new Date(contact.last_message_at).getTime()) / (1000 * 60 * 60 * 24))
            if (daysSince <= 1) score += 40
            else if (daysSince <= 7) score += 25
            else if (daysSince <= 30) score += 10
        }
        if (contact.bot_active) score += 10
        return Math.min(100, score)
    }

    const handleSaveNotes = async () => {
        if (!selectedPatient) return
        const { error } = await supabase.from('contacts').update({ notes: notesValue }).eq('id', selectedPatient.id)
        if (!error) {
            setSelectedPatient({ ...selectedPatient, notes: notesValue })
            setEditingNotes(false)
        }
    }

    // ========== PATIENT DETAIL VIEW ==========
    if (selectedPatient) {
        const status = getStatusLabel(selectedPatient)
        const score = getLeadScore(selectedPatient)
        const scoreColor = score >= 70 ? 'text-emerald-400' : score >= 40 ? 'text-amber-400' : 'text-rose-400'
        const scoreBg = score >= 70 ? 'bg-emerald-500/20' : score >= 40 ? 'bg-amber-500/20' : 'bg-rose-500/20'

        return (
            <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full pb-24 md:pb-10">
                <div className="max-w-3xl mx-auto p-4 md:p-10 space-y-5">
                    {/* Back button */}
                    <button 
                        onClick={() => setSelectedPatient(null)} 
                        className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-bold"
                    >
                        <ArrowLeft size={16} /> Volver a lista
                    </button>

                    {/* Patient header card */}
                    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-5 md:p-8 backdrop-blur-xl relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl" />
                        
                        <div className="flex items-start gap-4 md:gap-6">
                            <div className="w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white font-black text-xl flex-shrink-0 shadow-lg shadow-emerald-500/20">
                                {(selectedPatient.name || '?').charAt(0).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <h2 className="text-xl md:text-2xl font-black text-white tracking-tight truncate">{selectedPatient.name || 'Sin nombre'}</h2>
                                <div className="flex flex-wrap items-center gap-2 mt-1.5">
                                    <span className={`px-2.5 py-0.5 rounded-full text-[9px] uppercase font-black tracking-widest ${status.color}`}>{status.label}</span>
                                    <span className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">{selectedPatient.role || 'cliente'}</span>
                                </div>
                            </div>
                        </div>

                        {/* Quick action buttons */}
                        <div className="flex gap-2 mt-5">
                            <a href={`tel:${selectedPatient.phone_number}`} className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-bold hover:bg-emerald-500/30 transition-colors">
                                <Phone size={14} /> LLAMAR
                            </a>
                            <button className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-blue-500/20 border border-blue-500/30 rounded-xl text-blue-400 text-xs font-bold hover:bg-blue-500/30 transition-colors">
                                <MessageCircle size={14} /> CHAT
                            </button>
                            <button className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-indigo-500/20 border border-indigo-500/30 rounded-xl text-indigo-400 text-xs font-bold hover:bg-indigo-500/30 transition-colors">
                                <Calendar size={14} /> AGENDAR
                            </button>
                        </div>
                    </div>

                    {/* Stats grid */}
                    <div className="grid grid-cols-3 gap-3">
                        <div className={`${scoreBg} rounded-2xl p-4 border border-white/[0.06] text-center`}>
                            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Score</div>
                            <div className={`text-2xl font-black ${scoreColor}`}>{score}</div>
                            <div className="text-[9px] text-slate-500 font-bold mt-0.5">/ 100</div>
                        </div>
                        <div className="bg-white/[0.04] rounded-2xl p-4 border border-white/[0.06] text-center">
                            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Última vez</div>
                            <div className="text-sm font-bold text-white leading-tight mt-1.5">{formatDate(selectedPatient.last_message_at)}</div>
                        </div>
                        <div className="bg-white/[0.04] rounded-2xl p-4 border border-white/[0.06] text-center">
                            <div className="text-[9px] font-black text-slate-500 uppercase tracking-widest mb-1">Registrado</div>
                            <div className="text-sm font-bold text-white leading-tight mt-1.5">{formatDate(selectedPatient.created_at)}</div>
                        </div>
                    </div>

                    {/* Contact Info */}
                    <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-5 backdrop-blur-xl space-y-4">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Información de contacto</h3>
                        <div className="space-y-3">
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center">
                                    <Phone size={14} className="text-slate-400" />
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 font-bold uppercase">Teléfono</div>
                                    <div className="text-sm text-white font-mono font-bold">{selectedPatient.phone_number}</div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center">
                                    <Sparkles size={14} className="text-slate-400" />
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 font-bold uppercase">Agente IA</div>
                                    <div className={`text-sm font-bold ${selectedPatient.bot_active ? 'text-emerald-400' : 'text-amber-400'}`}>
                                        {selectedPatient.bot_active ? 'Activo' : 'Pausado'}
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-lg bg-white/[0.06] flex items-center justify-center">
                                    <User size={14} className="text-slate-400" />
                                </div>
                                <div>
                                    <div className="text-[10px] text-slate-500 font-bold uppercase">Rol</div>
                                    <div className="text-sm text-white font-bold capitalize">{selectedPatient.role || 'cliente'}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Notes section */}
                    <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-5 backdrop-blur-xl space-y-3">
                        <div className="flex items-center justify-between">
                            <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Notas del equipo</h3>
                            {editingNotes ? (
                                <div className="flex gap-1.5">
                                    <button onClick={() => setEditingNotes(false)} className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-white transition-colors">
                                        <X size={14} />
                                    </button>
                                    <button onClick={handleSaveNotes} className="w-7 h-7 flex items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors">
                                        <Save size={14} />
                                    </button>
                                </div>
                            ) : (
                                <button onClick={() => { setEditingNotes(true); setNotesValue(selectedPatient.notes || '') }} className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-white transition-colors">
                                    <Edit3 size={14} />
                                </button>
                            )}
                        </div>
                        {editingNotes ? (
                            <textarea 
                                value={notesValue}
                                onChange={(e) => setNotesValue(e.target.value)}
                                className="w-full bg-white/5 border border-white/[0.08] rounded-xl p-3 text-sm text-white outline-none focus:ring-2 focus:ring-emerald-500/50 min-h-[100px] resize-none placeholder:text-slate-600"
                                placeholder="Agregar notas sobre este cliente..."
                                autoFocus
                            />
                        ) : (
                            <p className="text-sm text-slate-400 leading-relaxed">{selectedPatient.notes || 'Sin notas. Toca el ícono de edición para agregar.'}</p>
                        )}
                    </div>

                    {/* Mock sections — visually complete, data connections pending */}
                    <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-5 backdrop-blur-xl space-y-3">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Historial de citas</h3>
                        <div className="space-y-2">
                            <div className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.03]">
                                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center"><Calendar size={14} className="text-emerald-400" /></div>
                                <div className="flex-1">
                                    <div className="text-xs font-bold text-white">Evaluación diagnóstica</div>
                                    <div className="text-[10px] text-slate-500">Pendiente conexión con calendario</div>
                                </div>
                                <span className="text-[9px] font-bold text-slate-500 bg-white/5 px-2 py-0.5 rounded-full">MOCK</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-5 backdrop-blur-xl space-y-3">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Historial de incidentes</h3>
                        <div className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.03]">
                            <div className="w-8 h-8 rounded-lg bg-rose-500/20 flex items-center justify-center"><AlertTriangle size={14} className="text-rose-400" /></div>
                            <div className="flex-1">
                                <div className="text-xs font-bold text-white">Sin incidentes registrados</div>
                                <div className="text-[10px] text-slate-500">Se alimenta de alertas del sistema</div>
                            </div>
                            <span className="text-[9px] font-bold text-slate-500 bg-white/5 px-2 py-0.5 rounded-full">MOCK</span>
                        </div>
                    </div>

                    <div className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-5 backdrop-blur-xl space-y-3">
                        <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Preferencias y comportamiento</h3>
                        <div className="grid grid-cols-2 gap-2">
                            <div className="p-3 rounded-xl bg-white/[0.03]">
                                <div className="text-[9px] text-slate-500 font-bold uppercase">Canal preferido</div>
                                <div className="text-sm text-white font-bold mt-1">WhatsApp</div>
                            </div>
                            <div className="p-3 rounded-xl bg-white/[0.03]">
                                <div className="text-[9px] text-slate-500 font-bold uppercase">Horario activo</div>
                                <div className="text-sm text-white font-bold mt-1">9:00 - 18:00</div>
                            </div>
                            <div className="p-3 rounded-xl bg-white/[0.03]">
                                <div className="text-[9px] text-slate-500 font-bold uppercase">Sentimiento</div>
                                <div className="text-sm text-emerald-400 font-bold mt-1">Positivo</div>
                            </div>
                            <div className="p-3 rounded-xl bg-white/[0.03]">
                                <div className="text-[9px] text-slate-500 font-bold uppercase">Interacciones</div>
                                <div className="text-sm text-white font-bold mt-1">—</div>
                            </div>
                        </div>
                        <p className="text-[10px] text-slate-600 italic text-center mt-1">Datos de comportamiento se conectarán en Sprint 2</p>
                    </div>
                </div>
            </div>
        )
    }

    // ========== CONTACT LIST VIEW ==========
    return (
        <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full transition-all pb-24 md:pb-10">
            <div className="max-w-6xl mx-auto p-4 md:p-10 space-y-5">
                <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-3">
                    <div>
                        <h2 className="text-lg md:text-2xl font-black text-white tracking-tight">Base de Clientes</h2>
                        <p className="text-xs md:text-sm text-slate-500 mt-0.5 font-medium">
                            {loading ? 'Cargando...' : `${totalCount} contacto${totalCount !== 1 ? 's' : ''}`}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setFilterStatus(f => f === null ? 'active' : f === 'active' ? 'paused' : null)}
                            className={`border font-bold py-2 px-3 md:px-4 rounded-xl text-xs flex items-center gap-1.5 transition-colors
                                ${filterStatus ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400' : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}
                        >
                            <Filter size={14} />
                            {filterStatus === 'active' ? 'IA Activa' : filterStatus === 'paused' ? 'IA Pausada' : 'Filtrar'}
                        </button>
                    </div>
                </div>

                <div className="bg-white/[0.03] border border-white/[0.06] p-3 md:p-4 rounded-2xl backdrop-blur-xl flex gap-3">
                    <div className="relative flex-1">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => { setSearchQuery(e.target.value); setPage(0) }}
                            placeholder="Buscar por nombre o teléfono..."
                            className="w-full bg-white/5 border border-white/[0.06] rounded-xl pl-9 pr-4 py-2.5 outline-none focus:ring-2 focus:ring-emerald-500/50 text-sm font-medium text-white placeholder:text-slate-600 transition-all"
                        />
                    </div>
                </div>

                <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden backdrop-blur-xl">
                    <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[580px]">
                        <thead>
                            <tr className="bg-white/[0.03] text-slate-500 text-[10px] uppercase font-bold tracking-wider border-b border-white/[0.06]">
                                <th className="p-4 pl-6">Cliente / Lead</th>
                                <th className="p-4">Contacto</th>
                                <th className="p-4">Estado</th>
                                <th className="p-4">Último msg</th>
                                <th className="p-4">IA</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm font-medium text-slate-300">
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="p-12 text-center">
                                        <div className="flex items-center justify-center gap-3">
                                            <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                                            <span className="text-slate-400 font-bold">Cargando contactos...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : contacts.length === 0 ? (
                                <tr>
                                    <td colSpan={5} className="p-12 text-center text-slate-400 font-bold">
                                        {searchQuery ? 'Sin resultados para esta búsqueda' : 'No hay contactos registrados'}
                                    </td>
                                </tr>
                            ) : contacts.map((contact) => {
                                const status = getStatusLabel(contact)
                                return (
                                    <tr 
                                        key={contact.id} 
                                        className="border-b border-white/[0.04] hover:bg-white/[0.03] transition-colors cursor-pointer group"
                                        onClick={() => setSelectedPatient(contact)}
                                    >
                                        <td className="p-3 md:p-4 pl-4 md:pl-6 flex items-center gap-3">
                                            <div className="w-7 h-7 md:w-8 md:h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs flex-shrink-0">
                                                {(contact.name || '?').charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <span className="font-bold block">{contact.name || 'Sin nombre'}</span>
                                                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">{contact.role || 'cliente'}</span>
                                            </div>
                                        </td>
                                        <td className="p-3 md:p-4 text-slate-500 font-mono text-[11px]">{contact.phone_number}</td>
                                        <td className="p-3 md:p-4">
                                            <span className={`px-2 py-0.5 rounded-full text-[9px] uppercase font-bold tracking-wider whitespace-nowrap ${status.color}`}>
                                                {status.label}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-500 text-xs">{formatDate(contact.last_message_at)}</td>
                                        <td className="p-4">
                                            {contact.bot_active
                                                ? <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400"><Sparkles size={12} /> On</span>
                                                : <span className="flex items-center gap-1.5 text-xs font-bold text-slate-500"><Pause size={12} /> Off</span>
                                            }
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                    </div>

                    <div className="p-3 md:p-4 bg-white/[0.02] border-t border-white/[0.06] flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                            {totalCount > 0 ? `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, totalCount)} de ${totalCount.toLocaleString()}` : 'Sin datos'}
                        </span>
                        {totalPages > 1 && (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(0, p - 1))}
                                    disabled={page === 0}
                                    className="p-2 rounded-lg border border-white/10 bg-white/5 disabled:opacity-30 hover:bg-white/10 transition-colors text-slate-400"
                                >
                                    <ChevronLeft size={16} />
                                </button>
                                <span className="flex items-center px-3 text-xs font-bold text-slate-500">
                                    {page + 1} / {totalPages}
                                </span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                    disabled={page >= totalPages - 1}
                                    className="p-2 rounded-lg border border-white/10 bg-white/5 disabled:opacity-30 hover:bg-white/10 transition-colors text-slate-400"
                                >
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
