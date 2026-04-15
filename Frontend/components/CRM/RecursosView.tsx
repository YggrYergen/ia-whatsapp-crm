'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Layers, Plus, Edit3, Save, X, ToggleLeft, ToggleRight, AlertTriangle, Palette } from 'lucide-react'
import { createClient } from '@/lib/supabase'
import { useTenant } from '@/contexts/TenantContext'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

interface Resource {
    id: string
    tenant_id: string
    name: string
    label: string
    color: string
    resource_type: string
    is_active: boolean
    sort_order: number
    created_at: string
}

interface EditingState {
    name: string
    label: string
    color: string
    resource_type: string
}

const _WHERE = 'RecursosView'

const PRESET_COLORS = [
    '#10b981', '#8b5cf6', '#3b82f6', '#f59e0b', '#ef4444',
    '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
]

const TYPE_LABELS: Record<string, string> = {
    room: 'Box / Sala',
    team: 'Equipo',
    table: 'Mesa',
    vehicle: 'Vehículo',
    other: 'Otro',
}

export default function RecursosView() {
    const { currentTenant } = useTenant()
    const tenantId = currentTenant?.id

    const [resources, setResources] = useState<Resource[]>([])
    const [loading, setLoading] = useState(true)
    const [showInactive, setShowInactive] = useState(false)
    const [editingId, setEditingId] = useState<string | null>(null)
    const [editingState, setEditingState] = useState<EditingState>({ name: '', label: '', color: '#10b981', resource_type: 'room' })
    const [isAdding, setIsAdding] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const fetchResources = useCallback(async () => {
        if (!tenantId) return
        const _where = `${_WHERE}.fetchResources`
        try {
            let query = supabase.from('resources').select('*').eq('tenant_id', tenantId)
            if (!showInactive) query = query.eq('is_active', true)
            const { data, error: fetchErr } = await query.order('sort_order').order('created_at')
            if (fetchErr) {
                console.error(`[${_where}]`, fetchErr)
                Sentry.captureException(fetchErr)
                setError('Error al cargar recursos.')
                return
            }
            setResources(data || [])
            setError(null)
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err)
            setError('Error inesperado.')
        } finally {
            setLoading(false)
        }
    }, [tenantId, showInactive])

    useEffect(() => { fetchResources() }, [fetchResources])

    useEffect(() => {
        if (!tenantId) return
        const channel = supabase
            .channel('resources_changes')
            .on('postgres_changes' as any, { event: '*', schema: 'public', table: 'resources', filter: `tenant_id=eq.${tenantId}` }, () => {
                fetchResources()
            })
            .subscribe()
        return () => { supabase.removeChannel(channel) }
    }, [tenantId, fetchResources])

    const handleCreate = async () => {
        if (!tenantId || !editingState.name.trim()) return
        const _where = `${_WHERE}.handleCreate`
        setSaving(true)
        setError(null)
        try {
            const { error: insertErr } = await supabase.from('resources').insert({
                tenant_id: tenantId,
                name: editingState.name.trim(),
                label: editingState.label.trim() || editingState.name.trim(),
                color: editingState.color,
                resource_type: editingState.resource_type,
                is_active: true,
                sort_order: resources.length,
            }).select().single()
            if (insertErr) {
                if (insertErr.message?.includes('duplicate') || insertErr.message?.includes('unique')) {
                    setError(`Ya existe un recurso con el nombre "${editingState.name}".`)
                } else {
                    console.error(`[${_where}]`, insertErr)
                    Sentry.captureException(insertErr)
                    setError('Error al crear recurso.')
                }
                return
            }
            setIsAdding(false)
            setEditingState({ name: '', label: '', color: '#10b981', resource_type: 'room' })
            await fetchResources()
        } catch (err) {
            console.error(`[${_where}]`, err)
            Sentry.captureException(err)
            setError('Error inesperado.')
        } finally {
            setSaving(false)
        }
    }

    const handleUpdate = async () => {
        if (!editingId || !editingState.name.trim()) return
        const _where = `${_WHERE}.handleUpdate`
        setSaving(true)
        setError(null)
        try {
            const { error: updateErr } = await supabase.from('resources').update({
                name: editingState.name.trim(),
                label: editingState.label.trim() || editingState.name.trim(),
                color: editingState.color,
                resource_type: editingState.resource_type,
                updated_at: new Date().toISOString(),
            }).eq('id', editingId)
            if (updateErr) {
                if (updateErr.message?.includes('duplicate') || updateErr.message?.includes('unique')) {
                    setError(`Ya existe otro recurso con el nombre "${editingState.name}".`)
                } else {
                    console.error(`[${_where}]`, updateErr)
                    Sentry.captureException(updateErr)
                    setError('Error al actualizar.')
                }
                return
            }
            setEditingId(null)
            await fetchResources()
        } catch (err) {
            console.error(`[${_where}]`, err)
            Sentry.captureException(err)
            setError('Error inesperado.')
        } finally {
            setSaving(false)
        }
    }

    const handleToggleActive = async (resource: Resource) => {
        const _where = `${_WHERE}.handleToggleActive`
        setError(null)
        try {
            if (resource.is_active) {
                const activeCount = resources.filter(r => r.is_active).length
                if (activeCount <= 1) {
                    setError('No puedes desactivar tu último recurso activo. Se necesita al menos uno para agendar.')
                    return
                }
            }
            const { error: toggleErr } = await supabase.from('resources').update({
                is_active: !resource.is_active,
                updated_at: new Date().toISOString(),
            }).eq('id', resource.id)
            if (toggleErr) {
                console.error(`[${_where}]`, toggleErr)
                Sentry.captureException(toggleErr)
                setError('Error al cambiar estado.')
                return
            }
            await fetchResources()
        } catch (err) {
            console.error(`[${_where}]`, err)
            Sentry.captureException(err)
            setError('Error inesperado.')
        }
    }

    const startEditing = (resource: Resource) => {
        setEditingId(resource.id)
        setIsAdding(false)
        setEditingState({
            name: resource.name,
            label: resource.label || resource.name,
            color: resource.color || '#10b981',
            resource_type: resource.resource_type || 'room',
        })
    }

    const cancelEdit = () => {
        setEditingId(null)
        setIsAdding(false)
        setEditingState({ name: '', label: '', color: '#10b981', resource_type: 'room' })
        setError(null)
    }

    if (loading) {
        return (
            <div className="flex-1 flex items-center justify-center bg-[#0a0e1a]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-3 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-slate-500 font-bold text-sm animate-pulse">Cargando recursos...</span>
                </div>
            </div>
        )
    }

    const renderEditForm = (isNew: boolean) => (
        <div className="bg-white/[0.06] border border-blue-500/30 rounded-2xl p-5 space-y-4 animate-fade-in">
            <div className="flex items-center justify-between">
                <h4 className="text-xs font-black text-blue-400 uppercase tracking-widest">
                    {isNew ? 'Nuevo Recurso' : 'Editando Recurso'}
                </h4>
                <button onClick={cancelEdit} className="w-7 h-7 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-white transition-colors">
                    <X size={14} />
                </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Nombre interno *</label>
                    <input
                        type="text" value={editingState.name}
                        onChange={e => setEditingState(s => ({ ...s, name: e.target.value }))}
                        placeholder="Ej: box_1, equipo_norte..."
                        className="w-full mt-1 bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-blue-500/50 placeholder:text-slate-600"
                        autoFocus
                    />
                </div>
                <div>
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Nombre visible</label>
                    <input
                        type="text" value={editingState.label}
                        onChange={e => setEditingState(s => ({ ...s, label: e.target.value }))}
                        placeholder="Ej: Box 1, Equipo Norte..."
                        className="w-full mt-1 bg-white/5 border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white outline-none focus:ring-2 focus:ring-blue-500/50 placeholder:text-slate-600"
                    />
                </div>
            </div>

            <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Tipo</label>
                <div className="flex flex-wrap gap-2 mt-2">
                    {Object.entries(TYPE_LABELS).map(([key, label]) => (
                        <button key={key} onClick={() => setEditingState(s => ({ ...s, resource_type: key }))}
                            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                                editingState.resource_type === key
                                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                    : 'bg-white/5 text-slate-400 border border-white/10 hover:bg-white/10'
                            }`}>
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-1">
                    <Palette size={10} /> Color
                </label>
                <div className="flex gap-2 mt-2">
                    {PRESET_COLORS.map(c => (
                        <button key={c} onClick={() => setEditingState(s => ({ ...s, color: c }))}
                            className={`w-7 h-7 rounded-lg transition-all ${editingState.color === c ? 'ring-2 ring-white ring-offset-2 ring-offset-[#0a0e1a] scale-110' : 'hover:scale-110'}`}
                            style={{ backgroundColor: c }}
                        />
                    ))}
                </div>
            </div>

            <div className="flex justify-end gap-2 pt-1">
                <button onClick={cancelEdit} className="px-4 py-2 rounded-xl text-xs font-bold text-slate-400 bg-white/5 hover:bg-white/10 transition-colors">Cancelar</button>
                <button onClick={isNew ? handleCreate : handleUpdate} disabled={saving || !editingState.name.trim()}
                    className="px-6 py-2 rounded-xl text-xs font-black bg-blue-500 text-white hover:bg-blue-600 transition-colors disabled:opacity-40 flex items-center gap-2">
                    {saving ? <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" /> : <Save size={14} />}
                    {saving ? 'Guardando...' : isNew ? 'Crear Recurso' : 'Guardar'}
                </button>
            </div>
        </div>
    )

    return (
        <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full transition-all pb-24 md:pb-10">
            <div className="max-w-4xl mx-auto p-4 md:p-10 space-y-5">
                <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-3">
                    <div>
                        <h2 className="text-lg md:text-2xl font-black text-white tracking-tight flex items-center gap-3">
                            <div className="w-9 h-9 rounded-xl bg-blue-500/20 flex items-center justify-center">
                                <Layers size={18} className="text-blue-400" />
                            </div>
                            Recursos
                        </h2>
                        <p className="text-xs md:text-sm text-slate-500 mt-1 font-medium">
                            {resources.length} recurso{resources.length !== 1 ? 's' : ''} · Boxes, equipos, mesas o cualquier unidad de agenda
                        </p>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={() => setShowInactive(v => !v)}
                            className={`border font-bold py-2 px-3 rounded-xl text-xs flex items-center gap-1.5 transition-colors ${
                                showInactive ? 'bg-amber-500/20 border-amber-500/30 text-amber-400' : 'bg-white/5 border-white/10 text-slate-400 hover:bg-white/10'
                            }`}>
                            {showInactive ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                            {showInactive ? 'Con inactivos' : 'Solo activos'}
                        </button>
                        <button onClick={() => { setIsAdding(true); setEditingId(null); setEditingState({ name: '', label: '', color: '#10b981', resource_type: 'room' }); setError(null) }}
                            className="bg-blue-500 hover:bg-blue-600 text-white font-black py-2 px-4 rounded-xl text-xs flex items-center gap-1.5 transition-colors shadow-lg shadow-blue-500/20">
                            <Plus size={14} /> Agregar
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 flex items-start gap-2.5 animate-fade-in">
                        <AlertTriangle size={16} className="text-rose-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-rose-300 font-bold flex-1">{error}</p>
                        <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-300"><X size={14} /></button>
                    </div>
                )}

                {isAdding && renderEditForm(true)}

                {resources.length === 0 && !isAdding ? (
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-12 text-center">
                        <div className="w-16 h-16 mx-auto rounded-2xl bg-blue-500/10 flex items-center justify-center mb-4">
                            <Layers size={28} className="text-blue-400/50" />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-1">Sin recursos configurados</h3>
                        <p className="text-slate-500 text-sm max-w-md mx-auto">
                            Agrega boxes, equipos o mesas para habilitar el sistema de agenda con round-robin.
                        </p>
                        <button onClick={() => { setIsAdding(true); setError(null) }}
                            className="mt-6 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2.5 px-6 rounded-xl text-sm flex items-center gap-2 mx-auto transition-colors">
                            <Plus size={16} /> Agregar primer recurso
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {resources.map((resource) => (
                            <React.Fragment key={resource.id}>
                                {editingId === resource.id ? (
                                    <div className="md:col-span-2">{renderEditForm(false)}</div>
                                ) : (
                                    <div className={`bg-white/[0.04] border rounded-2xl p-4 backdrop-blur-xl group hover:bg-white/[0.06] transition-all ${
                                        resource.is_active ? 'border-white/[0.08]' : 'border-amber-500/20 opacity-60'
                                    }`}>
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                                                style={{ backgroundColor: `${resource.color}20` }}>
                                                <div className="w-4 h-4 rounded-full" style={{ backgroundColor: resource.color }} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2">
                                                    <h3 className="font-bold text-white text-sm truncate">{resource.label || resource.name}</h3>
                                                    {!resource.is_active && (
                                                        <span className="text-[9px] px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full font-black uppercase">Off</span>
                                                    )}
                                                </div>
                                                <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-0.5">
                                                    {TYPE_LABELS[resource.resource_type] || resource.resource_type} · {resource.name}
                                                </p>
                                            </div>
                                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button onClick={() => startEditing(resource)}
                                                    className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors"
                                                    title="Editar">
                                                    <Edit3 size={14} />
                                                </button>
                                                <button onClick={() => handleToggleActive(resource)}
                                                    className={`w-8 h-8 flex items-center justify-center rounded-lg transition-colors ${
                                                        resource.is_active ? 'bg-white/5 text-slate-400 hover:text-amber-400 hover:bg-amber-500/10' : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
                                                    }`} title={resource.is_active ? 'Desactivar' : 'Reactivar'}>
                                                    {resource.is_active ? <ToggleRight size={14} /> : <ToggleLeft size={14} />}
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                )}

                <div className="bg-blue-500/5 border border-blue-500/10 rounded-xl p-4 flex items-start gap-3">
                    <Layers size={16} className="text-blue-400 flex-shrink-0 mt-0.5" />
                    <p className="text-[11px] text-blue-300/70 font-medium leading-relaxed">
                        Los recursos activos son las unidades de agenda (boxes, equipos, mesas) donde se asignan citas automáticamente con round-robin.
                        Cada cita se agenda en el primer recurso disponible.
                    </p>
                </div>
            </div>
        </div>
    )
}
