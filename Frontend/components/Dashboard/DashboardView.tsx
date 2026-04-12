'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { TrendingUp, Calendar as CalendarIcon, User, Activity, Bot, Check, Heart, DollarSign, Clock, AlertCircle, ArrowUpRight, GraduationCap, CheckCircle2, XCircle, AlertTriangle, MessageCircle, Bell, Filter, RefreshCw, ExternalLink } from 'lucide-react'
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useCrm } from '@/contexts/CrmContext'
import { useUI } from '@/contexts/UIContext'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

const supabase = createClient()

type AlertStatus = 'all' | 'pending' | 'resolved' | 'dismissed'

interface AlertItem {
    id: string;
    tenant_id: string;
    contact_id: string | null;
    type: string;
    message: string;
    is_resolved: boolean;
    is_read: boolean;
    created_at: string;
    // Joined fields
    contact_name?: string;
    contact_phone?: string;
}

export default function DashboardView() {
    const { setMobileView, contacts, setSelectedContact, setMessages } = useCrm()
    const router = useRouter()
    
    const [alerts, setAlerts] = useState<AlertItem[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [alertFilter, setAlertFilter] = useState<AlertStatus>('pending')

    // Fetch alerts with contact info
    const fetchAlerts = async () => {
        setIsLoading(true)
        const { data: alertsData } = await supabase
            .from('alerts')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(100)

        if (alertsData) {
            // Enrich with contact info
            const enriched = alertsData.map(a => {
                const contact = contacts.find(c => c.id === a.contact_id)
                return {
                    ...a,
                    contact_name: contact?.name || null,
                    contact_phone: contact?.phone_number || null
                }
            })
            setAlerts(enriched)
        }
        setIsLoading(false)
    }

    useEffect(() => {
        fetchAlerts()

        // Realtime: new alerts
        const sub = supabase
            .channel('dashboard-alerts-live')
            .on('postgres_changes' as any, { event: '*', schema: 'public', table: 'alerts' }, () => {
                fetchAlerts()
            })
            .subscribe()

        return () => { supabase.removeChannel(sub) }
    }, [contacts])

    const filteredAlerts = useMemo(() => {
        switch (alertFilter) {
            case 'pending':
                return alerts.filter(a => !a.is_resolved)
            case 'resolved':
                return alerts.filter(a => a.is_resolved)
            case 'dismissed':
                return [] // Future: dismissed status
            default:
                return alerts
        }
    }, [alerts, alertFilter])

    // Stats
    const pendingCount = alerts.filter(a => !a.is_resolved).length
    const resolvedToday = alerts.filter(a => {
        if (!a.is_resolved) return false
        const today = new Date().toDateString()
        return new Date(a.created_at).toDateString() === today
    }).length
    const escalationAlerts = alerts.filter(a => a.type === 'escalation' && !a.is_resolved)
    const appointmentAlerts = alerts.filter(a => a.message.includes('CITA') || a.message.includes('AGENDADA'))

    const navigateToChat = async (alert: AlertItem) => {
        if (!alert.contact_id) return
        const contact = contacts.find(c => c.id === alert.contact_id)
        if (!contact) return

        // Mark alert as read
        await supabase.from('alerts').update({ is_read: true }).eq('id', alert.id)

        // Fetch messages for this contact
        const { data: msgs } = await supabase
            .from('messages')
            .select('*')
            .eq('contact_id', contact.id)
            .order('timestamp', { ascending: true })
        
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
        if (alert.type === 'escalation') return <AlertTriangle size={14} className="text-rose-500" />
        if (alert.message.includes('AGENDADA') || alert.message.includes('NUEVA CITA')) return <CalendarIcon size={14} className="text-emerald-500" />
        if (alert.message.includes('CANCELADA')) return <XCircle size={14} className="text-red-500" />
        if (alert.message.includes('RE-AGENDADA')) return <RefreshCw size={14} className="text-blue-500" />
        return <Bell size={14} className="text-slate-400" />
    }

    const getAlertBadge = (alert: AlertItem) => {
        if (alert.type === 'escalation') return <Badge className="bg-rose-100 text-rose-700 border-none text-[9px] font-bold hover:bg-rose-100">Escalación</Badge>
        if (alert.message.includes('NUEVA CITA') || alert.message.includes('AGENDADA')) return <Badge className="bg-emerald-100 text-emerald-700 border-none text-[9px] font-bold hover:bg-emerald-100">Cita</Badge>
        if (alert.message.includes('CANCELADA')) return <Badge className="bg-red-100 text-red-700 border-none text-[9px] font-bold hover:bg-red-100">Cancelación</Badge>
        if (alert.message.includes('RE-AGENDADA')) return <Badge className="bg-blue-100 text-blue-700 border-none text-[9px] font-bold hover:bg-blue-100">Reagendada</Badge>
        return <Badge className="bg-slate-100 text-slate-600 border-none text-[9px] font-bold hover:bg-slate-100">Info</Badge>
    }

    const formatTimeAgo = (dateStr: string) => {
        const mins = Math.floor((Date.now() - new Date(dateStr).getTime()) / 60000)
        if (mins < 1) return 'Ahora'
        if (mins < 60) return `Hace ${mins} min`
        const hrs = Math.floor(mins / 60)
        if (hrs < 24) return `Hace ${hrs}h`
        const days = Math.floor(hrs / 24)
        return `Hace ${days}d`
    }

    return (
        <div className="flex-1 overflow-y-auto bg-slate-50 w-full transition-all pb-24 md:pb-10">
            <div className="w-full max-w-7xl mx-auto p-4 md:p-8 space-y-6 md:space-y-8">
                
                {/* BLOQUE 1: STATUS AT A GLANCE */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                            <Heart className="text-rose-500 fill-rose-500" size={20} /> ESTADO DEL SISTEMA
                        </h2>
                        <Badge className={`font-bold border-none ${pendingCount > 0 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                            {pendingCount > 0 ? `${pendingCount} pendiente${pendingCount > 1 ? 's' : ''}` : 'TODO OK ✓'}
                        </Badge>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-5 pb-4 px-4">
                                <div className="p-2 w-9 h-9 bg-emerald-50 rounded-lg flex items-center justify-center mb-3 text-emerald-600">
                                    <Bot size={20} />
                                </div>
                                <h3 className="text-2xl md:text-3xl font-black text-slate-800 tracking-tighter">
                                    {contacts.filter(c => c.bot_active && c.phone_number !== '56912345678').length}
                                </h3>
                                <p className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Chats con IA activa</p>
                            </CardContent>
                        </Card>
                        <Card className={`border-none shadow-sm hover:shadow-md transition-shadow ${pendingCount > 0 ? 'bg-amber-50 ring-1 ring-amber-200' : 'bg-white'}`}>
                            <CardContent className="pt-5 pb-4 px-4">
                                <div className={`p-2 w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${pendingCount > 0 ? 'bg-amber-100 text-amber-600' : 'bg-slate-50 text-slate-400'}`}>
                                    <AlertCircle size={20} />
                                </div>
                                <h3 className="text-2xl md:text-3xl font-black text-slate-800 tracking-tighter">{pendingCount}</h3>
                                <p className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Alertas pendientes</p>
                            </CardContent>
                        </Card>
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-5 pb-4 px-4">
                                <div className="p-2 w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center mb-3 text-blue-600">
                                    <CalendarIcon size={20} />
                                </div>
                                <h3 className="text-2xl md:text-3xl font-black text-slate-800 tracking-tighter">{appointmentAlerts.length}</h3>
                                <p className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Eventos de agenda</p>
                            </CardContent>
                        </Card>
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-5 pb-4 px-4">
                                <div className="p-2 w-9 h-9 bg-emerald-50 rounded-lg flex items-center justify-center mb-3 text-emerald-600">
                                    <Check size={20} />
                                </div>
                                <h3 className="text-2xl md:text-3xl font-black text-slate-800 tracking-tighter">{resolvedToday}</h3>
                                <p className="text-[9px] md:text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Resueltas hoy</p>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* BLOQUE 2: INTERVENCIÓN MANUAL (LIVE) */}
                {escalationAlerts.length > 0 && (
                    <div className="space-y-3">
                        <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                            <AlertCircle className="text-rose-500" size={20} /> INTERVENCIÓN MANUAL
                            <span className="ml-auto">
                                <Badge className="bg-rose-500 text-white border-none text-[10px] font-black animate-gentle-pulse hover:bg-rose-500">
                                    {escalationAlerts.length} PENDIENTE{escalationAlerts.length > 1 ? 'S' : ''}
                                </Badge>
                            </span>
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border border-rose-100 overflow-hidden divide-y divide-rose-50">
                            {escalationAlerts.map((alert) => (
                                <div key={alert.id} className="p-4 flex items-center justify-between hover:bg-rose-50/30 transition-colors gap-3">
                                    <div className="flex gap-3 items-start flex-1 min-w-0">
                                        <div className="w-2 h-2 bg-rose-500 rounded-full animate-gentle-pulse mt-2 flex-shrink-0" />
                                        <div className="min-w-0 flex-1">
                                            <p className="text-sm font-black text-slate-800 truncate">{alert.contact_name || alert.contact_phone || 'Contacto desconocido'}</p>
                                            <p className="text-xs text-rose-600 font-medium line-clamp-2 mt-0.5">{alert.message}</p>
                                            <span className="text-[10px] text-slate-400 font-bold mt-1 block">{formatTimeAgo(alert.created_at)}</span>
                                        </div>
                                    </div>
                                    <div className="flex gap-2 flex-shrink-0">
                                        {alert.contact_id && (
                                            <button 
                                                onClick={() => navigateToChat(alert)} 
                                                className="p-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors"
                                                title="Ir al chat"
                                            >
                                                <ArrowUpRight size={16} />
                                            </button>
                                        )}
                                        <button 
                                            onClick={() => handleResolve(alert.id)}
                                            className="p-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
                                            title="Resolver"
                                        >
                                            <CheckCircle2 size={16} />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* BLOQUE 3: HISTORIAL DE ALERTAS */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                            <Activity className="text-blue-500" size={20} /> HISTORIAL DE ALERTAS
                        </h2>
                        <button onClick={fetchAlerts} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                            <RefreshCw size={16} />
                        </button>
                    </div>

                    {/* Filter tabs */}
                    <div className="flex gap-1.5 overflow-x-auto pb-1">
                        {([
                            { key: 'pending', label: 'Pendientes', count: pendingCount },
                            { key: 'all', label: 'Todas', count: alerts.length },
                            { key: 'resolved', label: 'Resueltas', count: alerts.filter(a => a.is_resolved).length },
                        ] as { key: AlertStatus; label: string; count: number }[]).map((tab) => (
                            <button
                                key={tab.key}
                                onClick={() => setAlertFilter(tab.key)}
                                className={`py-1.5 px-3 rounded-lg text-[11px] font-bold uppercase tracking-wider transition-all whitespace-nowrap flex items-center gap-1.5
                                    ${alertFilter === tab.key
                                        ? tab.key === 'pending' ? 'bg-amber-500 text-white shadow-sm' : 'bg-slate-900 text-white shadow-sm'
                                        : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                            >
                                {tab.label}
                                <span className={`min-w-[18px] h-[18px] rounded-full text-[10px] font-black flex items-center justify-center
                                    ${alertFilter === tab.key ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-500'}`}>
                                    {tab.count}
                                </span>
                            </button>
                        ))}
                    </div>

                    {/* Alert List */}
                    <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
                        {isLoading ? (
                            <div className="p-8 text-center text-slate-400">
                                <RefreshCw size={20} className="animate-spin mx-auto mb-2" />
                                <p className="text-sm font-medium">Cargando alertas...</p>
                            </div>
                        ) : filteredAlerts.length === 0 ? (
                            <div className="p-8 text-center text-slate-400 space-y-2">
                                <CheckCircle2 size={32} className="mx-auto text-emerald-300" />
                                <p className="text-sm font-bold">
                                    {alertFilter === 'pending' ? 'No hay alertas pendientes 🎉' : 'No hay alertas en esta categoría'}
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-slate-50 max-h-[60vh] overflow-y-auto custom-scrollbar">
                                {filteredAlerts.map((alert) => (
                                    <div 
                                        key={alert.id} 
                                        className={`p-3 md:p-4 flex items-start gap-3 transition-colors group
                                            ${!alert.is_resolved ? 'hover:bg-amber-50/50' : 'hover:bg-slate-50 opacity-70'}
                                        `}
                                    >
                                        <div className="mt-0.5 flex-shrink-0">{getAlertIcon(alert)}</div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1 flex-wrap">
                                                {getAlertBadge(alert)}
                                                {alert.is_resolved && (
                                                    <Badge className="bg-emerald-50 text-emerald-600 border-none text-[9px] font-bold hover:bg-emerald-50">✓ Resuelta</Badge>
                                                )}
                                                <span className="text-[10px] text-slate-400 font-bold ml-auto flex-shrink-0">{formatTimeAgo(alert.created_at)}</span>
                                            </div>
                                            <p className="text-sm text-slate-700 font-medium leading-snug line-clamp-2">{alert.message}</p>
                                            {(alert.contact_name || alert.contact_phone) && (
                                                <p className="text-[11px] text-slate-400 font-bold mt-1">
                                                    {alert.contact_name || alert.contact_phone}
                                                </p>
                                            )}
                                        </div>
                                        <div className="flex gap-1.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                            {alert.contact_id && (
                                                <button 
                                                    onClick={() => navigateToChat(alert)}
                                                    className="p-1.5 bg-slate-100 text-slate-600 rounded-lg hover:bg-slate-200 transition-colors"
                                                    title="Ir al chat"
                                                >
                                                    <ExternalLink size={14} />
                                                </button>
                                            )}
                                            {!alert.is_resolved && (
                                                <>
                                                    <button 
                                                        onClick={() => handleResolve(alert.id)}
                                                        className="p-1.5 bg-emerald-100 text-emerald-600 rounded-lg hover:bg-emerald-200 transition-colors"
                                                        title="Resolver"
                                                    >
                                                        <CheckCircle2 size={14} />
                                                    </button>
                                                    <button 
                                                        onClick={() => handleDismiss(alert.id)}
                                                        className="p-1.5 bg-slate-100 text-slate-400 rounded-lg hover:bg-slate-200 transition-colors"
                                                        title="Descartar"
                                                    >
                                                        <XCircle size={14} />
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

                {/* BLOQUE 4: CONTACTOS ACTIVOS OVERVIEW */}
                <div className="space-y-3">
                    <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                        <GraduationCap className="text-indigo-500" size={20} /> RESUMEN DE CONTACTOS
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
                        {[
                            { label: "Total Contactos", val: String(contacts.filter(c => c.phone_number !== '56912345678').length) },
                            { label: "IA Activa", val: String(contacts.filter(c => c.bot_active && c.phone_number !== '56912345678').length) },
                            { label: "Intervención Manual", val: String(contacts.filter(c => !c.bot_active && c.phone_number !== '56912345678').length), highlight: true },
                            { label: "Total Alertas", val: String(alerts.length) },
                            { label: "Resueltas Hoy", val: String(resolvedToday) },
                        ].map((k, i) => (
                            <div key={i} className={`text-center p-4 rounded-2xl shadow-sm border ${k.highlight && parseInt(k.val) > 0 ? 'bg-amber-50 border-amber-200' : 'bg-white border-slate-100'}`}>
                                <p className="text-lg font-black text-slate-800">{k.val}</p>
                                <p className="text-[9px] font-bold text-slate-400 uppercase tracking-tighter mt-0.5">{k.label}</p>
                            </div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    )
}
