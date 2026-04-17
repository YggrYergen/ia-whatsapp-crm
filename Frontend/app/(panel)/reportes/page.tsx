'use client'

import React from 'react'
import { FileBarChart2, Construction, Sparkles, TrendingUp, Users, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export default function ReportesPage() {
    return (
        <div className="flex-1 overflow-y-auto bg-slate-950 text-slate-100 p-8 space-y-8 custom-scrollbar">
            <div className="flex items-center justify-between border-b border-white/10 pb-6">
                <div>
                    <h1 className="text-3xl font-black tracking-tighter flex items-center gap-3">
                        <FileBarChart2 className="text-emerald-400" size={32} /> REPORTES Y ANALÍTICAS
                    </h1>
                    <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mt-2 italic">
                        Visualización de métricas de Inteligencia Artificial
                    </p>
                </div>
                <Badge className="bg-indigo-500/20 text-indigo-400 border-indigo-500/30 px-3 py-1 font-bold">
                    Próximamente
                </Badge>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 opacity-60">
                {/* Mocks de Metricas */}
                <Card className="bg-slate-900 border-white/10 shadow-2xl overflow-hidden">
                    <CardHeader className="bg-white/5 pb-4">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-sm font-bold text-slate-300">Tasa de Conversión IA</CardTitle>
                            <TrendingUp className="text-emerald-400" size={16} />
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <div className="text-3xl font-black text-white">42.8%</div>
                        <p className="text-xs text-slate-500 mt-1 font-medium">+15.2% vs mes anterior</p>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900 border-white/10 shadow-2xl overflow-hidden">
                    <CardHeader className="bg-white/5 pb-4">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-sm font-bold text-slate-300">Mensajes Procesados</CardTitle>
                            <Sparkles className="text-indigo-400" size={16} />
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <div className="text-3xl font-black text-white">1,204</div>
                        <p className="text-xs text-slate-500 mt-1 font-medium">Equivalente a 80h humanas</p>
                    </CardContent>
                </Card>

                <Card className="bg-slate-900 border-white/10 shadow-2xl overflow-hidden">
                    <CardHeader className="bg-white/5 pb-4">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-sm font-bold text-slate-300">Agendamientos Exitosos</CardTitle>
                            <Calendar className="text-amber-400" size={16} />
                        </div>
                    </CardHeader>
                    <CardContent className="p-6">
                        <div className="text-3xl font-black text-white">142</div>
                        <p className="text-xs text-slate-500 mt-1 font-medium">Autónomos sin intervención</p>
                    </CardContent>
                </Card>
            </div>

            <div className="relative w-full h-80 rounded-3xl overflow-hidden border border-white/10 bg-gradient-to-br from-slate-900 to-slate-950 flex flex-col items-center justify-center p-8 text-center mt-8">
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150 mix-blend-overlay"></div>
                <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mb-6 relative z-10 shadow-2xl">
                    <Construction className="text-slate-400" size={28} />
                </div>
                <h2 className="text-2xl font-black text-white mb-2 relative z-10 tracking-tight">Módulo en Construcción</h2>
                <p className="text-slate-400 max-w-md text-sm leading-relaxed relative z-10 font-medium">
                    Estamos preparando una suite completa de reportería que te permitirá medir el impacto real y el ROI de los agentes de Inteligencia Artificial en tus clientes.
                </p>
                <div className="mt-8 relative z-10">
                    <div className="flex gap-2 justify-center">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <div className="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <div className="w-2 h-2 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                </div>
            </div>
        </div>
    )
}
