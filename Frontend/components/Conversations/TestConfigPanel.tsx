'use client'

import React from 'react'
import { Settings, Info, Activity, Database, AlertTriangle, Smartphone, ShieldCheck, Mail, Monitor, X, Sparkles, Loader2, Save } from 'lucide-react'
import { useCrm } from '@/contexts/CrmContext'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { createClient } from '@/lib/supabase'
import * as Sentry from '@sentry/nextjs'

const supabase = createClient()

export default function TestConfigPanel() {
    const { selectedContact, mobileView, showDesktopInfo, setShowDesktopInfo, setMobileView, setToasts } = useCrm()
    const [prompt, setPrompt] = React.useState('')
    const [isLoading, setIsLoading] = React.useState(false)
    const [isSaving, setIsSaving] = React.useState(false)

    React.useEffect(() => {
        if (selectedContact?.tenant_id) {
            fetchTenantConfig()
            
            // Realtime subscription for instructions
            const channel = supabase
                .channel('realtime-tenant-config')
                .on('postgres_changes', { 
                    event: 'UPDATE', 
                    schema: 'public', 
                    table: 'tenants', 
                    filter: `id=eq.${selectedContact.tenant_id}` 
                }, (payload) => {
                    if (payload.new.system_prompt) {
                        setPrompt(payload.new.system_prompt)
                    }
                })
                .subscribe()

            return () => {
                supabase.removeChannel(channel)
            }
        }
    }, [selectedContact?.tenant_id])

    const fetchTenantConfig = async () => {
        setIsLoading(true)
        try {
            const { data, error } = await supabase
                .from('tenants')
                .select('system_prompt')
                .eq('id', selectedContact.tenant_id)
                .single()
            
            if (data) setPrompt(data.system_prompt)
        } catch (err) {
            console.error(err)
            Sentry.captureException(err as Error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleSavePrompt = async () => {
        setIsSaving(true)
        try {
            const { error } = await supabase
                .from('tenants')
                .update({ system_prompt: prompt })
                .eq('id', selectedContact.tenant_id)
            
            if (!error) {
                setToasts(prev => [...prev, { id: Date.now(), payload: { content: 'Instrucciones actualizadas correctamente! ✅' } }])
            }
        } catch (err) {
            console.error(err)
            Sentry.captureException(err as Error)
        } finally {
            setIsSaving(false)
        }
    }

    if (!selectedContact) return null

    const isVisible = showDesktopInfo || mobileView === 'info'

    return (
        <div className={`
            bg-slate-50 border-l border-slate-200 flex-shrink-0 transition-all duration-300 overflow-y-auto custom-scrollbar
            ${isVisible ? 'w-full fixed inset-0 z-[100] md:static md:w-[320px] lg:w-[420px]' : 'w-0 overflow-hidden opacity-0 p-0 border-none'}
        `}>
            {/* Header with Close for Mobile */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-[101]">
                <h3 className="font-black text-slate-800 tracking-tight flex items-center gap-2">
                    <Settings className="text-indigo-600" size={18} /> CONFIG AGENTE
                </h3>
                <button 
                    onClick={() => { 
                        setMobileView('chat'); 
                        setShowDesktopInfo(false); 
                    }} 
                    className="p-2 hover:bg-slate-100 text-slate-600 rounded-full transition-colors"
                >
                    <X size={20} />
                </button>
            </div>

            <div className="p-5 md:p-6 space-y-6">
                {/* Status Section */}
                <div className="bg-gradient-to-br from-indigo-600 to-violet-700 rounded-2xl p-6 text-white shadow-lg space-y-4">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                            <Sparkles size={20} />
                        </div>
                        <div>
                            <h4 className="font-black text-xs uppercase tracking-widest opacity-70">En tiempo real</h4>
                            <p className="text-lg font-bold tracking-tight">Instrucciones de {selectedContact.name || 'Tenant'}</p>
                        </div>
                    </div>
                    <div className="bg-black/10 rounded-xl p-3 flex justify-between items-center text-xs border border-white/10">
                        <span className="opacity-80 font-medium">Estado del Bot</span>
                        <Badge className={`${selectedContact.bot_active ? 'bg-emerald-400 text-emerald-950' : 'bg-amber-400 text-amber-950'} border-none font-black`}>
                            {selectedContact.bot_active ? 'EJECUTANDO' : 'EN PAUSA'}
                        </Badge>
                    </div>
                </div>

                {/* Instructions Area */}
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                            <Monitor size={12} /> Prompt del Sistema (Instrucciones)
                        </label>
                        {isLoading && <Loader2 className="animate-spin text-indigo-500" size={12} />}
                    </div>
                    <div className="relative group">
                        <textarea 
                            value={prompt}
                            onChange={(e) => setPrompt(e.target.value)}
                            placeholder="Escribe las instrucciones aquí..."
                            className="w-full h-80 text-sm p-4 border rounded-2xl bg-white shadow-sm outline-none focus:ring-2 ring-indigo-500/20 focus:border-indigo-500 transition-all resize-none font-medium text-slate-700 leading-relaxed custom-scrollbar"
                        />
                        <div className="absolute bottom-4 right-4 flex gap-2">
                            <button 
                                onClick={handleSavePrompt}
                                disabled={isSaving || isLoading}
                                className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-xs font-bold shadow-lg hover:bg-indigo-700 active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {isSaving ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                                GUARDAR CAMBIOS
                            </button>
                        </div>
                    </div>
                    <p className="text-[10px] text-slate-400 font-medium leading-relaxed italic">
                        * Los cambios impactan inmediatamente en la próxima respuesta de la IA para este tenant.
                    </p>
                </div>

                <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex gap-3">
                    <AlertTriangle className="text-amber-500 shrink-0" size={18} />
                    <div className="space-y-1">
                        <p className="text-xs font-black text-amber-800 uppercase tracking-tight">ADVERTENCIA</p>
                        <p className="text-[11px] text-amber-700 font-medium leading-normal">
                            Modificar el prompt altera el comportamiento raíz de Javiera. Asegúrate de probar en el sandbox antes de cambios masivos.
                        </p>
                    </div>
                </div>

                {/* Analytics / Stats Card */}
                <Card className="border-slate-200/60 shadow-sm bg-white overflow-hidden">
                    <CardHeader className="bg-slate-50/50 pb-3 py-4">
                        <CardTitle className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                            <Activity size={14} /> Métrica de Eficiencia
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4 space-y-4">
                         <div className="grid grid-cols-2 gap-3">
                            <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100/50">
                                <span className="text-[9px] font-bold text-indigo-400 uppercase">Contexto</span>
                                <div className="text-lg font-black text-indigo-700">95%</div>
                            </div>
                            <div className="p-3 bg-emerald-50/50 rounded-xl border border-emerald-100/50">
                                <span className="text-[9px] font-bold text-emerald-400 uppercase">Acierto</span>
                                <div className="text-lg font-black text-emerald-700">A+</div>
                            </div>
                         </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
