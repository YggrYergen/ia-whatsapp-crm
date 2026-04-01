'use client'

import React from 'react'
import { Settings, Info, Activity, Database, AlertTriangle, Smartphone, ShieldCheck, Mail, Monitor, X } from 'lucide-react'
import { useCrm } from '@/contexts/CrmContext'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export default function TestConfigPanel() {
    const { selectedContact, mobileView, showDesktopInfo, setShowDesktopInfo, setMobileView } = useCrm()

    if (!selectedContact) return null

    const isVisible = showDesktopInfo || mobileView === 'info'

    return (
        <div className={`
            bg-white border-l border-slate-200 flex-shrink-0 transition-all duration-300 overflow-y-auto custom-scrollbar
            ${isVisible ? 'w-full fixed inset-0 z-[100] md:static md:w-[320px] lg:w-[380px]' : 'w-0 overflow-hidden opacity-0 p-0 border-none'}
        `}>
            {/* Header with Close for Mobile */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-[101]">
                <h3 className="font-black text-slate-800 tracking-tight flex items-center gap-2">
                    <Settings className="text-indigo-600" size={18} /> CONFIG PRUEBAS
                </h3>
                <button 
                    onClick={() => { 
                        setMobileView('chat'); 
                        setShowDesktopInfo(false); 
                    }} 
                    className="p-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full transition-colors"
                >
                    <X className="size-6" />
                </button>
            </div>

            <div className="p-5 md:p-6 space-y-6">
            <div className="flex flex-col items-center gap-4 py-6 text-center border-b border-slate-200">
                <div className="w-20 h-20 bg-indigo-600 rounded-2xl flex items-center justify-center text-white shadow-xl rotate-3 scale-110">
                    <Database size={32} />
                </div>
                <div className="space-y-1">
                    <h2 className="text-xl font-black text-slate-800 tracking-tight">CONFIGURACIÓN DE PRUEBAS</h2>
                    <Badge variant="outline" className="bg-white border-indigo-200 text-indigo-700 font-bold px-3 py-0.5">SANDBOX ACTIVO</Badge>
                </div>
            </div>

            <Card className="border-indigo-100 shadow-sm overflow-hidden bg-white">
                <CardHeader className="bg-indigo-50/50 pb-3">
                    <CardTitle className="text-xs font-black uppercase tracking-widest text-indigo-700 flex items-center gap-2">
                        <Activity size={14} /> Telemetría Sandbox
                    </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 space-y-3">
                    <div className="flex justify-between items-center text-sm p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <span className="text-slate-500 font-medium whitespace-nowrap">Estado de Thread</span>
                        <span className="text-emerald-600 font-bold flex items-center gap-1"><Activity size={12}/> Activo</span>
                    </div>
                    <div className="flex justify-between items-center text-sm p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <span className="text-slate-500 font-medium whitespace-nowrap">Aislamiento de DB</span>
                        <span className="text-amber-600 font-bold flex items-center gap-1"><ShieldCheck size={12}/> Total</span>
                    </div>
                </CardContent>
            </Card>

            <Card className="border-slate-200 shadow-sm">
                <CardHeader className="pb-3 border-b">
                    <CardTitle className="text-xs font-black uppercase tracking-widest text-slate-500 flex items-center gap-2">
                        <Settings size={14} /> Parámetros del Agente
                    </CardTitle>
                </CardHeader>
                <CardContent className="pt-4 space-y-4">
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Modelo LLM</label>
                        <select className="w-full text-xs p-2.5 border rounded-lg bg-white outline-none cursor-not-allowed opacity-50" disabled>
                            <option>Gemini 1.5 Pro</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-wider">Temperatura</label>
                        <div className="w-full h-1.5 bg-slate-200 rounded-full">
                            <div className="w-[70%] h-full bg-indigo-500 rounded-full"></div>
                        </div>
                        <div className="flex justify-between text-[9px] font-bold text-slate-400">
                            <span>0.0</span>
                            <span>CONSISTENTE (0.7)</span>
                            <span>1.0</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-4">
                <AlertTriangle className="text-amber-500 shrink-0" size={20} />
                <div className="space-y-1">
                    <p className="text-xs font-black text-amber-800 uppercase tracking-tight">Recordatorio de Auditoría</p>
                    <p className="text-[11px] text-amber-700 leading-relaxed font-medium">
                        Cualquier observación guardada en las burbujas será enviada al buzón de <b>Superadmin Feedback</b> para el refinamiento de Javiera IA.
                    </p>
                </div>
            </div>

            <div className="pt-10 flex flex-col gap-2 opacity-30 text-center pointer-events-none grayscale">
                 <div className="flex flex-col gap-2">
                    <Badge className="w-fit mx-auto bg-slate-200 text-slate-500 uppercase text-[8px] font-black">Próximamente</Badge>
                    <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center justify-center gap-2">
                        <Mail size={12}/> Email Logs <Monitor size={12}/> Analytics Live
                    </div>
                 </div>
            </div>
            </div>
        </div>
    )
}
