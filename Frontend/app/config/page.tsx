'use client'

/**
 * ConfigPanel — Global tenant config page (LLM provider, model, system prompt).
 *
 * ⚠️ TENANT ISOLATION: Resolves the user's tenant via auth.getUser() → tenant_users.
 *    Does NOT use TenantContext (this page is outside the (panel) layout group).
 *
 * ⚠️ OBSERVABILITY: Every failure → console.error + Sentry + Discord.
 *    (Rule 5: three-channel error reporting)
 */

import React, { useState, useEffect } from 'react'
import * as Sentry from '@sentry/nextjs'
import { createClient } from '@/lib/supabase'
import { notifyDiscord } from '@/lib/notifyDiscord'
import { Save, Bot, Info, Sparkles, Zap, ChevronLeft, Calendar, CheckCircle2, XCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import Link from 'next/link'

export default function ConfigPanel() {
    const _where = 'ConfigPanel'
    const supabase = createClient()
    const [tenantId, setTenantId] = useState<string | null>(null)
    const [tenant, setTenant] = useState<any>(null)
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [saveSuccess, setSaveSuccess] = useState(false)

    // Resolve the user's tenant via auth → tenant_users (no TenantContext needed)
    useEffect(() => {
        const resolveTenant = async () => {
            const fn = `${_where}.resolveTenant`
            try {
                const { data: { user } } = await supabase.auth.getUser()
                if (!user) {
                    setLoading(false)
                    return
                }

                // Get user's first tenant
                const { data: tuData, error: tuError } = await supabase
                    .from('tenant_users')
                    .select('tenant_id')
                    .eq('user_id', user.id)
                    .limit(1)
                    .single()

                if (tuError || !tuData) {
                    const errMsg = `[${fn}] No tenant found for user ${user.id} | error=${tuError?.message}`
                    console.error(errMsg)
                    Sentry.captureMessage(errMsg, 'error')
                    notifyDiscord('🔴 Config: No tenant for user', `**User:** \`${user.id}\`\n**Error:** ${tuError?.message}`, 'error')
                    setLoading(false)
                    return
                }

                setTenantId(tuData.tenant_id)

                // Fetch the tenant config
                const { data, error } = await supabase
                    .from('tenants')
                    .select('*')
                    .eq('id', tuData.tenant_id)
                    .single()

                if (error) {
                    const errMsg = `[${fn}] Tenant fetch failed | tenant=${tuData.tenant_id} | error=${error.message}`
                    console.error(errMsg)
                    Sentry.captureMessage(errMsg, 'error')
                    notifyDiscord('🔴 Config Fetch Failed', `**Tenant:** \`${tuData.tenant_id}\`\n**Error:** ${error.message}`, 'error')
                } else if (data) {
                    setTenant(data)
                }
            } catch (err: any) {
                const errMsg = `[${fn}] CRASH resolving tenant | error=${String(err).slice(0, 300)}`
                console.error(errMsg, err)
                Sentry.captureException(err, { extra: { where: fn } })
                notifyDiscord('🔴 Config Resolve CRASH', `**Error:** ${String(err).slice(0, 500)}`, 'error')
            } finally {
                setLoading(false)
            }
        }
        resolveTenant()
    }, [])



    const handleSave = async () => {
        const fn = `${_where}.handleSave`

        if (!tenant || !tenantId) {
            const errMsg = `[${fn}] Save blocked — tenant=${!!tenant}, tenantId=${tenantId}`
            console.error(errMsg)
            Sentry.captureMessage(errMsg, 'warning')
            return
        }

        // BUG-2 fix: Warn via Sentry if system prompt exceeds 4000 characters
        if (tenant.system_prompt && tenant.system_prompt.length > 4000) {
            const warnMsg = `[${fn}] System prompt exceeds 4000 char limit: ${tenant.system_prompt.length} chars | tenant=${tenantId}`
            console.warn(warnMsg)
            Sentry.captureMessage(warnMsg, 'warning')
            notifyDiscord(
                '⚠️ Oversized System Prompt',
                `**Tenant:** \`${tenantId}\`\n**Length:** ${tenant.system_prompt.length} chars\n**Limit:** 4000`,
                'warning'
            )
        }

        // SAFETY: Verify we're updating the correct tenant
        if (tenant.id !== tenantId) {
            const errMsg = `[${fn}] CRITICAL: tenant.id (${tenant.id}) !== tenantId (${tenantId}) — aborting save to prevent cross-tenant overwrite`
            console.error(errMsg)
            Sentry.captureMessage(errMsg, 'error')
            notifyDiscord(
                '🚨 CROSS-TENANT SAVE BLOCKED',
                `**tenant.id:** \`${tenant.id}\`\n**tenantId:** \`${tenantId}\`\n**Action:** Save aborted to prevent data corruption`,
                'error'
            )
            alert('Error de seguridad: el tenant activo no coincide con los datos cargados. Recarga la página.')
            return
        }

        setSaving(true)
        setSaveSuccess(false)
        try {
            const { error } = await supabase
                .from('tenants')
                .update({
                    llm_provider: tenant.llm_provider,
                    llm_model: tenant.llm_model,
                    system_prompt: tenant.system_prompt
                })
                .eq('id', tenantId) // CRITICAL: always scope by current tenant

            if (error) {
                const errMsg = `[${fn}] Save failed | tenant=${tenantId} | error=${error.message}`
                console.error(errMsg)
                Sentry.captureMessage(errMsg, 'error')
                notifyDiscord(
                    '🔴 Config Save Failed',
                    `**Tenant:** \`${tenantId}\`\n**Error:** ${error.message}\n**Provider:** ${tenant.llm_provider}\n**Model:** ${tenant.llm_model}`,
                    'error'
                )
                alert(`Error al guardar: ${error.message}`)
                return
            }

            console.info(`[${fn}] Config saved successfully | tenant=${tenantId} | provider=${tenant.llm_provider} | model=${tenant.llm_model}`)
            Sentry.addBreadcrumb({ category: 'config', message: `Config saved for tenant ${tenantId}`, level: 'info' })
            setSaveSuccess(true)
            setTimeout(() => setSaveSuccess(false), 3000)
        } catch (err: any) {
            const errMsg = `[${fn}] CRASH saving config | tenant=${tenantId} | error=${String(err).slice(0, 300)}`
            console.error(errMsg, err)
            Sentry.captureException(err, { extra: { where: fn, tenant_id: tenantId } })
            notifyDiscord(
                '🔴 Config Save CRASH',
                `**Tenant:** \`${tenantId}\`\n**Error:** ${String(err).slice(0, 500)}\n**Where:** ${fn}`,
                'error'
            )
            alert('Error inesperado al guardar. Revisa tu conexión e intenta de nuevo.')
        } finally {
            setSaving(false)
        }
    }

    if (loading) return (
        <div className="flex items-center justify-center h-screen bg-slate-50">
             <div className="flex flex-col items-center gap-4">
                 <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                 <p className="text-slate-500 font-bold animate-pulse">Cargando configuración...</p>
             </div>
        </div>
    )

    if (!tenantId || !tenant) return (
        <div className="flex items-center justify-center h-screen bg-slate-50">
            <div className="text-center space-y-3">
                <p className="text-slate-500 font-bold">No hay tenant seleccionado</p>
                <Link href="/">
                    <Button variant="outline">Volver al Dashboard</Button>
                </Link>
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
                        <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 px-4 py-1 font-black uppercase tracking-widest text-[10px]">
                            {tenant?.business_name || 'Configuración'}
                        </Badge>
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
                                        <CardDescription className="text-slate-400 font-medium text-lg mt-1">Configura el modelo y comportamiento de la IA para tu negocio.</CardDescription>
                                    </div>
                                </div>
                                <Button 
                                    onClick={handleSave} 
                                    disabled={saving}
                                    className={`font-black px-8 py-6 rounded-2xl shadow-xl text-lg transition-all active:scale-95 ${
                                        saveSuccess 
                                            ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-600/20' 
                                            : 'bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/20'
                                    } text-white`}
                                >
                                    {saving ? 'Guardando...' : saveSuccess ? <><CheckCircle2 size={22} className="mr-2" /> Guardado ✓</> : <><Save size={22} className="mr-2" /> Guardar Cambios</>}
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
                                                <p className="text-xs font-bold">Los modelos 'Mini' o 'Flash' son ideales para tareas rápidas.<br/>Modelos 'Pro' son mejores para consultas complejas.</p>
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
                                                    <SelectItem value="gpt-5.4-mini" className="font-bold">GPT-5.4 Mini (Recomendado)</SelectItem>
                                                    <SelectItem value="gpt-5.4-nano" className="font-bold">GPT-5.4 Nano (Económico)</SelectItem>
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
                                        Recuerda incluir siempre el nombre de tu negocio y los horarios de atención. El prompt es la base de la confianza del cliente.
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
                                        <CardTitle className="text-3xl font-black tracking-tight">Agenda y Reservas</CardTitle>
                                        <CardDescription className="text-slate-400 font-medium text-lg mt-1">Configuración de recursos, servicios y horarios.</CardDescription>
                                    </div>
                                </div>
                                <Badge variant="outline" className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30 px-4 py-1 font-black uppercase tracking-widest text-[10px]">
                                    <CheckCircle2 size={12} className="mr-1" /> Activo
                                </Badge>
                            </div>
                        </CardHeader>

                        <CardContent className="p-8 md:p-10 space-y-6 bg-white">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <Link href="/servicios" className="group p-6 bg-violet-50 border border-violet-100 rounded-2xl hover:shadow-lg hover:border-violet-300 transition-all">
                                    <div className="w-10 h-10 bg-violet-500 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                        <Sparkles size={20} className="text-white" />
                                    </div>
                                    <h4 className="font-bold text-slate-800 text-lg">Servicios</h4>
                                    <p className="text-sm text-slate-500 mt-1">Precios, duraciones y catálogo visible al asistente.</p>
                                </Link>

                                <Link href="/recursos" className="group p-6 bg-blue-50 border border-blue-100 rounded-2xl hover:shadow-lg hover:border-blue-300 transition-all">
                                    <div className="w-10 h-10 bg-blue-500 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                        <Calendar size={20} className="text-white" />
                                    </div>
                                    <h4 className="font-bold text-slate-800 text-lg">Recursos</h4>
                                    <p className="text-sm text-slate-500 mt-1">Equipos, técnicos o salas para round-robin.</p>
                                </Link>

                                <Link href="/agenda" className="group p-6 bg-emerald-50 border border-emerald-100 rounded-2xl hover:shadow-lg hover:border-emerald-300 transition-all">
                                    <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                        <Zap size={20} className="text-white" />
                                    </div>
                                    <h4 className="font-bold text-slate-800 text-lg">Agenda</h4>
                                    <p className="text-sm text-slate-500 mt-1">Vista calendario con todas las citas del día.</p>
                                </Link>
                            </div>
                            
                            <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4 flex items-start gap-3">
                                <Info className="text-blue-500 flex-shrink-0 mt-0.5" size={18} />
                                <p className="text-xs text-blue-700 font-semibold leading-relaxed">
                                    Tu agenda usa el sistema nativo con round-robin automático. Las citas se distribuyen entre tus recursos activos, evitando doble-agendamiento con protección a nivel de base de datos.
                                </p>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="bg-emerald-900 rounded-[2rem] p-10 text-white relative overflow-hidden shadow-2xl flex flex-col md:flex-row items-center justify-between gap-8">
                        <div className="relative z-10 max-w-xl text-center md:text-left">
                            <h3 className="text-4xl font-black mb-4">¿Necesitas un modelo a medida?</h3>
                            <p className="text-emerald-200 font-medium text-lg leading-relaxed">
                                Nuestro equipo puede entrenar un modelo específico con tu flujo de negocio para una precisión del 99.9%.
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
