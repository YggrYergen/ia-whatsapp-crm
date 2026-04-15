'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Package, Plus, Edit3, Trash2, Save, X, Clock, DollarSign, ChevronDown, ChevronUp, ToggleLeft, ToggleRight, AlertTriangle } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { useTenant } from '@/contexts/TenantContext'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

interface Service {
    id: string
    tenant_id: string
    name: string
    description: string | null
    price: number | null
    price_is_variable: boolean
    duration_minutes: number | null
    is_active: boolean
    sort_order: number
    created_at: string
    updated_at: string
}

interface EditingState {
    name: string
    description: string
    price: string
    price_is_variable: boolean
    duration_minutes: string
}

const _WHERE = 'ServiciosView'

export default function ServiciosView() {
    const { currentTenant } = useTenant()
    const tenantId = currentTenant?.id

    const [services, setServices] = useState<Service[]>([])
    const [loading, setLoading] = useState(true)
    const [showInactive, setShowInactive] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [editingState, setEditingState] = useState<EditingState>({ name: '', description: '', price: '', price_is_variable: false, duration_minutes: '' })
    const [isAdding, setIsAdding] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // ── Fetch services ──────────────────────────────────────────
    const fetchServices = useCallback(async () => {
        if (!tenantId) return
        const _where = `${_WHERE}.fetchServices`
        try {
            let query = supabase.from('tenant_services').select('*').eq('tenant_id', tenantId)
            if (!showInactive) {
                query = query.eq('is_active', true)
            }
            const { data, error: fetchErr } = await query.order('sort_order').order('created_at')
            if (fetchErr) {
                console.error(`[${_where}] Supabase error:`, fetchErr)
                Sentry.captureException(fetchErr)
                setError('Error al cargar servicios.')
                return
            }
            setServices(data || [])
            setError(null)
        } catch (err) {
            console.error(`[${_where}] Unexpected error:`, err)
            Sentry.captureException(err)
            setError('Error inesperado al cargar servicios.')
        } finally {
            setLoading(false)
        }
    }, [tenantId, showInactive])

    useEffect(() => { fetchServices() }, [fetchServices])

    // ── Realtime subscription for live updates ──────────────────
    useEffect(() => {
        if (!tenantId) return
        const channel = supabase
            .channel('services_changes')
            .on('postgres_changes' as any, { event: '*', schema: 'public', table: 'tenant_services', filter: `tenant_id=eq.${tenantId}` }, () => {
                fetchServices()
            })
            .subscribe()
        return () => { supabase.removeChannel(channel) }
    }, [tenantId, fetchServices])

    // ── Create service ──────────────────────────────────────────
    const handleCreate = async () => {
        if (!tenantId || !editingState.name.trim()) return
        const _where = `${_WHERE}.handleCreate`
        setSaving(true)
        setError(null)
        try {
            const payload: any = {
                tenant_id: tenantId,
                name: editingState.name.trim(),
                description: editingState.description.trim() || null,
                price: editingState.price ? parseInt(editingState.price) : null,
                price_is_variable: editingState.price_is_variable,
                duration_minutes: editingState.duration_minutes ? parseInt(editingState.duration_minutes) : null,
                is_active: true,
                sort_order: services.length,
            }

            const { data, error: insertErr } = await supabase.from('tenant_services').insert(payload).select().single()
            if (insertErr) {
                const errMsg = insertErr.message || ''
                if (errMsg.includes('duplicate') || errMsg.includes('unique')) {
                    setError(`Ya existe un servicio con el nombre "${editingState.name}".`)
                } else {
                    console.error(`[${_where}]`, insertErr)
                    Sentry.captureException(insertErr)
                    setError('Error al crear servicio.')
                }
                return
            }
            setIsAdding(false)
            setEditingState({ name: '', description: '', price: '', price_is_variable: false, duration_minutes: '' })
            await fetchServices()
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err)
            setError('Error inesperado al crear servicio.')
        } finally {
            setSaving(false)
        }
    }

    // ── Update service ──────────────────────────────────────────
    const handleUpdate = async () => {
        if (!editingId || !editingState.name.trim()) return
        const _where = `${_WHERE}.handleUpdate`
        setSaving(true)
        setError(null)
        try {
            const payload: any = {
                name: editingState.name.trim(),
                description: editingState.description.trim() || null,
                price: editingState.price ? parseInt(editingState.price) : null,
                price_is_variable: editingState.price_is_variable,
                duration_minutes: editingState.duration_minutes ? parseInt(editingState.duration_minutes) : null,
                updated_at: new Date().toISOString(),
            }

            const { error: updateErr } = await supabase.from('tenant_services').update(payload).eq('id', editingId)
            if (updateErr) {
                const errMsg = updateErr.message || ''
                if (errMsg.includes('duplicate') || errMsg.includes('unique')) {
                    setError(`Ya existe otro servicio con el nombre "${editingState.name}".`)
                } else {
                    console.error(`[${_where}]`, updateErr)
                    Sentry.captureException(updateErr)
                    setError('Error al actualizar servicio.')
                }
                return
            }
            setEditingId(null)
            await fetchServices()
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err)
            setError('Error inesperado al actualizar.')
        } finally {
            setSaving(false)
        }
    }

    // ── Toggle active/inactive ──────────────────────────────────
    const handleToggleActive = async (service: Service) => {
        const _where = `${_WHERE}.handleToggleActive`
        setError(null)
        try {
            // Prevent deactivating the last active service
            if (service.is_active) {
                const activeCount = services.filter(s => s.is_active).length
                if (activeCount <= 1) {
                    setError('No puedes desactivar tu último servicio activo. Tu asistente necesita al menos uno.')
                    return
                }
            }
            const { error: toggleErr } = await supabase.from('tenant_services').update({
                is_active: !service.is_active,
                updated_at: new Date().toISOString(),
            }).eq('id', service.id)
            if (toggleErr) {
                console.error(`[${_where}]`, toggleErr)
                Sentry.captureException(toggleErr)
                setError('Error al cambiar estado del servicio.')
                return
            }
            await fetchServices()
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err)
            setError('Error inesperado.')
        }
    }

    // ── Delete (soft) ───────────────────────────────────────────
    const handleDelete = async (service: Service) => {
        const _where = `${_WHERE}.handleDelete`
        if (!confirm(`¿Desactivar "${service.name}"? El servicio dejará de aparecer en el catálogo del asistente.`)) return
        await handleToggleActive(service)
    }

    // ── Start editing ───────────────────────────────────────────
    const startEditing = (service: Service) => {
        setEditingId(service.id)
        setIsAdding(false)
        setEditingState({
            name: service.name,
            description: service.description || '',
            price: service.price?.toString() || '',
            price_is_variable: service.price_is_variable,
            duration_minutes: service.duration_minutes?.toString() || '',
        })
    }

    const cancelEdit = () => {
        setEditingId(null)
        setIsAdding(false)
        setEditingState({ name: '', description: '', price: '', price_is_variable: false, duration_minutes: '' })
        setError(null)
    }

    // ── Format price for display ────────────────────────────────
    const formatPrice = (price: number | null, isVariable: boolean) => {
        if (price === null) return '—'
        const formatted = `$${price.toLocaleString('es-CL')}`
        return isVariable ? `Desde ${formatted}` : formatted
    }

    // ── Loading state ───────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-[#0a0e1a]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-3 border-violet-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-slate-500 font-bold text-sm animate-pulse">Cargando servicios...</span>
                </div>
            </div>
        )
    }

    // ── Inline edit form ────────────────────────────────────────
    const renderEditForm = (isNew: boolean) => (
        <div className="bg-white/[0.06] border border-violet-500/30 rounded-2xl p-5 space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
                <h4 className="text-xs font-black text-violet-400 uppercase tracking-widest">
                    {isNew ? 'Nuevo Servicio' : 'Editando Servicio'}
                </h4>
                <button onClick={cancelEdit} className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-white transition-colors">
                    <X size={14} />
                </button>
            </div>
            
            {/* Name */}
            <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Nombre *</label>
                <input
                    type="text"
                    value={editingState.name}
                    onChange={e => setEditingState(s => ({ ...s, name: e.target.value }))}
                    placeholder="Ej: Limpieza Facial, Fumigación General..."
                    className="w-full mt-1 bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50 placeholder:text-slate-600"
                    autoFocus
                />
            </div>

            {/* Description */}
            <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Descripción</label>
                <textarea
                    value={editingState.description}
                    onChange={e => setEditingState(s => ({ ...s, description: e.target.value }))}
                    placeholder="Descripción breve del servicio..."
                    rows={2}
                    className="w-full mt-1 bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50 placeholder:text-slate-600 resize-none"
                />
            </div>

            {/* Price + Duration row */}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Precio (CLP)</label>
                    <div className="relative mt-1">
                        <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="number"
                            value={editingState.price}
                            onChange={e => setEditingState(s => ({ ...s, price: e.target.value }))}
                            placeholder="35000"
                            min="0"
                            className="w-full bg-white/5 border border-white/[0.08] rounded-xl pl-9 pr-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50 placeholder:text-slate-600"
                        />
                    </div>
                    <label className="flex items-center gap-2 mt-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={editingState.price_is_variable}
                            onChange={e => setEditingState(s => ({ ...s, price_is_variable: e.target.checked }))}
                            className="w-3.5 h-3.5 rounded border-white/20 bg-white/5 text-violet-500 focus:ring-violet-500/50"
                        />
                        <span className="text-[10px] text-slate-400 font-bold uppercase">Precio variable ("Desde")</span>
                    </label>
                </div>
                <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Duración (min)</label>
                    <div className="relative mt-1">
                        <Clock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                        <input
                            type="number"
                            value={editingState.duration_minutes}
                            onChange={e => setEditingState(s => ({ ...s, duration_minutes: e.target.value }))}
                            placeholder="45"
                            min="1"
                            className="w-full bg-white/5 border border-white/[0.08] rounded-xl pl-9 pr-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-violet-500/50 placeholder:text-slate-600"
                        />
                    </div>
                    <p className="text-[9px] text-slate-600 mt-1 font-medium">Vacío = variable</p>
                </div>
            </div>

            {/* Save button */}
            <div className="flex justify-end gap-2 pt-1">
                <button onClick={cancelEdit} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 bg-white/5 hover:bg-white/10 transition-colors">
                    Cancelar
                </button>
                <button
                    onClick={isNew ? handleCreate : handleUpdate}
                    disabled={saving || !editingState.name.trim()}
                    className="px-6 py-2 rounded-xl text-xs font-black bg-violet-500 text-white hover:bg-violet-600 transition-colors disabled:opacity-40 flex items-center gap-2"
                >
                    {saving ? (
                        <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                        <Save size={14} />
                    )}
                    {saving ? 'Guardando...' : isNew ? 'Crear Servicio' : 'Guardar Cambios'}
                </button>
            </div>
        </div>
    )

    return (
        <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full transition-all pb-24 md:pb-10">
            <div className="max-w-4xl mx-auto p-4 md:p-10 space-y-5">
                {/* Header */}
                <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-3">
                    <div>
                        <h2 className="text-lg md:text-2xl font-black text-white tracking-tight flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-violet-500/20 flex items-center justify-center">
                                <Package size={18} className="text-violet-400" />
                            </div>
                            Servicios
                        </h2>
                        <p className="text-xs md:text-sm text-slate-500 mt-1 font-medium">
                            {services.length} servicio{services.length !== 1 ? 's' : ''} · Los cambios se reflejan en tu asistente en tiempo real
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setShowInactive(v => !v)}
                            className={`border font-bold py-2 px-3 rounded-xl text-xs flex items-center gap-1.5 transition-colors
                                ${showInactive ? 'bg-amber-500/20 border-amber-500/30 text-amber-400' : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'}`}
                        >
                            {showInactive ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                            {showInactive ? 'Mostrando inactivos' : 'Solo activos'}
                        </button>
                        <button
                            onClick={() => { setIsAdding(true); setEditingId(null); setEditingState({ name: '', description: '', price: '', price_is_variable: false, duration_minutes: '' }); setError(null) }}
                            className="bg-violet-500 hover:bg-violet-600 text-white font-black py-2 px-4 rounded-xl text-xs flex items-center gap-1.5 transition-colors shadow-lg shadow-violet-500/20"
                        >
                            <Plus size={14} /> Agregar
                        </button>
                    </div>
                </div>

                {/* Error banner */}
                {error && (
                    <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 flex items-start gap-2.5 animate-fade-in">
                        <AlertTriangle size={16} className="text-rose-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-rose-300 font-bold flex-1">{error}</p>
                        <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-300">
                            <X size={14} />
                        </button>
                    </div>
                )}

                {/* Add form */}
                {isAdding && renderEditForm(true)}

                {/* Services list */}
                {services.length === 0 && !isAdding ? (
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-12 text-center">
                        <div className="w-16 h-16 mx-auto rounded-2xl bg-violet-500/10 flex items-center justify-center mb-4">
                            <Package size={28} className="text-violet-400/50" />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-1">Sin servicios configurados</h3>
                        <p className="text-slate-500 text-sm max-w-md mx-auto">
                            Agrega tu primer servicio para que tu asistente virtual pueda informar precios, duraciones y agendar citas correctamente.
                        </p>
                        <button
                            onClick={() => { setIsAdding(true); setError(null) }}
                            className="mt-6 bg-violet-500 hover:bg-violet-600 text-white font-bold py-2.5 px-6 rounded-xl text-sm flex items-center gap-2 mx-auto transition-colors"
                        >
                            <Plus size={16} /> Agregar primer servicio
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {services.map((service) => (
                            <React.Fragment key={service.id}>
                                {editingId === service.id ? (
                                    renderEditForm(false)
                                ) : (
                                    <div className={`bg-white/[0.04] border rounded-2xl p-4 md:p-5 backdrop-blur-xl group hover:bg-white/[0.06] transition-all ${
                                        service.is_active ? 'border-white/[0.08]' : 'border-amber-500/20 opacity-60'
                                    }`}>
                                        <div className="flex items-start gap-4">
                                            {/* Color indicator */}
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                                                service.is_active ? 'bg-violet-500/20' : 'bg-slate-500/20'
                                            }`}>
                                                <Package size={18} className={service.is_active ? 'text-violet-400' : 'text-slate-500'} />
                                            </div>

                                            {/* Content */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-bold text-white text-sm truncate">{service.name}</h3>
                                                    {!service.is_active && (
                                                        <span className="text-[9px] px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full font-black uppercase">Inactivo</span>
                                                    )}
                                                </div>
                                                {service.description && (
                                                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">{service.description}</p>
                                                )}
                                                <div className="flex items-center gap-4 mt-2">
                                                    {service.price !== null && (
                                                        <span className="flex items-center gap-1 text-xs font-bold text-emerald-400">
                                                            <DollarSign size={12} />
                                                            {formatPrice(service.price, service.price_is_variable)}
                                                        </span>
                                                    )}
                                                    {service.duration_minutes && (
                                                        <span className="flex items-center gap-1 text-xs font-bold text-blue-400">
                                                            <Clock size={12} />
                                                            {service.duration_minutes} min
                                                        </span>
                                                    )}
                                                    {!service.duration_minutes && (
                                                        <span className="flex items-center gap-1 text-xs font-bold text-slate-500">
                                                            <Clock size={12} />
                                                            Variable
                                                        </span>
                                                    )}
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button
                                                    onClick={() => startEditing(service)}
                                                    className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-violet-400 hover:bg-violet-500/10 transition-colors"
                                                    title="Editar"
                                                >
                                                    <Edit3 size={14} />
                                                </button>
                                                <button
                                                    onClick={() => handleToggleActive(service)}
                                                    className={`w-8 h-8 flex items-center justify-center rounded-lg transition-colors ${
                                                        service.is_active
                                                            ? 'bg-white/5 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10'
                                                            : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                                                    }`}
                                                    title={service.is_active ? 'Desactivar' : 'Reactivar'}
                                                >
                                                    {service.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                )}

                {/* Info footer */}
                <div className="bg-violet-500/5 border border-violet-500/10 rounded-xl p-4 flex items-start gap-3">
                    <Package size={16} className="text-violet-400 flex-shrink-0 mt-0.5" />
                    <p className="text-[11px] text-violet-300/70 font-medium leading-relaxed">
                        Los servicios activos aparecen automáticamente en el catálogo de tu asistente virtual.
                        Cuando un cliente pregunte por precios o duración, el asistente responderá con la información que configures aquí.
                    </p>
                </div>
            </div>
        </div>
    )
}
