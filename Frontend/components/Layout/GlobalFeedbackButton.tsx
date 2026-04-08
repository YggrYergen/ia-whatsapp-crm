'use client'

import React from 'react'
import { MessageSquarePlus, X, Send, Camera } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { usePathname } from 'next/navigation'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { useCrm } from '@/contexts/CrmContext'

export default function GlobalFeedbackButton() {
    const pathname = usePathname()
    const [isOpen, setIsOpen] = React.useState(false)
    const [feedback, setFeedback] = React.useState("")
    const [isCapturing, setIsCapturing] = React.useState(false)
    const { setToasts } = useCrm()

    const handleSend = async () => {
        setIsCapturing(true)
        try {
            const payload = {
                tenant_id: null,
                patient_phone: 'Feedback Global UI',
                history: [
                    { role: 'user', content: `[Ruta Actual]: ${pathname}` },
                    { role: 'assistant', content: `[User Agent]: ${navigator.userAgent}` }
                ],
                notes: [
                    { id: 'global-1', content: `[Ruta Actual]: ${pathname}`, note: feedback }
                ],
                tester_email: 'tomasgemes@gmail.com'
            }
            
            const response = await fetch('/api/test-feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })

            const result = await response.json()
            if (!response.ok) throw new Error(result.message || "Fallo en el servidor")
            
            setIsOpen(false)
            setFeedback("")
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: 'Feedback global enviado correctamente 🚀' } }])
        } catch (err) {
            setToasts(prev => [...prev, { id: Date.now(), payload: { content: `Error enviando feedback: ${(err as Error).message}` } }])
        } finally {
            setIsCapturing(false)
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <DialogTrigger asChild>
                <button className="fixed bottom-32 left-6 z-[100] w-12 h-12 bg-slate-900 text-white rounded-full flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all group overflow-hidden border-2 border-slate-700/50">
                    <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <MessageSquarePlus size={22} className="relative z-10" />
                </button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px] bg-white/95 backdrop-blur-xl border-slate-200 shadow-2xl">
                <DialogHeader>
                    <DialogTitle className="text-xl font-black tracking-tight text-slate-800 flex items-center gap-2">
                        <MessageSquarePlus className="text-emerald-500" /> FEEDBACK GLOBAL
                    </DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Estás en: <span className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">{pathname}</span></p>
                    <textarea 
                        placeholder="Cuéntanos qué falta, qué falló o qué te gustaría ver aquí..."
                        className="w-full min-h-[120px] bg-white border border-slate-200 focus:ring-emerald-500 rounded-xl p-3 text-sm text-slate-800 outline-none transition-all placeholder:text-slate-400"
                        value={feedback}
                        onChange={e => setFeedback(e.target.value)}
                    />
                    <div className="bg-slate-100 rounded-lg p-3 flex items-center gap-3 border border-slate-200">
                        <div className="w-10 h-10 bg-slate-200 rounded flex items-center justify-center text-slate-500">
                           <Camera size={18} />
                        </div>
                        <p className="text-[10px] text-slate-500 font-medium leading-tight italic">
                            Se adjuntará automáticamente una captura de pantalla de lo que ves actualmente para darnos contexto técnico.
                        </p>
                    </div>
                </div>
                <DialogFooter>
                    <Button 
                        onClick={handleSend} 
                        disabled={!feedback.trim() || isCapturing}
                        className="w-full bg-slate-900 border-none hover:bg-slate-800 text-white font-black uppercase tracking-widest text-[11px] h-11"
                    >
                        {isCapturing ? "Capturando..." : "ENVIAR MI FEEDBACK"} <Send size={14} className="ml-2" />
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}
