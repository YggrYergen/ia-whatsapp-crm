'use client'

import React from 'react'
import { TrendingUp, Calendar as CalendarIcon, User, XCircle, Activity, Bot, Check, Sparkles, MessageCircle, Heart, DollarSign, Clock, AlertCircle, ArrowUpRight, GraduationCap } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useCrm } from '@/contexts/CrmContext'

export default function DashboardView() {
    const { setMobileView } = useCrm()

    return (
        <div className="flex-1 overflow-y-auto bg-slate-50 w-full transition-all pb-10">
            <div className="w-full max-w-7xl mx-auto p-4 md:p-8 space-y-8">
                
                {/* BLOQUE 1: PAZ MENTAL */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                            <Heart className="text-rose-500 fill-rose-500" size={20} /> PAZ MENTAL
                        </h2>
                        <Badge className="bg-emerald-100 text-emerald-700 border-none font-bold">ACTIVO AHORA</Badge>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-6">
                                <div className="p-2 w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center mb-4 text-emerald-600">
                                    <Bot size={24} />
                                </div>
                                <h3 className="text-3xl font-black text-slate-800 tracking-tighter">14</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Chats atendidos solos hoy</p>
                            </CardContent>
                        </Card>
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-6">
                                <div className="p-2 w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-4 text-blue-600">
                                    <Clock size={24} />
                                </div>
                                <h3 className="text-3xl font-black text-slate-800 tracking-tighter">~7.5 hrs</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Tiempo de gestión ahorrado</p>
                            </CardContent>
                        </Card>
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-6">
                                <div className="p-2 w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mb-4 text-amber-600">
                                    <Check size={24} />
                                </div>
                                <h3 className="text-3xl font-black text-slate-800 tracking-tighter">92%</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Tasa de resolución IA</p>
                            </CardContent>
                        </Card>
                        <Card className="border-none shadow-sm bg-white hover:shadow-md transition-shadow">
                            <CardContent className="pt-6">
                                <div className="p-2 w-10 h-10 bg-indigo-50 rounded-lg flex items-center justify-center mb-4 text-indigo-600">
                                    <CalendarIcon size={24} />
                                </div>
                                <h3 className="text-3xl font-black text-slate-800 tracking-tighter">6</h3>
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">Citas agendadas por Javiera</p>
                            </CardContent>
                        </Card>
                    </div>
                </div>

                {/* BLOQUE 2: OPORTUNIDADES DE INGRESO */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                             <DollarSign className="text-emerald-500" size={20} /> TOP LEADS (SCORING)
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
                            <div className="p-4 space-y-3">
                                {[
                                    { name: "María José P.", score: 14, status: "Nivel Avanzado", income: "$450k" },
                                    { name: "Carla Espinoza", score: 11, status: "Nivel Intermedio", income: "$320k" },
                                    { name: "Lucía Fernández", score: 9, status: "Nivel Intermedio", income: "$320k" }
                                ].map((lead, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 bg-slate-100 rounded-full flex items-center justify-center text-slate-500 font-bold text-xs">{lead.name[0]}</div>
                                            <div>
                                                <p className="text-sm font-bold text-slate-800">{lead.name}</p>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">{lead.status}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-xs font-black text-emerald-600">{lead.income}</p>
                                            <Badge className="text-[9px] bg-indigo-50 text-indigo-600 border-none px-1.5">{lead.score} pts</Badge>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                    <div className="space-y-4">
                        <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                             <TrendingUp className="text-amber-500" size={20} /> DESERTORES A RECUPERAR
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
                             <div className="p-4 space-y-3">
                                {[
                                    { name: "Valentina Mora", last: "32 días", prob: "85%", potential: "$1.2M" },
                                    { name: "Antonia Reyes", last: "45 días", prob: "70%", potential: "$850k" },
                                    { name: "Javiera Valdés", last: "60 días", prob: "60%", potential: "$450k" }
                                ].map((lead, i) => (
                                    <div key={i} className="flex items-center justify-between p-3 rounded-xl hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 bg-amber-50 rounded-full flex items-center justify-center text-amber-600 font-bold text-xs"><Clock size={14}/></div>
                                            <div>
                                                <p className="text-sm font-bold text-slate-800">{lead.name}</p>
                                                <p className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter">Última sesión: {lead.last}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-xs font-black text-slate-800">{lead.potential}</p>
                                            <p className="text-[10px] text-emerald-500 font-bold">{lead.prob} cierre</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>

                {/* BLOQUE 3: ACCIONES NECESARIAS (CTA) */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 space-y-4">
                        <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                             <AlertCircle className="text-rose-500" size={20} /> INTERVENCIÓN MANUAL
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border border-rose-100 overflow-hidden">
                             {[
                                { name: "Francisca Toro", motive: "Dolor cratrizal detectado", time: "12:45" },
                                { name: "Ingrid Valenzuela", motive: "Scoring > 12 (Lipedema)", time: "11:20" }
                             ].map((action, i) => (
                                <div key={i} className="p-4 border-b last:border-none flex items-center justify-between hover:bg-rose-50/30 transition-colors">
                                    <div className="flex gap-4 items-center">
                                        <div className="w-2 h-2 bg-rose-500 rounded-full animate-pulse" />
                                        <div>
                                            <p className="text-sm font-black text-slate-800">{action.name}</p>
                                            <p className="text-xs text-rose-600 font-medium">{action.motive}</p>
                                        </div>
                                    </div>
                                    <button onClick={() => setMobileView('chat')} className="p-2 bg-slate-900 text-white rounded-lg hover:bg-slate-800 transition-colors">
                                        <ArrowUpRight size={16} />
                                    </button>
                                </div>
                             ))}
                        </div>
                    </div>
                    <div className="space-y-4">
                        <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                             <Activity className="text-blue-500" size={20} /> NOTIFICACIONES
                        </h2>
                        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden p-4 space-y-3">
                            <div className="p-3 bg-blue-50/50 rounded-xl border border-blue-100">
                                <p className="text-[11px] font-bold text-blue-700 leading-tight">Javiera IA envió protocolo pre-sesión a 4 pacientes.</p>
                                <span className="text-[9px] text-blue-400 font-bold uppercase mt-1 block">Hace 5 min</span>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 opacity-60">
                                <p className="text-[11px] font-bold text-slate-600 leading-tight">Resumen semanal generado con éxito.</p>
                                <span className="text-[9px] text-slate-400 font-bold uppercase mt-1 block">Ayer</span>
                            </div>
                            <button className="w-full text-center py-2 text-[10px] font-black text-slate-400 uppercase tracking-widest hover:text-slate-600 transition-colors">Ver Historial Completo</button>
                        </div>
                    </div>
                </div>

                {/* BLOQUE 4: RESUMEN DE DESEMPEÑO (KPIs LIVE) */}
                <div className="space-y-4">
                    <h2 className="text-xl font-black text-slate-800 tracking-tight flex items-center gap-2">
                        <GraduationCap className="text-indigo-500" size={20} /> DESEMPEÑO DEL ASISTENTE
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                        {[
                            { label: "Mensajes / Hora", val: "42" },
                            { label: "Tiempo Resp.", val: "1.2s" },
                            { label: "Satisfacción", val: "4.9/5" },
                            { label: "Precisión Tool", val: "98%" },
                            { label: "Ahorro Estim.", val: "$850 USD" },
                            { label: "Fallback", val: "2%" }
                        ].map((k, i) => (
                            <div key={i} className="text-center p-4 bg-white rounded-2xl shadow-sm border border-slate-100">
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
