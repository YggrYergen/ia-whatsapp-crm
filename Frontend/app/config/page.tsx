'use client'

import React, { useState, useEffect } from 'react'
import * as Sentry from '@sentry/nextjs'
import { createClient } from '@/lib/supabase'
import { Save, Bot, Info, Sparkles, Zap, ChevronLeft, Calendar, CheckCircle2, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import Link from 'next/link'

export default function ConfigPanel() {
    const supabase = createClient()
    const [tenant, setTenant] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)

    useEffect(() => {
        fetchTenant()
    }, [])

    const fetchTenant = async () => {
        const { data } = await supabase.from('tenants').select('*').limit(1).single()
        if (data) setTenant(data)
        setLoading(false)
    }

    const handleSave = async () => {
        if (!tenant) return
        // BUG-2 fix: Block save if system prompt exceeds 4000 characters
        // This is a hard limit to prevent excessively long prompts from degrading LLM performance
        if (tenant.system_prompt && tenant.system_prompt.length > 4000) {
            Sentry.captureMessage(`System prompt exceeds 4000 char limit: ${tenant.system_prompt.length} chars`, 'warning')
            alert(`El System Prompt excede el límite de 4000 caracteres (actual: ${tenant.system_prompt.length}). Por favor reduce el contenido antes de guardar.`)
            return
        }
        setSaving(true)
        const { error } = await supabase.from('tenants').update({
            llm_provider: tenant.llm_provider,
            llm_model: tenant.llm_model,
            system_prompt: tenant.system_prompt
        }).eq('id', tenant.id)

        setSaving(false)
        if (!error) {
             // We could use shadcn toast here if we had it working, but for now simple feedback
             alert('Configuración guardada exitosamente')
        }
    }

    if (loading) return (
        <div className="flex items-center justify-center h-screen bg-slate-50">
             <div className="flex flex-col items-center gap-4">
                 <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                 <p className="text-slate-500 font-bold animate-pulse">Cargando configuración Enterprise...</p>
             </div>
        </div>
    )

    return (
        <TooltipProvider>
            <div className="min-h-screen bg-slate-50/50 p-4 md:p-12">
                <div className="max-w-4xl mx-auto space-y-8">
                    
                    <div className="flex items-center justify-between">
                        <Link href="/">
                            <Button variant="ghost" className="text-slate-500 hover:text-slate-800 gap-2 font-bold">
                                <ChevronLeft size={20} /> Volver al Dashboard
                            </Button>
                        </Link>
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 px-4 py-1 font-black uppercase tracking-widest text-[10px]">Configuración Global</Badge>
                    </div>

                    <Card className="border-slate-100 shadow-2xl overflow-hidden rounded-[2rem]">
                        <CardHeader className="bg-slate-900 text-white p-8 md:p-10 relative overflow-hidden">
                            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                                <div className="flex items-center gap-5">
                                    <div className="w-16 h-16 bg-emerald-500 rounded-2xl flex items-center justify-center shadow-lg transform -rotate-3">
                                        <Bot size={36} className="text-white" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-3xl font-black tracking-tight">Cerebro del Asistente</CardTitle>
                                        <CardDescription className="text-slate-400 font-medium text-lg mt-1">Configura el modelo y compartamiento de la IA para toda la clínica.</CardDescription>
                                    </div>
                                </div>
                                <Button 
                                    onClick={handleSave} 
                                    disabled={saving}
                                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-black px-8 py-6 rounded-2xl shadow-xl shadow-emerald-500/20 text-lg transition-all active:scale-95"
                                >
                                    {saving ? 'Guardando...' : <><Save size={22} className="mr-2" /> Guardar Cambios</>}
                                </Button>
                            </div>
                            {/* Abstract bg element */}
                            <div className="absolute top-0 right-0 p-10 opacity-10 rotate-12">
                                <Sparkles size={200} />
                            </div>
                        </CardHeader>
                        
                        <CardContent className="p-8 md:p-10 space-y-10 bg-white">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                <div className="space-y-3">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                                        Proveedor de IA 
                                        <Tooltip>
                                            <TooltipTrigger><Info size={14} className="text-slate-300" /></TooltipTrigger>
                                            <TooltipContent className="bg-slate-800 text-white border-none p-3 rounded-xl shadow-2xl">
                                                <p className="text-xs font-bold">OpenAI es el referente en razonamiento.<br/>Gemini destaca por velocidad y contexto largo.</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </label>
                                    <Select 
                                        value={tenant.llm_provider} 
                                        onValueChange={(val) => setTenant({ ...tenant, llm_provider: val })}
                                    >
                                        <SelectTrigger className="h-14 rounded-2xl border-slate-200 bg-slate-50 font-bold text-slate-700 focus:ring-emerald-500/20">
                                            <SelectValue placeholder="Seleccionar Proveedor" />
                                        </SelectTrigger>
                                        <SelectContent className="rounded-2xl border-slate-100 shadow-2xl">
                                            <SelectItem value="openai" className="font-bold flex items-center gap-2">OpenAI (SOTA)</SelectItem>
                                            <SelectItem value="gemini" className="font-bold">Google Gemini (Next-Gen)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="space-y-3">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                                        Modelo Seleccionado
                                        <Tooltip>
                                            <TooltipTrigger><Info size={14} className="text-slate-300" /></TooltipTrigger>
                                            <TooltipContent className="bg-slate-800 text-white border-none p-3 rounded-xl shadow-2xl">
                                                <p className="text-xs font-bold">Los modelos 'Mini' o 'Flash' son ideales para agendamientos rápidos.<br/>Modelos 'Pro' son mejores para consultas clínicas complejas.</p>
                                            </TooltipContent>
                                        </Tooltip>
                                    </label>
                                    <Select 
                                        value={tenant.llm_model} 
                                        onValueChange={(val) => setTenant({ ...tenant, llm_model: val })}
                                    >
                                        <SelectTrigger className="h-14 rounded-2xl border-slate-200 bg-slate-50 font-bold text-slate-700 focus:ring-emerald-500/20">
                                            <SelectValue placeholder="Seleccionar Modelo" />
                                        </SelectTrigger>
                                        <SelectContent className="rounded-2xl border-slate-100 shadow-2xl">
                                            {tenant.llm_provider === 'openai' ? (
                                                <>
                                                    <SelectItem value="o4-mini" className="font-bold">o4-mini (Reasoning/CoT)</SelectItem>
                                                    <SelectItem value="gpt-5-mini" className="font-bold">GPT-5 Mini (Fast Reasoning)</SelectItem>
                                                    <SelectItem value="gpt-4o-mini" className="font-bold text-slate-400">GPT-4o Mini (Legacy)</SelectItem>
                                                </>
                                            ) : (
                                                <>
                                                    <SelectItem value="gemini-3.1-pro-preview" className="font-bold">Gemini 3.1 Pro (Expert)</SelectItem>
                                                    <SelectItem value="gemini-3.1-flash-lite-preview" className="font-bold">Gemini 3.1 Flash-Lite (Ultrarapid)</SelectItem>
                                                </>
                                            )}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                                        System Prompt (Identidad y Reglas)
                                    </label>
                                    <Badge variant="outline" className={`font-black text-[10px] ${(tenant.system_prompt?.length || 0) > 3500 ? 'text-rose-600 border-rose-200 bg-rose-50' : (tenant.system_prompt?.length || 0) > 3000 ? 'text-amber-600 border-amber-200 bg-amber-50' : 'text-slate-400'}`}>
                                        {tenant.system_prompt?.length || 0} / 4000 caracteres
                                    </Badge>
                                </div>
                                <div className="relative group">
                                    <textarea
                                        rows={12}
                                        value={tenant.system_prompt}
                                        onChange={(e) => setTenant({ ...tenant, system_prompt: e.target.value })}
                                        className="w-full bg-slate-50 border border-slate-200 rounded-[2rem] p-8 text-sm text-slate-700 font-mono focus:outline-none focus:ring-4 focus:ring-emerald-500/5 focus:border-emerald-500 transition-all resize-none shadow-inner leading-relaxed"
                                        placeholder="Define quién es el bot, su tono de voz y las reglas de agendamiento..."
                                    />
                                    <div className="absolute top-4 right-4 text-emerald-500 opacity-20 group-focus-within:opacity-100 transition-opacity">
                                        <Zap size={24} />
                                    </div>
                                </div>
                                <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 flex items-start gap-3">
                                    <Info className="text-amber-500 flex-shrink-0 mt-0.5" size={18} />
                                    <p className="text-xs text-amber-700 font-semibold leading-relaxed">
                                        Recuerda incluir siempre el nombre de la clínica y los horarios de atención. El prompt es la base de la confianza del paciente.
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-100 shadow-2xl overflow-hidden rounded-[2rem]">
                        <CardHeader className="bg-slate-900 text-white p-8 md:p-10 relative overflow-hidden">
                            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
                                <div className="flex items-center gap-5">
                                    <div className="w-16 h-16 bg-blue-500 rounded-2xl flex items-center justify-center shadow-lg transform -rotate-3">
                                        <Calendar size={36} className="text-white" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-3xl font-black tracking-tight">Google Calendar</CardTitle>
                                        <CardDescription className="text-slate-400 font-medium text-lg mt-1">Conecta la agenda clínica (Google Workspace).</CardDescription>
                                    </div>
                                </div>
                            </div>
                        </CardHeader>
                        
                        <CardContent className="p-8 md:p-10 space-y-10 bg-white">
                            <div className="flex items-center justify-between p-6 bg-slate-50 border border-slate-200 rounded-2xl">
                                <div>
                                    <h4 className="text-lg font-bold text-slate-800">Estado de Conexión</h4>
                                    {tenant.google_calendar_status === 'connected' ? (
                                        <div className="flex flex-col mt-2">
                                            <span className="flex items-center gap-2 text-emerald-600 font-bold"><CheckCircle2 size={16} /> Conectado</span>
                                            <span className="text-sm text-slate-500 font-medium mt-1">Cuenta: {tenant.google_calendar_email || 'Oculta'}</span>
                                        </div>
                                    ) : (
                                        <span className="flex items-center gap-2 text-rose-500 font-bold mt-2"><XCircle size={16} /> Desconectado</span>
                                    )}
                                </div>
                                <div>
                                    {tenant.google_calendar_status === 'connected' ? (
                                        <Button 
                                            onClick={async () => {
                                                const res = await fetch(`/api/google/disconnect?tenant_id=${tenant.id}`, { method: 'POST' });
                                                if (res.ok) {
                                                    setTenant({ ...tenant, google_calendar_status: 'disconnected', google_calendar_email: null });
                                                    alert('Google Calendar Desconectado exitosamente');
                                                }
                                            }}
                                            variant="destructive"
                                            className="font-bold px-6 py-6 rounded-xl text-md"
                                        >
                                            Desconectar
                                        </Button>
                                    ) : (
                                        <Button 
                                            onClick={() => {
                                                window.location.href = `/api/google/auth?tenant_id=${tenant.id}`;
                                            }}
                                            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-6 rounded-xl shadow-lg shadow-blue-600/20 text-md"
                                        >
                                            Conectar Google Calendar
                                        </Button>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="bg-emerald-900 rounded-[2rem] p-10 text-white relative overflow-hidden shadow-2xl flex flex-col md:flex-row items-center justify-between gap-8">
                        <div className="relative z-10 max-w-xl text-center md:text-left">
                            <h3 className="text-4xl font-black mb-4">¿Necesitas un modelo a medida?</h3>
                            <p className="text-emerald-200 font-medium text-lg leading-relaxed">
                                Nuestro equipo puede entrenar un modelo específico con tu protocolo médico para una precisión del 99.9%.
                            </p>
                        </div>
                        <Button className="relative z-10 bg-white text-emerald-900 font-black hover:bg-slate-100 px-12 py-8 rounded-2xl text-xl shadow-2xl active:scale-95 transition-all">
                            Solicitar Custom LLM
                        </Button>
                        <div className="absolute -top-10 -right-10 w-64 h-64 bg-white/5 rounded-full blur-3xl"></div>
                        <div className="absolute -bottom-10 -left-10 w-64 h-64 bg-emerald-400/10 rounded-full blur-3xl"></div>
                    </div>
                </div>
            </div>
        </TooltipProvider>
    )
}
