'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Clock, User, RefreshCw, CalendarCheck, CalendarDays, Plus, Loader2 } from 'lucide-react'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { useCrm } from '@/contexts/CrmContext'
import * as Sentry from '@sentry/nextjs'

type ViewMode = 'day' | 'week' | 'month'

interface CalendarEvent {
    id: string;
    summary: string;
    description: string;
    start: string;
    end: string;
    box: string;
    status: string;
}

export default function AgendaView() {
    const { setToasts } = useCrm()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [viewMode, setViewMode] = useState<ViewMode>('day')
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [loading, setLoading] = useState(false)
    
    // Booking Modal State
    const [isBookingOpen, setIsBookingOpen] = useState(false)
    const [bookingTime, setBookingTime] = useState("")
    const [bookingDate, setBookingDate] = useState("")
    const [patientName, setPatientName] = useState("")
    const [patientPhone, setPatientPhone] = useState("")
    const [isSubmitting, setIsSubmitting] = useState(false)

    const fetchEvents = async () => {
        setLoading(true)
        try {
            // Rango según la vista (simplificado a mes corrido para cubrir todo)
            const yr = currentDate.getFullYear()
            const mo = currentDate.getMonth()
            const startIso = new Date(yr, mo, 1).toISOString()
            const endIso = new Date(yr, mo + 1, 0, 23, 59, 59).toISOString()
            
            const res = await fetch(`/api/calendar/events?start_iso=${startIso}&end_iso=${endIso}`)
            const data = await res.json()
            if (data.status === 'success') {
                setEvents(data.events)
            } else {
                setToasts(prev => [...prev, { id: Date.now(), payload: { content: "Error al cargar la agenda" } }])
            }
        } catch (err) {
            console.error("Fetch calendar err", err)
            Sentry.captureException(err as Error)
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: "Error de conexión cargando agenda" } }])
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchEvents()
    }, [currentDate.getMonth(), currentDate.getFullYear()])

    const handlePrev = () => {
        const d = new Date(currentDate)
        if (viewMode === 'day') d.setDate(d.getDate() - 1)
        if (viewMode === 'week') d.setDate(d.getDate() - 7)
        if (viewMode === 'month') d.setMonth(d.getMonth() - 1)
        setCurrentDate(d)
    }

    const handleNext = () => {
        const d = new Date(currentDate)
        if (viewMode === 'day') d.setDate(d.getDate() + 1)
        if (viewMode === 'week') d.setDate(d.getDate() + 7)
        if (viewMode === 'month') d.setMonth(d.getMonth() + 1)
        setCurrentDate(d)
    }

    const formatHeaderDate = () => {
        if (viewMode === 'day') {
            return currentDate.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
        }
        if (viewMode === 'month') {
            return currentDate.toLocaleDateString('es-ES', { month: 'long', year: 'numeric' })
        }
        // week
        const start = new Date(currentDate)
        start.setDate(start.getDate() - start.getDay() + 1)
        const end = new Date(start)
        end.setDate(end.getDate() + 6)
        return `${start.getDate()} ${start.toLocaleDateString('es-ES',{month:'short'})} - ${end.getDate()} ${end.toLocaleDateString('es-ES',{month:'short', year:'numeric'})}`
    }

    const handleSlotClick = (dateStr: string, timeStr: string) => {
        setBookingDate(dateStr)
        setBookingTime(timeStr)
        setIsBookingOpen(true)
    }

    const handleBook = async () => {
        if (!patientName.trim() || !patientPhone.trim()) {
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: "Llene todos los campos" } }])
            return
        }
        setIsSubmitting(true)
        try {
            const payload = {
                date_str: bookingDate,
                time_str: bookingTime,
                duration: 30,
                patient_name: patientName,
                phone: patientPhone
            }
            const res = await fetch(`/api/calendar/book`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            const data = await res.json()
            if (data.status === 'success') {
                setToasts(prev => [...prev, { id: Date.now(), payload: { content: data.message } }])
                setPatientName("")
                setPatientPhone("")
                setIsBookingOpen(false)
                fetchEvents()
            } else {
                throw new Error(data.message)
            }
        } catch (err: any) {
            Sentry.captureException(err)
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: err.message || "Error al agendar" } }])
        } finally {
            setIsSubmitting(false)
        }
    }

    const hours = Array.from({ length: 11 }, (_, i) => `${(i + 9).toString().padStart(2, '0')}:00`)
    
    // Obtener stats
    const todaysEvents = events.filter(e => new Date(e.start).toDateString() === new Date().toDateString())
    const box1Count = todaysEvents.filter(e => e.box === 'Box 1').length
    const box2Count = todaysEvents.filter(e => e.box === 'Box 2').length
    const totalCap = 11 // 9 a 19 son 11 slots
    const box1Pct = Math.round((box1Count / totalCap) * 100) || 0
    const box2Pct = Math.round((box2Count / totalCap) * 100) || 0

    return (
        <div className="flex flex-col h-full bg-slate-50/50 p-4 md:p-8 space-y-6 overflow-y-auto">
            {/* Top Stats / Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-black text-slate-900 tracking-tight flex items-center gap-3">
                        <CalendarDays className="text-indigo-600" size={32} />
                        Agenda Médica
                    </h1>
                    <p className="text-slate-500 font-medium">Gestión y control de citas en tiempo real.</p>
                </div>
                
                <div className="flex items-center gap-2">
                    <Button variant="outline" className="bg-white border-slate-200 shadow-sm gap-2" onClick={fetchEvents}>
                        <RefreshCw size={16} className={loading ? "animate-spin" : ""} /> Sincronizar Google
                    </Button>
                    <Button onClick={() => handleSlotClick(new Date().toISOString().split('T')[0], "09:00")} className="bg-indigo-600 hover:bg-indigo-700 shadow-lg shadow-indigo-200 gap-2">
                        <CalendarCheck size={18} /> Nueva Cita
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Sidebar Stats */}
                <div className="lg:col-span-1 space-y-4">
                    <Card className="border-none shadow-sm bg-indigo-900 text-white overflow-hidden relative">
                        <div className="absolute top-0 right-0 p-4 opacity-10">
                            <CalendarIcon size={80} />
                        </div>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-bold opacity-80 uppercase tracking-wider">Hoy</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="text-4xl font-black mb-1">{todaysEvents.length}</div>
                            <p className="text-xs text-indigo-200">Citas programadas para hoy</p>
                        </CardContent>
                    </Card>

                    <Card className="border-none shadow-sm">
                        <CardHeader className="pb-4">
                            <CardTitle className="text-sm font-bold text-slate-500 uppercase tracking-wider">Ocupación Hoy</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-bold">
                                    <span>Box 1</span>
                                    <span className="text-indigo-600">{box1Pct}%</span>
                                </div>
                                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-indigo-500 transition-all" style={{ width: `${box1Pct}%` }} />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <div className="flex justify-between text-xs font-bold">
                                    <span>Box 2</span>
                                    <span className="text-emerald-600">{box2Pct}%</span>
                                </div>
                                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                                    <div className="h-full bg-emerald-500 transition-all" style={{ width: `${box2Pct}%` }} />
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
                        <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Próximos en Llegar (Hoy)</h4>
                        <div className="space-y-4">
                            {todaysEvents.slice(0, 4).map(app => (
                                <div key={app.id} className="flex items-center gap-3 group cursor-pointer hover:bg-slate-50 p-2 rounded-xl transition-all">
                                    <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 group-hover:bg-indigo-100 group-hover:text-indigo-600 transition-colors">
                                        <User size={18} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-bold text-slate-800 truncate">{app.summary.split('-')[1]?.trim() || app.summary}</p>
                                        <div className="flex items-center gap-2 text-[10px] text-slate-400 font-bold">
                                            <Clock size={10} /> {new Date(app.start).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})} • {app.box}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {todaysEvents.length === 0 && <p className="text-xs text-slate-400">Sin citas pendientes hoy.</p>}
                        </div>
                    </div>
                </div>

                {/* Main Calendar Area */}
                <Card className="lg:col-span-3 border-none shadow-xl bg-white overflow-hidden rounded-[2rem] flex flex-col">
                    <CardHeader className="flex flex-row items-center justify-between border-b border-slate-50 pb-6 w-full shrink-0">
                        <div className="flex items-center gap-4">
                            <div className="flex bg-slate-100 p-1 rounded-xl">
                                <Button onClick={handlePrev} variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-white hover:shadow-sm"><ChevronLeft size={18} /></Button>
                                <Button onClick={handleNext} variant="ghost" size="icon" className="h-8 w-8 rounded-lg hover:bg-white hover:shadow-sm"><ChevronRight size={18} /></Button>
                            </div>
                            <h2 className="text-lg md:text-xl font-black text-slate-800 tracking-tight capitalize">{formatHeaderDate()}</h2>
                        </div>
                        <div className="flex gap-1 bg-slate-100 p-1 rounded-xl shrink-0 overflow-x-auto">
                            <Button onClick={() => setViewMode('day')} variant="ghost" className={`h-8 px-4 py-0 text-xs font-bold rounded-lg ${viewMode==='day'?'bg-white shadow-sm text-indigo-600':'text-slate-500'}`}>Día</Button>
                            <Button onClick={() => setViewMode('week')} variant="ghost" className={`h-8 px-4 py-0 text-xs font-bold rounded-lg ${viewMode==='week'?'bg-white shadow-sm text-indigo-600':'text-slate-500'}`}>Semana</Button>
                            <Button onClick={() => setViewMode('month')} variant="ghost" className={`h-8 px-4 py-0 text-xs font-bold rounded-lg ${viewMode==='month'?'bg-white shadow-sm text-indigo-600':'text-slate-500'}`}>Mes</Button>
                        </div>
                    </CardHeader>
                    
                    <CardContent className="p-0 flex-1 overflow-y-auto custom-scrollbar relative">
                        {loading && (
                            <div className="absolute inset-0 bg-white/50 backdrop-blur-sm z-50 flex items-center justify-center">
                                <Loader2 className="animate-spin text-indigo-600" size={32} />
                            </div>
                        )}
                        
                        {/* Day View */}
                        {viewMode === 'day' && (
                            <div className="flex flex-col min-w-[600px]">
                                <div className="flex border-b border-slate-100">
                                    <div className="w-20 border-r border-slate-100"></div>
                                    <div className="flex-1 grid grid-cols-2 text-center text-xs font-black uppercase text-slate-400 py-2">
                                        <div className="border-r border-slate-100">Box 1</div>
                                        <div>Box 2</div>
                                    </div>
                                </div>
                                {hours.map((hour, idx) => {
                                    const hourDate = new Date(currentDate)
                                    const [h, m] = hour.split(':')
                                    hourDate.setHours(parseInt(h), parseInt(m), 0, 0)
                                    
                                    const box1App = events.find(e => {
                                        const d = new Date(e.start)
                                        return d.toDateString() === hourDate.toDateString() && d.getHours() === hourDate.getHours() && e.box === 'Box 1'
                                    })
                                    const box2App = events.find(e => {
                                        const d = new Date(e.start)
                                        return d.toDateString() === hourDate.toDateString() && d.getHours() === hourDate.getHours() && e.box === 'Box 2'
                                    })

                                    return (
                                        <div key={idx} className="flex border-b border-slate-50 min-h-[80px] group">
                                            <div className="w-20 flex-shrink-0 flex items-center justify-center border-r border-slate-50 bg-slate-50/30 text-[11px] font-black text-slate-400 uppercase">
                                                {hour}
                                            </div>
                                            <div className="flex-1 grid grid-cols-2">
                                                {/* BOX 1 */}
                                                <div className="border-r border-slate-50 p-1 relative h-full">
                                                    {box1App ? (
                                                        <div className="h-full rounded-xl p-3 bg-indigo-50 border-l-4 border-indigo-500 shadow-sm transition-all hover:scale-105 cursor-pointer">
                                                            <p className="text-[10px] font-black uppercase tracking-tighter text-indigo-600 mb-1">{box1App.summary}</p>
                                                        </div>
                                                    ) : (
                                                        <div onClick={() => handleSlotClick(currentDate.toISOString().split('T')[0], hour)} className="h-full w-full opacity-0 group-hover:opacity-100 flex items-center justify-center border border-dashed border-indigo-200 rounded-xl transition-all hover:bg-indigo-50/50 cursor-pointer">
                                                            <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest">+ Agendar</span>
                                                        </div>
                                                    )}
                                                </div>
                                                {/* BOX 2 */}
                                                <div className="p-1 relative h-full">
                                                    {box2App ? (
                                                        <div className="h-full rounded-xl p-3 bg-emerald-50 border-l-4 border-emerald-500 shadow-sm transition-all hover:scale-105 cursor-pointer">
                                                            <p className="text-[10px] font-black uppercase tracking-tighter text-emerald-600 mb-1">{box2App.summary}</p>
                                                        </div>
                                                    ) : (
                                                        <div onClick={() => handleSlotClick(currentDate.toISOString().split('T')[0], hour)} className="h-full w-full opacity-0 group-hover:opacity-100 flex items-center justify-center border border-dashed border-emerald-200 rounded-xl transition-all hover:bg-emerald-50/50 cursor-pointer">
                                                            <span className="text-[10px] font-black text-emerald-400 uppercase tracking-widest">+ Agendar</span>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        )}

                        {/* Week View */}
                        {viewMode === 'week' && (
                            <div className="flex flex-col min-w-[800px]">
                                <div className="flex border-b border-slate-100">
                                    <div className="w-16 border-r border-slate-100"></div>
                                    <div className="flex-1 grid grid-cols-7 text-center">
                                        {[...Array(7)].map((_, i) => {
                                            const d = new Date(currentDate)
                                            d.setDate(d.getDate() - d.getDay() + 1 + i)
                                            return (
                                                <div key={i} className="py-2 border-r border-slate-100">
                                                    <div className="text-[10px] font-bold text-slate-400 uppercase">{d.toLocaleDateString('es-ES', {weekday: 'short'})}</div>
                                                    <div className="text-lg font-black text-slate-800">{d.getDate()}</div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                                {hours.map((hour, idx) => (
                                    <div key={idx} className="flex border-b border-slate-50 min-h-[60px] group text-[10px]">
                                        <div className="w-16 flex-shrink-0 flex items-center justify-center border-r border-slate-50 bg-slate-50/30 font-black text-slate-400">
                                            {hour}
                                        </div>
                                        <div className="flex-1 grid grid-cols-7">
                                            {[...Array(7)].map((_, i) => {
                                                const d = new Date(currentDate)
                                                d.setDate(d.getDate() - d.getDay() + 1 + i)
                                                const [h, m] = hour.split(':')
                                                d.setHours(parseInt(h), parseInt(m), 0, 0)
                                                
                                                const slotEvents = events.filter(e => {
                                                    const ed = new Date(e.start)
                                                    return ed.toDateString() === d.toDateString() && ed.getHours() === d.getHours()
                                                })

                                                const isFull = slotEvents.length >= 2

                                                return (
                                                    <div key={i} className="border-r border-slate-50 p-0.5 relative" onClick={() => !isFull && handleSlotClick(d.toISOString().split('T')[0], hour)}>
                                                        {slotEvents.map((se, seIdx) => (
                                                            <div key={seIdx} className={`rounded p-1 text-[8px] font-bold truncate mb-0.5 text-white ${se.box==='Box 1'?'bg-indigo-500':'bg-emerald-500'}`}>
                                                                {se.summary.split('-')[1]?.trim() || se.summary}
                                                            </div>
                                                        ))}
                                                        {!isFull && (
                                                            <div className="absolute inset-0 m-1 opacity-0 group-hover:opacity-100 hover:bg-slate-100/50 rounded flex items-center justify-center cursor-pointer transition-colors border border-dashed border-slate-300">
                                                                <Plus className="text-slate-400" size={14} />
                                                            </div>
                                                        )}
                                                    </div>
                                                )
                                            })}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Month View */}
                        {viewMode === 'month' && (
                            <div className="h-full flex flex-col min-w-[600px]">
                                <div className="grid grid-cols-7 text-center border-b border-slate-100 shrink-0">
                                    {['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'].map(d => (
                                        <div key={d} className="py-2 text-[10px] font-black tracking-widest uppercase text-slate-400">{d}</div>
                                    ))}
                                </div>
                                <div className="flex-1 grid grid-cols-7 grid-rows-5 h-full">
                                    {[...Array(35)].map((_, i) => {
                                        const d = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
                                        d.setDate(d.getDate() - (d.getDay() || 7) + 1 + i)
                                        const isCurrentMonth = d.getMonth() === currentDate.getMonth()
                                        
                                        const dayEvents = events.filter(e => new Date(e.start).toDateString() === d.toDateString())

                                        return (
                                            <div key={i} className={`border-r border-b border-slate-50 p-1 flex flex-col relative transition-colors ${!isCurrentMonth ? 'bg-slate-50/50 opacity-50' : 'hover:bg-slate-50'}`} onClick={() => {
                                                setCurrentDate(d)
                                                setViewMode('day')
                                            }}>
                                                <div className="text-right">
                                                    <span className={`text-xs font-bold ${d.toDateString() === new Date().toDateString() ? 'bg-indigo-600 text-white rounded-full w-5 h-5 inline-flex items-center justify-center' : 'text-slate-500'}`}>
                                                        {d.getDate()}
                                                    </span>
                                                </div>
                                                <div className="flex-1 overflow-y-auto mt-1 space-y-0.5 custom-scrollbar">
                                                    {dayEvents.map((se, seIdx) => (
                                                        <div key={seIdx} className={`rounded-[3px] p-0.5 px-1 truncate text-[8px] font-bold text-white ${se.box==='Box 1'?'bg-indigo-500':'bg-emerald-500'}`}>
                                                            {se.summary}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Modal Booking */}
            <Dialog open={isBookingOpen} onOpenChange={setIsBookingOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Agendar Nueva Cita</DialogTitle>
                        <DialogDescription>
                            Para el {bookingDate} a las {bookingTime}. El sistema revisará y asignará el Box correspondiente de forma automática según disponibilidad.
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                        <div className="grid gap-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Nombre Paciente</label>
                            <Input placeholder="Ej. Ana Soto" value={patientName} onChange={e => setPatientName(e.target.value)} />
                        </div>
                        <div className="grid gap-2">
                            <label className="text-xs font-bold text-slate-500 uppercase">Teléfono / WhatsApp</label>
                            <Input placeholder="+569..." value={patientPhone} onChange={e => setPatientPhone(e.target.value)} />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setIsBookingOpen(false)}>Cancelar</Button>
                        <Button onClick={handleBook} disabled={isSubmitting} className="bg-indigo-600 hover:bg-indigo-700 text-white">
                            {isSubmitting ? <Loader2 className="animate-spin" /> : "Confirmar Reserva"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

        </div>
    )
}
