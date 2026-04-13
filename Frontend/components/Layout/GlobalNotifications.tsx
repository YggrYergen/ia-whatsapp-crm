'use client'

import React from 'react'
import { AlertTriangle, XCircle, ArrowRight } from 'lucide-react'
import { useCrm } from '@/contexts/CrmContext'
import { useUI } from '@/contexts/UIContext'
import { createClient } from '@/lib/supabase'
import NotificationFeed from './NotificationFeed'

const supabase = createClient()

export default function GlobalNotifications() {
    const { toasts, setToasts, setSelectedContact, setMessages, setMobileView, setSimulationMode, contacts } = useCrm()

    const fetchMessages = async (id: string) => {
        const { data } = await supabase.from('messages').select('*').eq('contact_id', id).order('created_at', { ascending: true })
        if (data) setMessages(data)
    }

    const handleJumpToChat = (toast: any) => {
        // Buscar al paciente real que detonó la alerta (payload.contact_id)
        const targetContact = contacts.find(c => c.id === toast.payload.contact_id);
        
        if (targetContact) {
            setSelectedContact(targetContact);
            fetchMessages(targetContact.id);
            setMobileView('chat');
            setSimulationMode(false);
        } else {
            console.warn("Contact not found for alert redirection", toast.payload.contact_id);
        }
        
        // Remove toast
        setToasts(prev => prev.filter(t => t.id !== toast.id));
    }

    return (
        <>
            <div className="fixed top-4 right-4 z-[100] flex flex-col gap-3 max-w-sm w-full px-4 md:px-0 pointer-events-none">
                {toasts.map(toast => (
                    <div key={toast.id} className="bg-white pointer-events-auto border-l-4 border-rose-500 shadow-2xl rounded-2xl p-4 flex flex-col gap-3 animate-in slide-in-from-right-4 fade-in duration-300">
                        <div className="flex justify-between items-start">
                            <div className="flex items-center gap-2 text-rose-600 font-bold text-xs uppercase tracking-wider">
                                <AlertTriangle size={14} className="animate-pulse" /> Alerta de Sistema
                            </div>
                            <button onClick={() => setToasts(t => t.filter(x => x.id !== toast.id))} className="text-slate-300 hover:text-slate-500 transition-colors">
                                <XCircle size={18} />
                            </button>
                        </div>
                        <div>
                            <p className="text-sm font-bold text-slate-800 leading-tight">{toast.payload?.content}</p>
                        </div>
                        <button 
                            onClick={() => handleJumpToChat(toast)}
                            className="bg-rose-50 hover:bg-rose-100 text-rose-700 font-black text-[10px] uppercase tracking-widest py-2 px-3 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95"
                        >
                            Ir al chat del paciente <ArrowRight size={12} />
                        </button>
                    </div>
                ))}
            </div>

            {/* NotificationFeed MUST be outside the pointer-events-none container */}
            <NotificationFeed />
        </>
    )
}
