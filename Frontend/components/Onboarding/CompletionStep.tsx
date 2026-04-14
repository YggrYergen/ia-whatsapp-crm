'use client'

/**
 * CompletionStep — Step 3: Celebration screen after onboarding is complete.
 * Shows a success animation, summary, and "Go to Dashboard" button.
 * CORRECTION NEEDDED: Here the button should take user directly to sandbox chat, not to dashboard.
 */

import React, { useEffect, useState } from 'react'
import { CheckCircle, ArrowRight, Rocket, PartyPopper } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface CompletionStepProps {
  tenantName: string
  onContinue: () => void
}

export default function CompletionStep({ tenantName, onContinue }: CompletionStepProps) {
  const router = useRouter()
  const [showContent, setShowContent] = useState(false)

  // Staggered reveal
  useEffect(() => {
    const timer = setTimeout(() => setShowContent(true), 300)
    return () => clearTimeout(timer)
  }, [])

  const handleContinue = () => {
    onContinue()
    router.push('/chats')
  }

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950 flex items-center justify-center animate-onboarding-in overflow-hidden">
      {/* Confetti particles */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute animate-confetti"
            style={{
              left: `${10 + Math.random() * 80}%`,
              top: `${60 + Math.random() * 30}%`,
              animationDelay: `${Math.random() * 1.5}s`,
              animationDuration: `${1.5 + Math.random() * 1.5}s`,
            }}
          >
            <div
              className="w-2 h-2 rounded-sm"
              style={{
                backgroundColor: ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899'][
                  Math.floor(Math.random() * 6)
                ],
              }}
            />
          </div>
        ))}
      </div>

      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-500/8 rounded-full blur-[120px]" />

      <div className={`
        relative z-10 max-w-lg w-full mx-4 text-center space-y-8
        transition-all duration-700 ${showContent ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
      `}>
        {/* Success icon */}
        <div className="flex justify-center">
          <div className="relative">
            <div className="w-24 h-24 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-3xl flex items-center justify-center shadow-2xl shadow-emerald-500/30 rotate-3">
              <CheckCircle className="w-12 h-12 text-white" />
            </div>
            <div className="absolute -top-2 -right-2">
              <PartyPopper className="w-8 h-8 text-amber-400" />
            </div>
          </div>
        </div>

        {/* Title */}
        <div className="space-y-3">
          <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            ¡Todo listo! 🎉
          </h1>
          <p className="text-lg text-slate-400 max-w-md mx-auto leading-relaxed">
            Tu asistente para{' '}
            <span className="text-emerald-400 font-semibold">{tenantName}</span>{' '}
            está configurado y listo para trabajar.
          </p>
        </div>

        {/* What's next */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 text-left space-y-3 max-w-md mx-auto">
          <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
            <Rocket className="w-4 h-4 text-emerald-400" />
            Próximos pasos
          </h3>
          <ul className="space-y-2 text-sm text-slate-400">
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 font-bold mt-0.5">1.</span>
              <span>Prueba tu asistente en el <strong className="text-slate-300">chat de pruebas</strong></span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 font-bold mt-0.5">2.</span>
              <span>Ajusta la configuración desde el panel si es necesario</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-emerald-400 font-bold mt-0.5">3.</span>
              <span>Cuando estés listo, coordina la <strong className="text-slate-300">conexión a WhatsApp</strong></span>
            </li>
          </ul>
        </div>

        {/* CTA */}
        <button
          onClick={handleContinue}
          className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl text-base font-semibold bg-gradient-to-r from-emerald-500 to-cyan-500 text-white hover:shadow-xl hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98] transition-all duration-300"
        >
          Ir al panel
          <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  )
}
