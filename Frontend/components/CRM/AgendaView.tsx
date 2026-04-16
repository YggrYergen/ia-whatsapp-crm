'use client'

import React, { useState, useEffect, useMemo, useCallback } from 'react'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Clock, User, RefreshCw, CalendarCheck, CalendarDays, Plus, Loader2, AlertTriangle } from 'lucide-react'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useTenant } from '@/contexts/TenantContext'
import { createClient } from '@/lib/supabase'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()
const _WHERE = 'AgendaView'

type ViewMode = 'day' | 'week' | 'month'

interface Resource {
    id: string
    name: string
    label: string
    color: string
    is_active: boolean
    sort_order: number
}

interface Appointment {
    id: string
    resource_id: string
    contact_id: string | null
    start_time: string
    end_time: string
    duration_minutes: number
    client_name: string
    client_phone: string
    status: string
    service_name: string | null
    notes: string | null
}

interface SchedulingConfig {
    business_hours: Record<string, { start: string; end: string } | null>
    default_duration_minutes: number
    slot_interval_minutes: number
    timezone: string
}

// Default business hours fallback (9-19 Mon-Fri)
const DEFAULT_BUSINESS_HOURS: Record<string, { start: string; end: string } | null> = {
    monday: { start: '09:00', end: '19:00' },
    tuesday: { start: '09:00', end: '19:00' },
    wednesday: { start: '09:00', end: '19:00' },
    thursday: { start: '09:00', end: '19:00' },
    friday: { start: '09:00', end: '19:00' },
    saturday: null,
    sunday: null,
}

const DAY_NAMES = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']

/** Get business hours for a specific date */
function getHoursForDate(date: Date, config: SchedulingConfig | null): { start: number; end: number } | null {
    const dayName = DAY_NAMES[date.getDay()]
    const hours = config?.business_hours?.[dayName] ?? DEFAULT_BUSINESS_HOURS[dayName]
    if (!hours) return null // Closed day
    const startH = parseInt(hours.start.split(':')[0])
    const endH = parseInt(hours.end.split(':')[0])
    return { start: startH, end: endH }
}

/** Generate hour slots array for a given start/end */
function generateHourSlots(startH: number, endH: number): string[] {
    const slots: string[] = []
    for (let h = startH; h < endH; h++) {
        slots.push(`${h.toString().padStart(2, '0')}:00`)
    }
    return slots
}

