'use client'

import React, { useState, useEffect } from 'react'
import { User, Phone, Mail, Calendar, MapPin, Tag, Clock, Save, FileText, X, ShieldAlert, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useCrm } from '@/contexts/CrmContext'
import { createClient } from '@/lib/supabase'

const supabase = createClient()

export default function ClientProfilePanel() {
    const { 
        selectedContact, setSelectedContact, contacts, setContacts,
        showDesktopInfo, setShowDesktopInfo, mobileView, setMobileView,
        dashboardRole 
    } = useCrm()
    
    const [notes, setNotes] = useState('')
    const [isSaving, setIsSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

    useEffect(() => {
        if (selectedContact) {
            setNotes(selectedContact.notes || '')
            setSaveStatus('idle')
        }
    }, [selectedContact])

    // Auto-save logic with debounce
    useEffect(() => {
        if (!selectedContact) return
        if (notes === (selectedContact.notes || '')) return

        setSaveStatus('saving')
        const timer = setTimeout(async () => {
            const { error } = await supabase
                .from('contacts')
                .update({ notes })
                .eq('id', selectedContact.id)
            
            if (!error) {
                setSaveStatus('saved')
                setSelectedContact({ ...selectedContact, notes })
                setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, notes } : c))
                setTimeout(() => setSaveStatus('idle'), 2000)
            }
        }, 1500)

        return () => clearTimeout(timer)
    }, [notes])

    // Auto-save logic with debounce
    useEffect(() => {
        if (!selectedContact) return
        if (notes === (selectedContact.notes || '')) return

        setSaveStatus('saving')
        const timer = setTimeout(async () => {
            const { error } = await supabase
                .from('contacts')
                .update({ notes })
                .eq('id', selectedContact.id)
            
            if (!error) {
                setSaveStatus('saved')
                setSelectedContact({ ...selectedContact, notes })
                setContacts(contacts.map(c => c.id === selectedContact.id ? { ...c, notes } : c))
                setTimeout(() => setSaveStatus('idle'), 2000)
            }
        }, 1500)

        return () => clearTimeout(timer)
    }, [notes])

    const handleRoleChange = async (newRole: 'cliente' | 'staff' | 'admin') => {
        if (!selectedContact) return
        const { error } = await supabase.from('contacts').update({ role: newRole }).eq('id', selectedContact.id)
        if (!error) {
            const updated = { ...selectedContact, role: newRole }
            setSelectedContact(updated)
            setContacts(contacts.map(c => c.id === selectedContact.id ? updated : c))
        }
    }

    if (!selectedContact) return null;

    const isVisible = showDesktopInfo || mobileView === 'info'
    const isTestContact = selectedContact.phone_number === '56912345678'

    return (
        <div className={`
            bg-white border-l border-slate-200 flex-shrink-0 transition-all duration-300 overflow-y-auto custom-scrollbar
            ${isVisible ? 'w-full fixed inset-0 z-[100] md:static md:w-[320px] lg:w-[380px]' : 'w-0 overflow-hidden opacity-0 p-0 border-none'}
        `}>
            {/* Header Fixed close for Mobile (Crucial Fix) */}
            <div className="flex items-center justify-between p-4 border-b border-slate-100 bg-white/80 backdrop-blur-md sticky top-0 z-[101]">
                <h3 className="font-black text-slate-800 tracking-tight">INFORMACIÓN DEL LEAD</h3>
                <button 
                    onClick={() => { 
                        setMobileView('chat'); 
                        setShowDesktopInfo(false); 
                    }} 
                    className="p-3 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-full transition-colors"
                    aria-label="Cerrar panel"
                >
                    <X size={24} />
                </button>
            </div>

            <div className="p-5 md:p-6 space-y-6">
                
                {/* Simulation Control (Only for Test Contact & Admin Dashboard) */}
                {isTestContact && dashboardRole === 'admin' && (
                    <div className="bg-indigo-50 border-2 border-indigo-100 rounded-2xl p-4 shadow-sm">
                        <div className="flex items-center gap-2 mb-3">
                            <ShieldAlert size={18} className="text-indigo-600" />
                            <h4 className="text-xs font-black uppercase tracking-widest text-indigo-700">Controles de Simulación</h4>
                        </div>
                        <div className="space-y-4">
                            <div className="grid grid-cols-1 gap-2">
                                <label className="text-[10px] font-bold text-indigo-400 uppercase block ml-1">Simular Rol del Paciente:</label>
                                <div className="flex flex-col gap-1.5">
                                    {[
                                        { id: 'cliente', label: '👤 Usuario / Paciente' },
                                        { id: 'staff', label: '👔 Staff Clínica' },
                                        { id: 'admin', label: '🔑 Administrador' }
                                    ].map((r) => (
                                        <button
                                            key={r.id}
                                            onClick={() => handleRoleChange(r.id as any)}
                                            className={`
                                                flex items-center px-4 py-2 rounded-xl text-xs font-bold transition-all border-2
                                                ${selectedContact.role === r.id 
                                                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-md' 
                                                    : 'bg-white text-indigo-400 border-indigo-50 hover:border-indigo-100 hover:text-indigo-600'
                                                }
                                            `}
                                        >
                                            {r.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                            <p className="text-[10px] text-indigo-400 font-medium italic leading-relaxed">
                                *Esto define el comportamiento de la IA y el acceso a herramientas.
                            </p>
                        </div>
                    </div>
                )}

                {/* Profile Summary */}
                <div className="flex flex-col items-center text-center pb-6 border-b border-slate-100">
                    <div className="w-24 h-24 rounded-full bg-emerald-50 border-4 border-white shadow-xl flex items-center justify-center mb-4 relative group">
                        <User size={48} className="text-emerald-500" />
                        <div className="absolute bottom-1 right-1 w-6 h-6 bg-emerald-500 rounded-full border-2 border-white flex items-center justify-center">
                            <Badge className="p-0 bg-transparent hover:bg-transparent"><div className="w-2 h-2 bg-white rounded-full"></div></Badge>
                        </div>
                    </div>
                    <h3 className="text-xl font-bold text-slate-800 tracking-tight">{selectedContact.name || 'Sin Nombre'}</h3>
                    <div className="mt-2 flex flex-wrap justify-center gap-2">
                        <Badge variant="outline" className={`capitalize font-bold text-[10px] border-emerald-200
                            ${selectedContact.role === 'admin' ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-50 text-emerald-700'}
                        `}>
                            {selectedContact.role === 'admin' ? 'Clínica Staff' : 'Paciente / Lead'}
                        </Badge>
                        <Badge variant="outline" className="bg-slate-50 text-slate-500 border-slate-200 font-bold text-[10px] uppercase">{selectedContact.status || 'lead'}</Badge>
                    </div>
                </div>

                {/* Details Section */}
                <div className="space-y-4">
                    <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400 mb-2">Información de Contacto</h4>
                    <div className="space-y-3">
                        <div className="flex items-center gap-3 text-sm text-slate-600 font-medium">
                            <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400"><Phone size={16} /></div>
                            <span>{selectedContact.phone_number}</span>
                        </div>
                        <div className="flex items-center gap-3 text-sm text-slate-600 font-medium opacity-60">
                            <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center text-slate-400"><Mail size={16} /></div>
                            <span>No registrado</span>
                        </div>
                    </div>
                </div>

                {/* CRM Notes Section */}
                <Card className="border-slate-100 shadow-sm bg-slate-50/50">
                    <CardHeader className="p-4 pb-2">
                        <div className="flex justify-between items-center">
                            <CardTitle className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                                <FileText size={14} /> Notas Internas
                            </CardTitle>
                            {saveStatus === 'saving' && <span className="text-[10px] text-amber-600 font-bold animate-pulse">Guardando...</span>}
                            {saveStatus === 'saved' && <span className="text-[10px] text-emerald-600 font-bold">Guardado ✓</span>}
                        </div>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <textarea 
                            className="w-full h-32 bg-white border-slate-200 rounded-xl p-3 text-sm font-medium outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder:text-slate-300 resize-none text-slate-700"
                            placeholder="Escribe detalles importantes para la IA..."
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                        />
                    </CardContent>
                </Card>

                {/* Automation Status */}
                <div className="bg-indigo-900 rounded-2xl p-5 text-white relative overflow-hidden shadow-lg">
                    <div className="relative z-10">
                        <div className="flex items-center gap-2 mb-2">
                            <Clock size={16} className="text-indigo-300" />
                            <span className="text-[10px] font-black uppercase tracking-widest text-indigo-200">Próxima Acción IA</span>
                        </div>
                        <p className="text-sm font-bold leading-relaxed mb-3">Seguimiento de agendamiento en 24 horas si no concreta.</p>
                        <Select onValueChange={() => {}}>
                            <SelectTrigger className="w-full bg-white/10 border-white/20 text-white font-bold h-9">
                                <SelectValue placeholder="Modificar Prioridad" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="high">Alta Prioridad</SelectItem>
                                <SelectItem value="medium">Normal</SelectItem>
                                <SelectItem value="low">Baja Prioridad</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="absolute top-0 right-0 p-4 opacity-10">
                        <Calendar size={80} />
                    </div>
                </div>
            </div>
        </div>
    )
}
