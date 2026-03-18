'use client'

import React, { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase'
import { Save, Bot } from 'lucide-react'

export default function ConfigPanel() {
    const supabase = createClient()
    const [tenant, setTenant] = useState<any>(null)
    const [loading, setLoading] = useState(true)

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
        const { error } = await supabase.from('tenants').update({
            llm_provider: tenant.llm_provider,
            llm_model: tenant.llm_model,
            system_prompt: tenant.system_prompt
        }).eq('id', tenant.id)

        if (!error) alert('Configuración guardada exitosamente')
    }

    if (loading) return <div>Cargando...</div>

    return (
        <div className="p-8 max-w-4xl mx-auto bg-white rounded-xl shadow-lg mt-10">
            <div className="flex items-center gap-3 mb-8 border-b pb-4">
                <Bot size={32} className="text-blue-600" />
                <h1 className="text-2xl font-bold">Configuración del Asistente (Tenant)</h1>
            </div>

            <div className="space-y-6">
                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Proveedor de IA</label>
                        <select
                            value={tenant.llm_provider}
                            onChange={(e) => setTenant({ ...tenant, llm_provider: e.target.value })}
                            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            <option value="openai">OpenAI (GPT-5.4)</option>
                            <option value="gemini">Google Gemini (3.1)</option>
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Modelo Seleccionado</label>
                        <select
                            value={tenant.llm_model}
                            onChange={(e) => setTenant({ ...tenant, llm_model: e.target.value })}
                            className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                            {tenant.llm_provider === 'openai' ? (
                                <>
                                    <option value="o4-mini">o4-mini (Reasoning/CoT)</option>
                                    <option value="gpt-5-mini">GPT-5 Mini (Current/Reasoning)</option>
                                    <option value="gpt-4o-mini">GPT-4o Mini (Legacy)</option>
                                </>
                            ) : (
                                <>
                                    <option value="gemini-3.1-pro-preview">Gemini 3.1 Pro (Smart)</option>
                                    <option value="gemini-3.1-flash-lite-preview">Gemini 3.1 Flash-Lite (Fast)</option>
                                </>
                            )}
                        </select>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">System Prompt (Instrucciones)</label>
                    <textarea
                        rows={8}
                        value={tenant.system_prompt}
                        onChange={(e) => setTenant({ ...tenant, system_prompt: e.target.value })}
                        className="w-full p-4 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm bg-gray-50"
                        placeholder="Introduce las instrucciones del bot..."
                    />
                </div>

                <div className="pt-4 flex justify-end">
                    <button
                        onClick={handleSave}
                        className="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-700 transition"
                    >
                        <Save size={20} />
                        Guardar Configuración
                    </button>
                </div>
            </div>
        </div>
    )
}
