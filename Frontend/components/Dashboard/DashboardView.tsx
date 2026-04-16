'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { TrendingUp, Calendar as CalendarIcon, User, Activity, Bot, Check, Heart, Clock, AlertCircle, ArrowUpRight, CheckCircle2, XCircle, AlertTriangle, MessageCircle, Bell, RefreshCw, ExternalLink, Filter, ChevronDown } from 'lucide-react'
import { Badge } from "@/components/ui/badge"
import { useCrm } from '@/contexts/CrmContext'
import { useUI } from '@/contexts/UIContext'
import { useTenant } from '@/contexts/TenantContext'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

const supabase = createClient()

type AlertStatus = 'all' | 'pending' | 'resolved'
type TimeRange = '1h' | '6h' | 'today' | 'week' | 'month' | 'year'

interface AlertItem {
    id: string;
    tenant_id: string;
    contact_id: string | null;
    type: string;
    message: string;
    is_resolved: boolean;
    is_read: boolean;
    created_at: string;
    contact_name?: string;
    contact_phone?: string;
}

export default function DashboardView() {
    const { setMobileView, contacts, setSelectedContact, setMessages } = useCrm()
    const { currentTenantId } = useTenant()
    const router = useRouter()
    
    const [alerts, setAlerts] = useState<AlertItem[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [alertFilter, setAlertFilter] = useState<AlertStatus>('pending')
    const [timeRange, setTimeRange] = useState<TimeRange>('today')
    const [showTimeDropdown, setShowTimeDropdown] = useState(false)

    const getTimeRangeStart = (range: TimeRange): Date => {
        const now = new Date()
        switch (range) {
            case '1h': return new Date(now.getTime() - 60 * 60 * 1000)
            case '6h': return new Date(now.getTime() - 6 * 60 * 60 * 1000)
            case 'today': {
                const d = new Date(now.toLocaleString('en-US', { timeZone: 'America/Santiago' }))
                d.setHours(0, 0, 0, 0)
                return d
            }
            case 'week': return new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
            case 'month': return new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
            case 'year': return new Date(now.getTime() - 365 * 24 * 60 * 60 * 1000)
        }
    }

    const timeRangeLabels: Record<TimeRange, string> = {
        '1h': 'Última hora', '6h': 'Últimas 6h', 'today': 'Hoy',
        'week': 'Semana', 'month': 'Mes', 'year': 'Año'
    }

    const fetchAlerts = async () => {
        if (!currentTenantId) return
        setIsLoading(true)
        const { data: alertsData } = await supabase
            .from('alerts')
            .select('*')
            .eq('tenant_id', currentTenantId)
            .order('created_at', { ascending: false })
            .limit(200)

        if (alertsData) {
            const enriched = alertsData.map(a => {
                const contact = contacts.find(c => c.id === a.contact_id)
                return { ...a, contact_name: contact?.name || null, contact_phone: contact?.phone_number || null }
            })
            setAlerts(enriched)
        }
        setIsLoading(false)
    }

    useEffect(() => {
        if (!currentTenantId) {
            setAlerts([])
            setIsLoading(false)
            return
        }
        fetchAlerts()
        const sub = supabase
            .channel(`dashboard-alerts-${currentTenantId.slice(0, 8)}`)
            .on('postgres_changes' as any, {
                event: '*', schema: 'public', table: 'alerts',
                filter: `tenant_id=eq.${currentTenantId}`
            }, () => fetchAlerts())
            .subscribe()
        return () => { supabase.removeChannel(sub) }
    }, [contacts, currentTenantId])

    // Time-filtered alerts
    const timeFilteredAlerts = useMemo(() => {
        const start = getTimeRangeStart(timeRange)
        return alerts.filter(a => new Date(a.created_at) >= start)
    }, [alerts, timeRange])

    const filteredAlerts = useMemo(() => {
        switch (alertFilter) {
            case 'pending': return timeFilteredAlerts.filter(a => !a.is_resolved)
            case 'resolved': return timeFilteredAlerts.filter(a => a.is_resolved)
            default: return timeFilteredAlerts
        }
    }, [timeFilteredAlerts, alertFilter])

    // Stats (time-filtered)
    const pendingCount = timeFilteredAlerts.filter(a => !a.is_resolved).length
    const resolvedCount = timeFilteredAlerts.filter(a => a.is_resolved).length
    const escalationAlerts = timeFilteredAlerts.filter(a => a.type === 'escalation' && !a.is_resolved)
    const appointmentCount = timeFilteredAlerts.filter(a => a.message.includes('CITA') || a.message.includes('AGENDADA')).length
    const activeChats = contacts.filter(c => c.bot_active && c.phone_number !== '56912345678').length

    const navigateToChat = async (alert: AlertItem) => {
        if (!alert.contact_id) return
        const contact = contacts.find(c => c.id === alert.contact_id)
        if (!contact) return
        await supabase.from('alerts').update({ is_read: true }).eq('id', alert.id)
        const { data: msgs } = await supabase.from('messages').select('*').eq('contact_id', contact.id).order('timestamp', { ascending: true })
        if (msgs) setMessages(msgs)
        setSelectedContact(contact)
        setMobileView('chat')
        router.push('/chats')
    }

    const handleResolve = async (alertId: string) => {
        await supabase.from('alerts').update({ is_resolved: true }).eq('id', alertId)
        setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_resolved: true } : a))
    }

    const handleDismiss = async (alertId: string) => {
        await supabase.from('alerts').update({ is_resolved: true, is_read: true }).eq('id', alertId)
        setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_resolved: true, is_read: true } : a))
    }

    const getAlertIcon = (alert: AlertItem) => {
        if (alert.type === 'escalation') return <AlertTriangle size={14} className="text-rose-400" />
        if (alert.message.includes('AGENDADA') || alert.message.includes('NUEVA CITA')) return <CalendarIcon size={14} className="text-emerald-400" />
        if (alert.message.includes('CANCELADA')) return <XCircle size={14} className="text-red-400" />
        if (alert.message.includes('RE-AGENDADA')) return <RefreshCw size={14} className="text-blue-400" />
        return <Bell size={14} className="text-slate-400" />
    }

    const getAlertBadge = (alert: AlertItem) => {
        if (alert.type === 'escalation') return <Badge className="bg-rose-500/20 text-rose-300 border-none text-[9px] font-bold hover:bg-rose-500/20">Escalación</Badge>
        if (alert.message.includes('NUEVA CITA') || alert.message.includes('AGENDADA')) return <Badge className="bg-emerald-500/20 text-emerald-300 border-none text-[9px] font-bold hover:bg-emerald-500/20">Cita</Badge>
        if (alert.message.includes('CANCELADA')) return <Badge className="bg-red-500/20 text-red-300 border-none text-[9px] font-bold hover:bg-red-500/20">Cancelación</Badge>
        if (alert.message.includes('RE-AGENDADA')) return <Badge className="bg-blue-500/20 text-blue-300 border-none text-[9px] font-bold hover:bg-blue-500/20">Reagendada</Badge>
        return <Badge className="bg-white/10 text-slate-400 border-none text-[9px] font-bold hover:bg-white/10">Info</Badge>
    }

    const formatTimeAgo = (dateStr: string) => {
        const mins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000)
        if (mins < 1) return 'Ahora'
        if (mins < 60) return `${mins}m`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `${hrs}h`
        const days = Math.floor(hrs / 24)
        return `${days}d`
    }

    return (
        <div className="flex-1 overflow-y-auto w-full transition-all bg-[#0a0e1a] min-h-screen">
            <div className="w-full max-w-7xl mx-auto p-4 md:p-8 space-y-5 md:space-y-6 pb-24 md:pb-10">
                
                {/* Header + Time Range */}
                <div className="flex items-center justify-between gap-3">
                    <h1 className="text-lg md:text-2xl font-black text-white tracking-tight">
                        Centro de Control
                    </h1>
                    <div className="relative">
                        <button 
                            onClick={() => setShowTimeDropdown(!showTimeDropdown)}
                            className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-[11px] font-bold text-slate-300 hover:bg-white/10 transition-colors"
                        >
                            <Clock size={12} /> {timeRangeLabels[timeRange]}
                            <ChevronDown size={12} className={`transition-transform ${showTimeDropdown ? 'rotate-180' : ''}`} />
                        </button>
                        {showTimeDropdown && (
                            <>
                                <div className="fixed inset-0 z-40" onClick={() => setShowTimeDropdown(false)} />
                                <div className="absolute right-0 top-full mt-1 bg-[#151a2e] border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 min-w-[140px]">
                                    {(Object.entries(timeRangeLabels) as [TimeRange, string][]).map(([key, label]) => (
                                        <button
                                            key={key}
                                            onClick={() => { setTimeRange(key); setShowTimeDropdown(false) }}
                                            className={`w-full text-left px-4 py-2.5 text-[11px] font-bold transition-colors
                                                ${timeRange === key ? 'bg-emerald-500/20 text-emerald-400' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* STAT CARDS — Compact glassmorphism strip */}
                <div className="grid grid-cols-4 gap-2 md:gap-3">
                    {[
                        { label: 'Chats Activos', val: activeChats, icon: <Bot size={14} />, accent: 'from-emerald-500/20 to-emerald-500/5', text: 'text-emerald-400' },
                        { label: 'Pendientes', val: pendingCount, icon: <AlertCircle size={14} />, accent: pendingCount > 0 ? 'from-amber-500/20 to-amber-500/5' : 'from-white/5 to-white/[0.02]', text: pendingCount > 0 ? 'text-amber-400' : 'text-slate-400' },
                        { label: 'Agendadas', val: appointmentCount, icon: <CalendarIcon size={14} />, accent: 'from-blue-500/20 to-blue-500/5', text: 'text-blue-400' },
                        { label: 'Resueltas', val: resolvedCount, icon: <CheckCircle2 size={14} />, accent: 'from-emerald-500/20 to-emerald-500/5', text: 'text-emerald-400' },
                    ].map((card, i) => (
                        <div key={i} className={`relative overflow-hidden rounded-2xl border border-white/[0.06] bg-gradient-to-b ${card.accent} backdrop-blur-xl p-3 md:p-4`}>
                            <div className={`${card.text} mb-1.5 md:mb-2`}>{card.icon}</div>
                            <div className="text-xl md:text-2xl font-black text-white tracking-tighter leading-none">{card.val}</div>
                            <div className="text-[9px] md:text-[10px] font-bold text-slate-500 uppercase tracking-wider mt-1 leading-tight">{card.label}</div>
                        </div>
                    ))}
                </div>

                {/* INTERVENCIÓN MANUAL (LIVE) */}
                {escalationAlerts.length > 0 && (
                    <div className="space-y-2.5">
                        <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-rose-500 rounded-full animate-gentle-pulse" />
                            <h2 className="text-xs md:text-sm font-black text-white uppercase tracking-widest">
                                Intervención Manual
                            </h2>
                            <Badge className="bg-rose-500/20 text-rose-400 border-none text-[9px] font-black hover:bg-rose-500/20 ml-auto">
                                {escalationAlerts.length}
                            </Badge>
                        </div>
                        <div className="bg-white/[0.03] border border-rose-500/20 rounded-2xl overflow-hidden backdrop-blur-xl divide-y divide-white/[0.04]">
                            {escalationAlerts.map((alert) => (
                                <div key={alert.id} className="p-3 md:p-4 flex items-center justify-between gap-3 hover:bg-white/[0.03] transition-colors">
                                    <div className="flex gap-3 items-start flex-1 min-w-0">
                                        <div className="w-1.5 h-1.5 bg-rose-500 rounded-full animate-gentle-pulse mt-2 flex-shrink-0" />
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-bold text-white truncate">{alert.contact_name || alert.contact_phone || 'Desconocido'}</p>
                                            <p className="text-xs text-rose-300/70 font-medium line-clamp-1 mt-0.5">{alert.message}</p>
                                            <span className="text-[10px] text-slate-500 font-bold">{formatTimeAgo(alert.created_at)}</span>
                                        </div>
                                    </div>
                                    <div className="flex gap-1.5 flex-shrink-0">
                                        {alert.contact_id && (
                                            <button onClick={() => navigateToChat(alert)} className="p-2 bg-white/10 text-white rounded-xl hover:bg-white/20 transition-colors" title="Ir al chat">
                                                <ArrowUpRight size={14} />
                                            </button>
                                        )}
                                        <button onClick={() => handleResolve(alert.id)} className="p-2 bg-emerald-500/20 text-emerald-400 rounded-xl hover:bg-emerald-500/30 transition-colors" title="Resolver">
                                            <CheckCircle2 size={14} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* HISTORIAL DE ALERTAS */}
                <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xs md:text-sm font-black text-white uppercase tracking-widest flex items-center gap-2">
                            <Activity size={14} className="text-blue-400" /> Historial
                        </h2>
                        <button onClick={fetchAlerts} className="p-1.5 text-slate-500 hover:text-white hover:bg-white/10 rounded-lg transition-colors">
                            <RefreshCw size={14} />
                        </button>
                    </div>

                    {/* Filter tabs */}
                    <div className="flex gap-1 bg-white/[0.03] p-1 rounded-xl border border-white/[0.06]">
                        {([
                            { key: 'pending' as AlertStatus, label: 'Pendientes', count: timeFilteredAlerts.filter(a => !a.is_resolved).length },
                            { key: 'all' as AlertStatus, label: 'Todas', count: timeFilteredAlerts.length },
                            { key: 'resolved' as AlertStatus, label: 'Resueltas', count: timeFilteredAlerts.filter(a => a.is_resolved).length },
                        ]).map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setAlertFilter(tab.key)}
                                className={`flex-1 py-1.5 px-2 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-1.5
                                    ${alertFilter === tab.key
                                        ? 'bg-white/10 text-white shadow-sm'
                                        : 'text-slate-500 hover:text-slate-300'}`}
                            >
                                {tab.label}
                                <span className={`min-w-[16px] h-[16px] rounded-full text-[9px] font-black flex items-center justify-center
                                    ${alertFilter === tab.key ? 'bg-white/20 text-white' : 'bg-white/5 text-slate-500'}`}>
                                    {tab.count}
                                </span>
                            </button>
                        ))}
                    </div>

                    {/* Alert List */}
                    <div className="bg-white/[0.03] border border-white/[0.06] rounded-2xl overflow-hidden backdrop-blur-xl">
                        {isLoading ? (
                            <div className="p-8 text-center text-slate-500">
                                <RefreshCw size={18} className="animate-spin mx-auto mb-2" />
                                <p className="text-xs font-medium">Cargando...</p>
                            </div>
                        ) : filteredAlerts.length === 0 ? (
                            <div className="p-8 text-center space-y-2">
                                <CheckCircle2 size={28} className="mx-auto text-emerald-500/30" />
                                <p className="text-xs font-bold text-slate-500">
                                    {alertFilter === 'pending' ? 'Sin alertas pendientes ✓' : 'Sin alertas en este período'}
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-white/[0.04] max-h-[50vh] overflow-y-auto custom-scrollbar">
                                {filteredAlerts.map((alert) => (
                                    <div 
                                        key={alert.id} 
                                        className={`p-3 md:p-4 flex items-start gap-3 transition-colors group
                                            ${!alert.is_resolved ? 'hover:bg-white/[0.03]' : 'hover:bg-white/[0.02] opacity-50'}
                                        `}
                                    >
                                        <div className="mt-0.5 flex-shrink-0">{getAlertIcon(alert)}</div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                                                {getAlertBadge(alert)}
                                                {alert.is_resolved && <Badge className="bg-emerald-500/10 text-emerald-400 border-none text-[9px] font-bold hover:bg-emerald-500/10">✓</Badge>}
                                                <span className="text-[10px] text-slate-600 font-bold ml-auto flex-shrink-0">{formatTimeAgo(alert.created_at)}</span>
                                            </div>
                                            <p className="text-[13px] text-slate-300 font-medium leading-snug line-clamp-2">{alert.message}</p>
                                            {(alert.contact_name || alert.contact_phone) && (
                                                <p className="text-[10px] text-slate-500 font-bold mt-0.5">{alert.contact_name || alert.contact_phone}</p>
                                            )}
                                        </div>
                                        <div className="flex gap-1 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {alert.contact_id && (
                                                <button onClick={() => navigateToChat(alert)} className="p-1.5 bg-white/5 text-slate-400 rounded-lg hover:bg-white/10 hover:text-white transition-colors" title="Ir al chat">
                                                    <ExternalLink size={12} />
                                                </button>
                                            )}
                                            {!alert.is_resolved && (
                                                <>
                                                    <button onClick={() => handleResolve(alert.id)} className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg hover:bg-emerald-500/20 transition-colors" title="Resolver">
                                                        <CheckCircle2 size={12} />
                                                    </button>
                                                    <button onClick={() => handleDismiss(alert.id)} className="p-1.5 bg-white/5 text-slate-500 rounded-lg hover:bg-white/10 transition-colors" title="Descartar">
                                                        <XCircle size={12} />
                                                    </button>
                                                </>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* RESUMEN CONTACTOS — Compact glassmorphic chips */}
                <div className="space-y-2.5">
                    <h2 className="text-xs md:text-sm font-black text-white uppercase tracking-widest flex items-center gap-2">
                        <User size={14} className="text-indigo-400" /> Resumen
                    </h2>
                    <div className="flex gap-2 flex-wrap">
                        {[
                            { label: "Total", val: contacts.filter(c => c.phone_number !== '56912345678').length },
                            { label: "IA On", val: contacts.filter(c => c.bot_active && c.phone_number !== '56912345678').length, accent: 'text-emerald-400' },
                            { label: "Manual", val: contacts.filter(c => !c.bot_active && c.phone_number !== '56912345678').length, accent: 'text-amber-400', highlight: true },
                            { label: "Alertas", val: timeFilteredAlerts.length },
                            { label: "Resueltas", val: resolvedCount, accent: 'text-emerald-400' },
                        ].map((k, i) => (
                            <div key={i} className={`flex items-center gap-2 px-3 py-2 rounded-xl border backdrop-blur-xl
                                ${k.highlight && parseInt(String(k.val)) > 0 
                                    ? 'bg-amber-500/10 border-amber-500/20' 
                                    : 'bg-white/[0.03] border-white/[0.06]'}`}
                            >
                                <span className={`text-base font-black ${k.accent || 'text-white'}`}>{k.val}</span>
                                <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">{k.label}</span>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    )
}
