'use client'

import React, { useEffect, useState } from 'react'
import { Terminal, Calendar, MessageSquare, Trash2, CheckCircle, RefreshCcw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { createClient } from '@/lib/supabase'
import { useCrm } from '@/contexts/CrmContext'

const supabase = createClient()

export default function AdminFeedbackPage() {
    const { user } = useCrm()
    const [feedbacks, setFeedbacks] = useState<any[]>([])
    const [loading, setLoading] = useState(true)

    const fetchFeedback = async () => {
        setLoading(true)
        const { data, error } = await supabase
            .from('test_feedback')
            .select('*')
            .order('created_at', { ascending: false })
        
        if (data) setFeedbacks(data)
        setLoading(false)
    }

    useEffect(() => {
        if (user?.email === 'tomasgemes@gmail.com') {
            fetchFeedback()
        }
    }, [user])

    if (user?.email !== 'tomasgemes@gmail.com') {
        return (
            <div className="flex flex-col items-center justify-center h-full space-y-4">
                <Badge variant="destructive" className="p-4 text-lg">ACCESO RESTRINGIDO</Badge>
                <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Área exclusiva para el equipo de desarrollo</p>
            </div>
        )
    }

    const handleDelete = async (id: string) => {
        await supabase.from('test_feedback').delete().eq('id', id)
        fetchFeedback()
    }

    return (
        <div className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-8 space-y-8 custom-scrollbar">
            <div className="flex items-center justify-between border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-3xl font-black tracking-tighter flex items-center gap-3">
                        <Terminal className="text-emerald-400" size={32} /> AUDITORÍA DE SANDBOX
                    </h1>
                    <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mt-2 italic">
                        Visualización de feedback recopilado en entornos de prueba
                    </p>
                </div>
                <button 
                    onClick={fetchFeedback}
                    className="p-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-xl transition-all border border-emerald-500/20"
                >
                    <RefreshCcw size={20} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            {loading ? (
                <div className="flex justify-center p-20">
                    <div className="animate-pulse flex items-center gap-3 text-slate-400 font-black uppercase tracking-widest">
                        <Terminal className="animate-bounce" /> Cargando Datos...
                    </div>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-6">
                    {feedbacks.length === 0 ? (
                        <div className="text-center p-20 bg-white/5 rounded-3xl border border-dashed border-white/10 text-slate-500 font-black uppercase tracking-widest text-sm">
                            No hay feedback registrado aún.
                        </div>
                    ) : (
                        feedbacks.map((fb) => (
                            <Card key={fb.id} className="bg-slate-900 border-white/10 shadow-2xl overflow-hidden hover:border-emerald-500/30 transition-colors">
                                <CardHeader className="bg-white/5 flex flex-row items-center justify-between border-b border-white/5 space-y-0 py-4">
                                    <div className="flex items-center gap-4">
                                        <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-black text-[10px]">
                                            ID: {fb.id.split('-')[0]}
                                        </Badge>
                                        <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400">
                                            <Calendar size={14} /> {new Date(fb.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(fb.id)}
                                        className="text-slate-600 hover:text-rose-400 transition-colors"
                                    >
                                        <Trash2 size={18} />
                                    </button>
                                </CardHeader>
                                <CardContent className="p-6">
                                    <div className="space-y-4">
                                        {fb.history?.map((m: any, i: number) => {
                                            const noteObj = fb.notes?.find((n: any) => n.content === m.content);
                                            return (
                                                <div key={i} className={`p-4 rounded-xl border ${m.role === 'assistant' ? 'bg-indigo-500/10 border-indigo-500/20' : 'bg-emerald-500/10 border-emerald-500/20'}`}>
                                                    <div className="flex items-center justify-between mb-2">
                                                        <Badge className={`${m.role === 'assistant' ? 'bg-indigo-500' : 'bg-emerald-500'} text-white text-[8px] font-black uppercase`}>
                                                            {m.role === 'assistant' ? 'IA Response' : 'User Simulation'}
                                                        </Badge>
                                                    </div>
                                                    <p className="text-sm font-medium text-slate-200 leading-relaxed italic">"{m.content}"</p>
                                                    {noteObj && (
                                                        <div className="mt-3 bg-amber-500/20 border border-amber-500/30 p-3 rounded-lg flex items-start gap-3">
                                                            <MessageSquare className="text-amber-400 shrink-0 mt-0.5" size={16} />
                                                            <div>
                                                                <p className="text-[10px] font-black text-amber-500 uppercase tracking-widest">Observación Dev:</p>
                                                                <p className="text-xs font-bold text-amber-200 mt-1">{noteObj.note}</p>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </CardContent>
                            </Card>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
