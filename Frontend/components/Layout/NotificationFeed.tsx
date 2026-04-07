'use client'

import React from 'react'
import { Bell, X, CheckCheck, Loader2 } from 'lucide-react'
import { useUI } from '@/contexts/UIContext'
import { formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'

export default function NotificationFeed() {
    const { notifications, isNotificationFeedOpen, setIsNotificationFeedOpen, markAsRead, markAllAsRead } = useUI()

    if (!isNotificationFeedOpen) return null

    return (
        <>
            <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-[100] md:hidden" onClick={() => setIsNotificationFeedOpen(false)} />
            
            <div className={`
                fixed top-0 right-0 h-full w-full md:w-[400px] bg-white shadow-2xl z-[101] border-l border-slate-200
                flex flex-col transform transition-transform duration-300 ease-in-out
                ${isNotificationFeedOpen ? 'translate-x-0' : 'translate-x-full'}
            `}>
                <div className="p-6 border-b border-slate-100 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center">
                            <Bell size={20} />
                        </div>
                        <div>
                            <h2 className="text-xl font-black text-slate-800 tracking-tight">Notificaciones</h2>
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
                            onClick={() => setIsNotificationFeedOpen(false)}
                            className="w-10 h-10 flex items-center justify-center text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-xl transition-colors"
                        >
                            <X size={20} />
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
                    {notifications.length === 0 ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400">
                            <Bell size={48} className="mb-4 opacity-20" />
                            <p className="font-bold">No hay notificaciones</p>
                        </div>
                    ) : (
                        notifications.map(notif => (
                            <div 
                                key={notif.id} 
                                className={`p-4 rounded-2xl border transition-all ${
                                    notif.is_read 
                                        ? 'bg-white border-slate-200 opacity-60' 
                                        : 'bg-white border-emerald-500 shadow-lg shadow-emerald-500/10'
                                }`}
                                onClick={() => markAsRead(notif.id)}
                            >
                                <div className="flex justify-between items-start gap-2">
                                    <div className="flex-1">
                                        <div className="flex justify-between items-center mb-1">
                                            <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${
                                                notif.type === 'error' ? 'bg-rose-100 text-rose-700' :
                                                notif.type === 'handoff' ? 'bg-amber-100 text-amber-700' :
                                                'bg-slate-100 text-slate-600'
                                            }`}>
                                                {notif.type || 'Sistema'}
                                            </span>
                                            <span className="text-[10px] font-bold text-slate-400">
                                                {formatDistanceToNow(new Date(notif.created_at), { addSuffix: true, locale: es })}
                                            </span>
                                        </div>
                                        <p className="text-sm font-semibold text-slate-700 mt-2">{notif.message}</p>
                                    </div>
                                    {!notif.is_read && (
                                        <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1 flex-shrink-0" />
                                    )}
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </>
    )
}