export default function AgendaView() {
    const { currentTenant, currentTenantId } = useTenant()

    const [currentDate, setCurrentDate] = useState(new Date())
    const [viewMode, setViewMode] = useState<ViewMode>('day')
    const [resources, setResources] = useState<Resource[]>([])
    const [appointments, setAppointments] = useState<Appointment[]>([])
    const [schedulingConfig, setSchedulingConfig] = useState<SchedulingConfig | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Booking Modal State
    const [isBookingOpen, setIsBookingOpen] = useState(false)
    const [bookingTime, setBookingTime] = useState("")
    const [bookingDate, setBookingDate] = useState("")
    const [patientName, setPatientName] = useState("")
    const [patientPhone, setPatientPhone] = useState("")
    const [isSubmitting, setIsSubmitting] = useState(false)

    // ─── Data Fetching ───────────────────────────────────────────

    const fetchSchedulingConfig = useCallback(async () => {
        if (!currentTenantId) return
        const _where = `${_WHERE}.fetchSchedulingConfig`
        try {
            const { data, error: fetchErr } = await supabase
                .from('scheduling_config')
                .select('business_hours, default_duration_minutes, slot_interval_minutes, timezone')
                .eq('tenant_id', currentTenantId)
                .single()

            if (fetchErr) {
                // PGRST116 = no rows found — that's OK, use defaults
                if (fetchErr.code === 'PGRST116') {
                    console.warn(`[${_where}] No scheduling_config found for tenant, using defaults`)
                    setSchedulingConfig(null)
                    return
                }
                console.error(`[${_where}]`, fetchErr)
                Sentry.captureException(fetchErr, { tags: { where: _where, tenant_id: currentTenantId } })
                return
            }
            setSchedulingConfig(data as SchedulingConfig)
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err, { tags: { where: _where, tenant_id: currentTenantId } })
        }
    }, [currentTenantId])

    const fetchResources = useCallback(async () => {
        if (!currentTenantId) return
        const _where = `${_WHERE}.fetchResources`
        try {
            const { data, error: fetchErr } = await supabase
                .from('resources')
                .select('id, name, label, color, is_active, sort_order')
                .eq('tenant_id', currentTenantId)
                .eq('is_active', true)
                .order('sort_order')
                .order('created_at')

            if (fetchErr) {
                console.error(`[${_where}]`, fetchErr)
                Sentry.captureException(fetchErr, { tags: { where: _where, tenant_id: currentTenantId } })
                setError('Error al cargar recursos.')
                return
            }
            setResources(data || [])
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err, { tags: { where: _where, tenant_id: currentTenantId } })
            setError('Error inesperado cargando recursos.')
        }
    }, [currentTenantId])

    const fetchAppointments = useCallback(async () => {
        if (!currentTenantId) return
        const _where = `${_WHERE}.fetchAppointments`
        try {
            // Fetch appointments for the current month to cover all views
            const yr = currentDate.getFullYear()
            const mo = currentDate.getMonth()
            const startISO = new Date(yr, mo, 1).toISOString()
            const endISO = new Date(yr, mo + 1, 0, 23, 59, 59).toISOString()

            const { data, error: fetchErr } = await supabase
                .from('appointments')
                .select('id, resource_id, contact_id, start_time, end_time, duration_minutes, client_name, client_phone, status, service_name, notes')
                .eq('tenant_id', currentTenantId)
                .neq('status', 'cancelled')
                .gte('start_time', startISO)
                .lte('start_time', endISO)
                .order('start_time')

            if (fetchErr) {
                console.error(`[${_where}]`, fetchErr)
                Sentry.captureException(fetchErr, { tags: { where: _where, tenant_id: currentTenantId } })
                setError('Error al cargar citas.')
                return
            }
            setAppointments(data || [])
        } catch (err) {
            console.error(`[${_where}] Unexpected:`, err)
            Sentry.captureException(err, { tags: { where: _where, tenant_id: currentTenantId } })
            setError('Error inesperado cargando citas.')
        }
    }, [currentTenantId, currentDate])

    const fetchAll = useCallback(async () => {
        setLoading(true)
        setError(null)
        await Promise.all([fetchSchedulingConfig(), fetchResources(), fetchAppointments()])
        setLoading(false)
    }, [fetchSchedulingConfig, fetchResources, fetchAppointments])

    useEffect(() => { fetchAll() }, [fetchAll])

    // Realtime subscription for appointments changes
    useEffect(() => {
        if (!currentTenantId) return
        const channel = supabase
            .channel('appointments_agenda')
            .on('postgres_changes' as any, {
                event: '*', schema: 'public', table: 'appointments',
                filter: `tenant_id=eq.${currentTenantId}`
            }, () => { fetchAppointments() })
            .subscribe()
        return () => { supabase.removeChannel(channel) }
    }, [currentTenantId, fetchAppointments])

    // ─── Business Hours Logic ────────────────────────────────────

    const todayHours = useMemo(() => getHoursForDate(currentDate, schedulingConfig), [currentDate, schedulingConfig])
    const hours = useMemo(() => {
        if (!todayHours) return generateHourSlots(9, 19) // Closed day: show default for visual
        return generateHourSlots(todayHours.start, todayHours.end)
    }, [todayHours])

    // ─── Stats ───────────────────────────────────────────────────

    const todaysAppointments = useMemo(() =>
        appointments.filter(a => new Date(a.start_time).toDateString() === new Date().toDateString()),
        [appointments]
    )

    const resourceStats = useMemo(() => {
        if (!todayHours) return resources.map(r => ({ ...r, count: 0, total: 0, pct: 0 }))
        const totalSlots = todayHours.end - todayHours.start
        return resources.map(r => {
            const count = todaysAppointments.filter(a => a.resource_id === r.id).length
            return { ...r, count, total: totalSlots, pct: totalSlots > 0 ? Math.round((count / totalSlots) * 100) : 0 }
        })
    }, [resources, todaysAppointments, todayHours])

    // ─── Navigation ──────────────────────────────────────────────

    const handlePrev = () => {
        const d = new Date(currentDate)
        if (viewMode === 'day') d.setDate(d.getDate() - 1)
        if (viewMode === 'week') d.setDate(d.getDate() - 7)
        if (viewMode === 'month') d.setMonth(d.getMonth() - 1)
        setCurrentDate(d)
    }

    const handleNext = () => {
        const d = new Date(currentDate)
        if (viewMode === 'day') d.setDate(d.getDate() + 1)
        if (viewMode === 'week') d.setDate(d.getDate() + 7)
        if (viewMode === 'month') d.setMonth(d.getMonth() + 1)
        setCurrentDate(d)
    }

    const formatHeaderDate = () => {
        if (viewMode === 'day') {
            return currentDate.toLocaleDateString('es-CL', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
        }
        if (viewMode === 'month') {
            return currentDate.toLocaleDateString('es-CL', { month: 'long', year: 'numeric' })
        }
        const start = new Date(currentDate)
        start.setDate(start.getDate() - start.getDay() + 1)
        const end = new Date(start)
        end.setDate(end.getDate() + 6)
        return `${start.getDate()} ${start.toLocaleDateString('es-CL', { month: 'short' })} - ${end.getDate()} ${end.toLocaleDateString('es-CL', { month: 'short', year: 'numeric' })}`
    }

    // ─── Booking ─────────────────────────────────────────────────

    const handleSlotClick = (dateStr: string, timeStr: string) => {
        setBookingDate(dateStr)
        setBookingTime(timeStr)
        setIsBookingOpen(true)
    }

    const handleBook = async () => {
        if (!patientName.trim() || !patientPhone.trim()) return
        if (!currentTenantId) return
        const _where = `${_WHERE}.handleBook`
        setIsSubmitting(true)
        try {
            const payload = {
                tenant_id: currentTenantId,
                date_str: bookingDate,
                time_str: bookingTime,
                duration: schedulingConfig?.default_duration_minutes || 30,
                patient_name: patientName,
                phone: patientPhone
            }
            const res = await fetch(`/api/calendar/book`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            const data = await res.json()
            if (data.status === 'success') {
                setPatientName("")
                setPatientPhone("")
                setIsBookingOpen(false)
                fetchAppointments()
            } else {
                throw new Error(data.message || 'Error desconocido al agendar')
            }
        } catch (err: any) {
            console.error(`[${_where}]`, err)
            Sentry.captureException(err, { tags: { where: _where, tenant_id: currentTenantId } })
            setError(err.message || "Error al agendar")
        } finally {
            setIsSubmitting(false)
        }
    }

    // ─── Helper: find appointment at a specific resource/hour ───

    const findAppointmentAt = (date: Date, hour: number, resourceId: string): Appointment | undefined => {
        return appointments.find(a => {
            const d = new Date(a.start_time)
            return d.toDateString() === date.toDateString() && d.getHours() === hour && a.resource_id === resourceId
        })
    }

    // ─── Closed day indicator ────────────────────────────────────

    const isClosedDay = (date: Date): boolean => {
        const dayHours = getHoursForDate(date, schedulingConfig)
        return dayHours === null
    }

    // ─── Loading state ───────────────────────────────────────────

    if (loading && resources.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center bg-[#0a0e1a]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-slate-500 font-bold text-sm animate-pulse">Cargando agenda...</span>
                </div>
            </div>
        )
    }

    // ─── No resources state ──────────────────────────────────────

    if (!loading && resources.length === 0) {
        return (
            <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full pb-24 md:pb-10">
                <div className="max-w-2xl mx-auto p-6 md:p-10">
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl p-12 text-center">
                        <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4">
                            <CalendarDays size={28} className="text-indigo-400/50" />
                        </div>
                        <h3 className="text-white font-bold text-lg mb-1">Sin recursos configurados</h3>
                        <p className="text-slate-500 text-sm max-w-md mx-auto">
                            Configura al menos un recurso (box, equipo, mesa) en la sección de Recursos para habilitar la agenda.
                        </p>
                    </div>
                </div>
            </div>
        )
    }

    // ─── RENDER ──────────────────────────────────────────────────

    return (
        <div className="flex-1 overflow-y-auto bg-[#0a0e1a] w-full transition-all pb-24 md:pb-10">
            <div className="max-w-[1400px] mx-auto p-3 md:p-8 space-y-4 md:space-y-6">

                {/* ── Header ── */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-xl md:text-3xl font-black text-white tracking-tight flex items-center gap-2 md:gap-3">
                            <div className="w-9 h-9 rounded-xl bg-indigo-500/20 flex items-center justify-center">
                                <CalendarDays size={18} className="text-indigo-400" />
                            </div>
                            Agenda
                        </h1>
                        <p className="text-xs md:text-sm text-slate-500 font-medium mt-1">
                            {resources.length} recurso{resources.length !== 1 ? 's' : ''} activo{resources.length !== 1 ? 's' : ''} · Citas en tiempo real
                        </p>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                        <Button variant="outline" className="bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 shadow-sm gap-1.5 text-xs h-9" onClick={fetchAll}>
                            <RefreshCw size={14} className={loading ? "animate-spin" : ""} /> Sincronizar
                        </Button>
                        <Button onClick={() => handleSlotClick(new Date().toISOString().split('T')[0], hours[0] || "09:00")}
                            className="bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg shadow-indigo-500/20 gap-1.5 text-xs h-9 font-black">
                            <CalendarCheck size={14} /> Nueva Cita
                        </Button>
                    </div>
                </div>

                {/* ── Error Banner ── */}
                {error && (
                    <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 flex items-start gap-2.5 animate-fade-in">
                        <AlertTriangle size={16} className="text-rose-400 flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-rose-300 font-bold flex-1">{error}</p>
                        <button onClick={() => setError(null)} className="text-rose-500 hover:text-rose-300"><span className="text-sm">✕</span></button>
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 md:gap-6">
                    {/* ── Sidebar Stats ── */}
                    <div className="lg:col-span-1 space-y-3">
                        {/* Today count */}
                        <div className="bg-indigo-500/10 border border-indigo-500/20 text-white rounded-2xl p-4 relative overflow-hidden">
                            <div className="absolute top-2 right-2 opacity-10"><CalendarIcon size={48} /></div>
                            <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Hoy</div>
                            <div className="text-3xl font-black leading-none mt-1">{todaysAppointments.length}</div>
                            <p className="text-[10px] text-slate-500 mt-1">
                                {todayHours ? `${todayHours.start}:00 - ${todayHours.end}:00` : 'Día cerrado'}
                            </p>
                        </div>

                        {/* Resource occupancy — REAL progress bars */}
                        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4">
                            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Ocupación Hoy</h4>
                            <div className="space-y-2.5">
                                {resourceStats.map(rs => (
                                    <div key={rs.id} className="space-y-1">
                                        <div className="flex justify-between text-[11px] font-bold">
                                            <span className="text-slate-400 truncate mr-2">{rs.label || rs.name}</span>
                                            <span style={{ color: rs.color }}>{rs.count}/{rs.total} · {rs.pct}%</span>
                                        </div>
                                        <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                                            <div className="h-full rounded-full transition-all duration-500"
                                                style={{ width: `${rs.pct}%`, backgroundColor: rs.color }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Upcoming */}
                        <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4">
                            <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-3">Próximas</h4>
                            <div className="space-y-2">
                                {todaysAppointments.slice(0, 4).map(app => {
                                    const resource = resources.find(r => r.id === app.resource_id)
                                    return (
                                        <div key={app.id} className="flex items-center gap-2.5 p-1.5 rounded-xl hover:bg-white/[0.04] transition-colors cursor-pointer">
                                            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                                                style={{ backgroundColor: `${resource?.color || '#6366f1'}20` }}>
                                                <User size={14} style={{ color: resource?.color || '#6366f1' }} />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-[12px] font-bold text-white truncate">{app.client_name}</p>
                                                <div className="flex items-center gap-1 text-[9px] text-slate-500 font-bold">
                                                    <Clock size={8} /> {new Date(app.start_time).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })} · {resource?.label || resource?.name || '?'}
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })}
                                {todaysAppointments.length === 0 && <p className="text-[11px] text-slate-600">Sin citas hoy.</p>}
                            </div>
                        </div>
                    </div>

                    {/* ── Main Calendar Area ── */}
                    <div className="lg:col-span-3 bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden flex flex-col">
                        {/* Calendar Header */}
                        <div className="flex flex-row items-center justify-between border-b border-white/[0.06] p-3 md:p-4 shrink-0 gap-2">
                            <div className="flex items-center gap-2 md:gap-4">
                                <div className="flex bg-white/[0.06] p-0.5 rounded-lg">
                                    <Button onClick={handlePrev} variant="ghost" size="icon" className="h-7 w-7 rounded-md text-slate-400 hover:bg-white/10 hover:text-white"><ChevronLeft size={16} /></Button>
                                    <Button onClick={handleNext} variant="ghost" size="icon" className="h-7 w-7 rounded-md text-slate-400 hover:bg-white/10 hover:text-white"><ChevronRight size={16} /></Button>
                                </div>
                                <h2 className="text-sm md:text-xl font-black text-white tracking-tight capitalize">{formatHeaderDate()}</h2>
                                {todayHours === null && viewMode === 'day' && (
                                    <Badge variant="outline" className="text-amber-400 border-amber-500/30 bg-amber-500/10 text-[9px] font-black">CERRADO</Badge>
                                )}
                            </div>
                            <div className="flex gap-0.5 bg-white/[0.06] p-0.5 rounded-lg shrink-0">
                                <Button onClick={() => setViewMode('day')} variant="ghost" className={`h-7 px-2.5 md:px-4 py-0 text-[10px] md:text-xs font-bold rounded-md ${viewMode === 'day' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}>Día</Button>
                                <Button onClick={() => setViewMode('week')} variant="ghost" className={`h-7 px-2.5 md:px-4 py-0 text-[10px] md:text-xs font-bold rounded-md ${viewMode === 'week' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}>Sem</Button>
                                <Button onClick={() => setViewMode('month')} variant="ghost" className={`h-7 px-2.5 md:px-4 py-0 text-[10px] md:text-xs font-bold rounded-md ${viewMode === 'month' ? 'bg-indigo-500/20 text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}>Mes</Button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                            {loading && (
                                <div className="absolute inset-0 bg-[#0a0e1a]/50 backdrop-blur-sm z-50 flex items-center justify-center">
                                    <Loader2 className="animate-spin text-indigo-400" size={32} />
                                </div>
                            )}

                            {/* ══════ DAY VIEW ══════ */}
                            {viewMode === 'day' && (
                                <div className="flex flex-col w-full">
                                    {/* Resource column headers */}
                                    <div className="flex border-b border-white/[0.06] sticky top-0 bg-[#0a0e1a] z-10">
                                        <div className="w-12 md:w-16 border-r border-white/[0.06]"></div>
                                        <div className={`flex-1 grid text-center text-[10px] font-black uppercase text-slate-500 py-2`}
                                            style={{ gridTemplateColumns: `repeat(${resources.length}, 1fr)` }}>
                                            {resources.map((r, i) => (
                                                <div key={r.id} className={`flex items-center justify-center gap-1.5 ${i < resources.length - 1 ? 'border-r border-white/[0.06]' : ''}`}>
                                                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: r.color }} />
                                                    <span className="truncate">{r.label || r.name}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                    {/* Time slots */}
                                    {hours.map((hour, idx) => {
                                        const hourNum = parseInt(hour.split(':')[0])
                                        return (
                                            <div key={idx} className="flex border-b border-white/[0.04] min-h-[48px] md:min-h-[64px] group">
                                                <div className="w-12 md:w-16 flex-shrink-0 flex items-center justify-center border-r border-white/[0.04] text-[10px] font-black text-slate-600">
                                                    {hour}
                                                </div>
                                                <div className="flex-1 grid" style={{ gridTemplateColumns: `repeat(${resources.length}, 1fr)` }}>
                                                    {resources.map((r, rIdx) => {
                                                        const app = findAppointmentAt(currentDate, hourNum, r.id)
                                                        return (
                                                            <div key={r.id} className={`p-0.5 md:p-1 relative h-full ${rIdx < resources.length - 1 ? 'border-r border-white/[0.04]' : ''}`}>
                                                                {app ? (
                                                                    <div className="h-full rounded-lg md:rounded-xl p-2 md:p-3 border-l-3 md:border-l-4 shadow-sm"
                                                                        style={{ backgroundColor: `${r.color}15`, borderLeftColor: r.color }}>
                                                                        <p className="text-[9px] md:text-[10px] font-black uppercase tracking-tighter line-clamp-2"
                                                                            style={{ color: r.color }}>
                                                                            {app.client_name}
                                                                        </p>
                                                                        {app.service_name && (
                                                                            <p className="text-[8px] text-slate-500 mt-0.5 truncate">{app.service_name}</p>
                                                                        )}
                                                                    </div>
                                                                ) : (
                                                                    <div onClick={() => handleSlotClick(currentDate.toISOString().split('T')[0], hour)}
                                                                        className="h-full w-full opacity-0 group-hover:opacity-100 flex items-center justify-center border border-dashed rounded-xl transition-all cursor-pointer hover:bg-white/[0.03]"
                                                                        style={{ borderColor: `${r.color}40` }}>
                                                                        <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: `${r.color}80` }}>+ Agendar</span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}

                            {/* ══════ WEEK VIEW ══════ */}
                            {viewMode === 'week' && (
                                <div className="flex flex-col overflow-x-auto">
                                    <div className="flex border-b border-white/[0.06] sticky top-0 bg-[#0a0e1a] z-10">
                                        <div className="w-12 md:w-16 border-r border-white/[0.06]"></div>
                                        <div className="flex-1 grid grid-cols-7 text-center">
                                            {[...Array(7)].map((_, i) => {
                                                const d = new Date(currentDate)
                                                d.setDate(d.getDate() - d.getDay() + 1 + i)
                                                const closed = isClosedDay(d)
                                                return (
                                                    <div key={i} className={`py-2 border-r border-white/[0.06] ${closed ? 'opacity-40' : ''}`}>
                                                        <div className="text-[10px] font-bold text-slate-500 uppercase">{d.toLocaleDateString('es-CL', { weekday: 'short' })}</div>
                                                        <div className={`text-lg font-black ${d.toDateString() === new Date().toDateString() ? 'text-indigo-400' : 'text-white'}`}>{d.getDate()}</div>
                                                        {closed && <div className="text-[7px] text-amber-500 font-bold">CERRADO</div>}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    </div>
                                    {hours.map((hour, idx) => (
                                        <div key={idx} className="flex border-b border-white/[0.04] min-h-[50px] group text-[10px]">
                                            <div className="w-10 md:w-16 flex-shrink-0 flex items-center justify-center border-r border-white/[0.04] font-black text-slate-600 text-[9px] md:text-[10px]">
                                                {hour}
                                            </div>
                                            <div className="flex-1 grid grid-cols-7">
                                                {[...Array(7)].map((_, i) => {
                                                    const d = new Date(currentDate)
                                                    d.setDate(d.getDate() - d.getDay() + 1 + i)
                                                    const hourNum = parseInt(hour.split(':')[0])

                                                    const slotApps = appointments.filter(a => {
                                                        const ad = new Date(a.start_time)
                                                        return ad.toDateString() === d.toDateString() && ad.getHours() === hourNum
                                                    })

                                                    return (
                                                        <div key={i} className="border-r border-white/[0.04] p-0.5 relative cursor-pointer hover:bg-white/[0.02]"
                                                            onClick={() => slotApps.length < resources.length && handleSlotClick(d.toISOString().split('T')[0], hour)}>
                                                            {slotApps.map((se) => {
                                                                const resource = resources.find(r => r.id === se.resource_id)
                                                                return (
                                                                    <div key={se.id} className="rounded p-1 text-[8px] font-bold truncate mb-0.5 text-white"
                                                                        style={{ backgroundColor: resource?.color || '#6366f1' }}>
                                                                        {se.client_name}
                                                                    </div>
                                                                )
                                                            })}
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* ══════ MONTH VIEW ══════ */}
                            {viewMode === 'month' && (
                                <div className="h-full flex flex-col">
                                    <div className="grid grid-cols-7 text-center border-b border-white/[0.06] shrink-0">
                                        {['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'].map(d => (
                                            <div key={d} className="py-2 text-[10px] font-black tracking-widest uppercase text-slate-500">{d}</div>
                                        ))}
                                    </div>
                                    <div className="flex-1 grid grid-cols-7 grid-rows-5 h-full">
                                        {[...Array(35)].map((_, i) => {
                                            const d = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
                                            d.setDate(d.getDate() - (d.getDay() || 7) + 1 + i)
                                            const isCurrentMonth = d.getMonth() === currentDate.getMonth()
                                            const closed = isClosedDay(d)

                                            const dayApps = appointments.filter(a => new Date(a.start_time).toDateString() === d.toDateString())

                                            return (
                                                <div key={i} className={`border-r border-b border-white/[0.04] p-1 flex flex-col relative transition-colors cursor-pointer
                                                    ${!isCurrentMonth ? 'opacity-30' : 'hover:bg-white/[0.03]'}
                                                    ${closed && isCurrentMonth ? 'bg-white/[0.01]' : ''}`}
                                                    onClick={() => { setCurrentDate(d); setViewMode('day') }}>
                                                    <div className="text-right">
                                                        <span className={`text-xs font-bold ${d.toDateString() === new Date().toDateString() ? 'bg-indigo-500 text-white rounded-full w-5 h-5 inline-flex items-center justify-center' : 'text-slate-500'}`}>
                                                            {d.getDate()}
                                                        </span>
                                                    </div>
                                                    <div className="flex-1 overflow-y-auto mt-1 space-y-0.5 custom-scrollbar">
                                                        {dayApps.map((se) => {
                                                            const resource = resources.find(r => r.id === se.resource_id)
                                                            return (
                                                                <div key={se.id} className="rounded-[3px] p-0.5 px-1 truncate text-[8px] font-bold text-white"
                                                                    style={{ backgroundColor: resource?.color || '#6366f1' }}>
                                                                    {se.client_name}
                                                                </div>
                                                            )
                                                        })}
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* ── Booking Modal ── */}
                <Dialog open={isBookingOpen} onOpenChange={setIsBookingOpen}>
                    <DialogContent className="bg-[#141825] border-white/10 text-white">
                        <DialogHeader>
                            <DialogTitle className="text-white">Agendar Nueva Cita</DialogTitle>
                            <DialogDescription className="text-slate-400">
                                Para el {bookingDate} a las {bookingTime}. El sistema asignará el recurso disponible automáticamente.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                            <div className="grid gap-2">
                                <label className="text-xs font-bold text-slate-500 uppercase">Nombre</label>
                                <Input placeholder="Ej. Ana Soto" value={patientName} onChange={e => setPatientName(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white placeholder:text-slate-600" />
                            </div>
                            <div className="grid gap-2">
                                <label className="text-xs font-bold text-slate-500 uppercase">Teléfono / WhatsApp</label>
                                <Input placeholder="+569..." value={patientPhone} onChange={e => setPatientPhone(e.target.value)}
                                    className="bg-white/5 border-white/10 text-white placeholder:text-slate-600" />
                            </div>
                        </div>
                        <DialogFooter>
                            <Button variant="outline" onClick={() => setIsBookingOpen(false)} className="border-white/10 text-slate-300 hover:bg-white/10">Cancelar</Button>
                            <Button onClick={handleBook} disabled={isSubmitting} className="bg-indigo-500 hover:bg-indigo-600 text-white font-bold">
                                {isSubmitting ? <Loader2 className="animate-spin" /> : "Confirmar Reserva"}
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </div>
        </div>
    )
}
