'use client'

import React from 'react'
import { Bell, X, CheckCheck, AlertTriangle, Calendar, RefreshCw, XCircle, ExternalLink, CheckCircle2 } from 'lucide-react'
import { useUI } from '@/contexts/UIContext'
import { useCrm } from '@/contexts/CrmContext'
import { createClient } from '@/lib/supabase'
import { useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

const supabase = createClient()

export default function NotificationFeed() {
    const { notifications, isNotificationFeedOpen, setIsNotificationFeedOpen, markAsRead, markAllAsRead } = useUI()
    const { contacts, setSelectedContact, setMessages, setMobileView } = useCrm()
    const router = useRouter()

    if (!isNotificationFeedOpen) return null

    const closeFeed = () => setIsNotificationFeedOpen(false)

    const getNotifIcon = (notif: any) => {
        if (notif.type === 'escalation') return <AlertTriangle size={16} className="text-rose-500" />
        if (notif.message?.includes('NUEVA CITA') || notif.message?.includes('AGENDADA')) return <Calendar size={16} className="text-emerald-500" />
        if (notif.message?.includes('CANCELADA')) return <XCircle size={16} className="text-red-500" />
        if (notif.message?.includes('RE-AGENDADA')) return <RefreshCw size={16} className="text-blue-500" />
        return <Bell size={16} className="text-slate-400" />
    }

    const getNotifLabel = (notif: any) => {
        if (notif.type === 'escalation') return { text: 'Escalación', classes: 'bg-rose-100 text-rose-700' }
        if (notif.message?.includes('NUEVA CITA') || notif.message?.includes('AGENDADA')) return { text: 'Cita agendada', classes: 'bg-emerald-100 text-emerald-700' }
        if (notif.message?.includes('CANCELADA')) return { text: 'Cancelación', classes: 'bg-red-100 text-red-700' }
        if (notif.message?.includes('RE-AGENDADA')) return { text: 'Reagendada', classes: 'bg-blue-100 text-blue-700' }
        return { text: notif.type || 'Sistema', classes: 'bg-slate-100 text-slate-600' }
    }

    const navigateToChat = async (notif: any) => {
        if (!notif.contact_id) return
        const contact = contacts.find((c: any) => c.id === notif.contact_id)
        if (!contact) return

        markAsRead(notif.id)
        const { data: msgs } = await supabase
            .from('messages')
            .select('*')
            .eq('contact_id', contact.id)
            .order('timestamp', { ascending: true })
        
        if (msgs) setMessages(msgs)
        setSelectedContact(contact)
        setMobileView('chat')
        closeFeed()
        router.push('/chats')
    }

    const hasContact = (n: any) => !!n.contact_id && contacts.some((c: any) => c.id === n.contact_id)

    return (
        <>
            {/* Backdrop — covers full screen, tapping closes */}
            <div 
                className="fixed inset-0 bg-slate-900/30 backdrop-blur-sm z-[100]" 
                onClick={closeFeed}
                onTouchEnd={(e) => { e.preventDefault(); closeFeed(); }}
            />
            
            {/* Panel — stops above the 60px mobile nav */}
            <div className="fixed top-0 right-0 w-full md:w-[400px] bg-white shadow-2xl z-[101] border-l border-slate-200 flex flex-col animate-slide-in-right h-[calc(100dvh-60px)] md:h-full md:bottom-0 bottom-[60px]">
                
                {/* Header */}
                <div className="p-4 md:p-6 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center">
                            <Bell size={20} />
                        </div>
                        <div>
                            <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight">Notificaciones</h2>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{notifications.filter(n => !n.is_read).length} no leídas</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button 
                            onClick={markAllAsRead}
                            className="w-10 h-10 flex items-center justify-center text-slate-400 hover:text-emerald-500 hover:bg-emerald-50 rounded-xl transition-colors"
                            title="Marcar todas como leídas"
                        >
                            <CheckCheck size={20} />
                        </button>
                        <button 
                            onClick={closeFeed}
                            onTouchEnd={(e) => { e.preventDefault(); e.stopPropagation(); closeFeed(); }}
                            className="w-10 h-10 flex items-center justify-center text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-colors active:bg-rose-100"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                {/* Scrollable content */}
                <div className="flex-1 overflow-y-auto overscroll-contain p-3 md:p-4 space-y-2 bg-slate-50/50 -webkit-overflow-scrolling-touch">
                    {notifications.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400 py-16">
                            <Bell size={48} className="mb-4 opacity-20" />
                            <p className="font-bold">No hay notificaciones</p>
                        </div>
                    ) : (
                        notifications.map(notif => {
                            const label = getNotifLabel(notif)
                            const canNavigate = hasContact(notif)
                            
                            return (
                                <div 
                                    key={notif.id} 
                                    className={`p-3 md:p-4 rounded-2xl border transition-all cursor-pointer group ${
                                        notif.is_read 
                                            ? 'bg-white border-slate-100 opacity-60 hover:opacity-80' 
                                            : 'bg-white border-emerald-200 shadow-sm hover:shadow-md'
                                    }`}
                                    onClick={() => markAsRead(notif.id)}
                                >
                                    <div className="flex gap-3 items-start">
                                        <div className="mt-0.5 flex-shrink-0">{getNotifIcon(notif)}</div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex justify-between items-center mb-1">
                                                <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${label.classes}`}>
                                                    {label.text}
                                                </span>
                                                <span className="text-[10px] font-bold text-slate-400 flex-shrink-0 ml-2">
                                                    {formatDistanceToNow(new Date(notif.created_at), { addSuffix: true, locale: es })}
                                                </span>
                                            </div>
                                            <p className="text-sm font-semibold text-slate-700 mt-1.5 leading-snug line-clamp-3">{notif.message}</p>
                                            
                                            {canNavigate && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); navigateToChat(notif); }}
                                                    className="mt-2 flex items-center gap-1.5 text-[11px] font-bold text-blue-600 hover:text-blue-700 transition-colors"
                                                >
                                                    <ExternalLink size={12} /> Ir al chat
                                                </button>
                                            )}
                                        </div>
                                        {!notif.is_read && (
                                            <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1 flex-shrink-0" />
                                        )}
                                    </div>
                                </div>
                            )
                        })
                    )}
                </div>
            </div>
        </>
    )
}
