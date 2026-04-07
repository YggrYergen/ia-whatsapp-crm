'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Filter, Plus, Search, Sparkles, Pause, ChevronLeft, ChevronRight } from 'lucide-react'
import { createClient } from '@/lib/supabase'

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
}

const PAGE_SIZE = 20

export default function PacientesView() {
    const [contacts, setContacts] = useState<Contact[]>([])
    const [totalCount, setTotalCount] = useState(0)
    const [page, setPage] = useState(0)
    const [loading, setLoading] = useState(true)
    const [searchQuery, setSearchQuery] = useState('')
    const [filterStatus, setFilterStatus] = useState<string | null>(null)

    const fetchContacts = async () => {
        setLoading(true)
        let query = supabase
            .from('contacts')
            .select('*', { count: 'exact' })
            .order('last_message_at', { ascending: false, nullsFirst: false })
            .range(page * PAGE_SIZE, (page + 1) * PAGE_SIZE - 1)

        if (searchQuery.trim()) {
            query = query.or(`name.ilike.%${searchQuery}%,phone_number.ilike.%${searchQuery}%`)
        }
        if (filterStatus === 'active') {
            query = query.eq('bot_active', true)
        } else if (filterStatus === 'paused') {
            query = query.eq('bot_active', false)
        }

        const { data, count, error } = await query
        if (!error && data) {
            setContacts(data)
            setTotalCount(count || 0)
        }
        setLoading(false)
    }

    useEffect(() => {
        fetchContacts()
    }, [page, searchQuery, filterStatus])

    // Realtime updates
    useEffect(() => {
        const sub = supabase
            .channel('pacientes_view_changes')
            .on('postgres_changes' as any, { event: '*', table: 'contacts' }, () => {
                fetchContacts()
            })
            .subscribe()
        return () => { supabase.removeChannel(sub) }
    }, [page, searchQuery, filterStatus])

    const totalPages = Math.ceil(totalCount / PAGE_SIZE)

    const getStatusLabel = (contact: Contact) => {
        if (!contact.last_message_at) return { label: 'Lead Nuevo', color: 'bg-amber-100 text-amber-700' }
        const daysSince = Math.floor((Date.now() - new Date(contact.last_message_at).getTime()) / (1000 * 60 * 60 * 24))
        if (daysSince <= 7) return { label: 'Cliente Activo', color: 'bg-emerald-100 text-emerald-700' }
        if (daysSince <= 30) return { label: 'Reciente', color: 'bg-blue-100 text-blue-700' }
        return { label: 'Inactivo', color: 'bg-slate-100 text-slate-500' }
    }

    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '—'
        const d = new Date(dateStr)
        return d.toLocaleDateString('es-CL', { day: '2-digit', month: 'short', year: 'numeric' })
    }

    return (
        <div className="flex-1 overflow-y-auto bg-slate-50 p-6 lg:p-10 w-full transition-all pb-[100px] md:pb-10 fixed inset-0 md:static top-[72px] bottom-0 z-40 md:z-0">
            <div className="max-w-6xl mx-auto space-y-6">
                <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
                    <div>
                        <h2 className="text-3xl font-bold text-slate-800 tracking-tight">Base de Pacientes CRM</h2>
                        <p className="text-slate-500 mt-1">
                            {loading ? 'Cargando...' : `${totalCount} contacto${totalCount !== 1 ? 's' : ''} registrado${totalCount !== 1 ? 's' : ''}`}
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <div className="relative">
                            <button
                                onClick={() => setFilterStatus(f => f === null ? 'active' : f === 'active' ? 'paused' : null)}
                                className={`border font-bold py-2 px-4 rounded-lg shadow-sm flex items-center gap-2 transition-colors
                                    ${filterStatus ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                            >
                                <Filter size={16} />
                                {filterStatus === 'active' ? 'IA Activa' : filterStatus === 'paused' ? 'IA Pausada' : 'Filtrar'}
                            </button>
                        </div>
                    </div>
                </div>

                {/* Search bar */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-100 flex gap-4">
                    <div className="relative flex-1">
                        <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => { setSearchQuery(e.target.value); setPage(0) }}
                            placeholder="Buscar por nombre o teléfono..."
                            className="w-full bg-slate-50 border-none rounded-xl pl-10 pr-4 py-3 outline-none focus:ring-2 focus:ring-emerald-500 text-sm font-medium"
                        />
                    </div>
                </div>

                {/* Data Table */}
                <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden overflow-x-auto">
                    <table className="w-full text-left border-collapse min-w-[800px]">
                        <thead>
                            <tr className="bg-slate-50 text-slate-500 text-xs uppercase font-bold tracking-wider border-b border-slate-200">
                                <th className="p-4 pl-6">Paciente / Lead</th>
                                <th className="p-4">Contacto</th>
                                <th className="p-4">Estado</th>
                                <th className="p-4">Último Mensaje</th>
                                <th className="p-4">Agente IA</th>
                            </tr>
                        </thead>
                        <tbody className="text-sm font-medium text-slate-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={5} className="p-12 text-center">
                                        <div className="flex justify-center items-center gap-3">
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
                                    <tr key={contact.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors cursor-pointer group">
                                        <td className="p-4 pl-6 flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                                                {(contact.name || '?').charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <span className="font-bold block">{contact.name || 'Sin nombre'}</span>
                                                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">{contact.role || 'cliente'}</span>
                                            </div>
                                        </td>
                                        <td className="p-4 text-slate-500 font-mono text-xs">{contact.phone_number}</td>
                                        <td className="p-4">
                                            <span className={`px-2.5 py-1 rounded-md text-[10px] uppercase font-bold tracking-wider ${status.color}`}>
                                                {status.label}
                                            </span>
                                        </td>
                                        <td className="p-4 text-slate-500 text-xs">{formatDate(contact.last_message_at)}</td>
                                        <td className="p-4">
                                            {contact.bot_active
                                                ? <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-600"><Sparkles size={12} /> Activo</span>
                                                : <span className="flex items-center gap-1.5 text-xs font-bold text-slate-400"><Pause size={12} /> Pausado</span>
                                            }
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>

                    {/* Pagination */}
                    <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                            {totalCount > 0 ? `Mostrando ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, totalCount)} de ${totalCount.toLocaleString()}` : 'Sin datos'}
                        </span>
                        {totalPages > 1 && (
                            <div className="flex gap-2">
                                <button
                                    onClick={() => setPage(p => Math.max(0, p - 1))}
                                    disabled={page === 0}
                                    className="p-2 rounded-lg border border-slate-200 bg-white disabled:opacity-30 hover:bg-slate-50 transition-colors"
                                >
                                    <ChevronLeft size={16} />
                                </button>
                                <span className="flex items-center px-3 text-xs font-bold text-slate-500">
                                    {page + 1} / {totalPages}
                                </span>
                                <button
                                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                    disabled={page >= totalPages - 1}
                                    className="p-2 rounded-lg border border-slate-200 bg-white disabled:opacity-30 hover:bg-slate-50 transition-colors"
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
