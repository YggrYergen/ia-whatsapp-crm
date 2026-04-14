'use client'

/**
 * CompletionStep — Step 3: Premium celebration screen after onboarding is complete.
 * 
 * Features:
 *   - Animated SVG checkmark with stroke drawing animation
 *   - Pulsing glow rings with emerald/cyan gradient
 *   - Floating glitter particles with random trajectories
 *   - Staggered content reveal
 *   - CTA redirects to /chats (sandbox testing)
 *
 * Ref: User requested "big relaxing check animation with extra glitters and glow"
 */

import React, { useEffect, useState } from 'react'
import { ArrowRight, Rocket, Sparkles } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface CompletionStepProps {
  tenantName: string
  onContinue: () => void
}

// Generate stable particle configs at module level (avoids SSR hydration mismatch)
const PARTICLES = Array.from({ length: 40 }, (_, i) => ({
  id: i,
  left: 5 + (i * 2.3) % 90,
  size: 2 + (i % 4),
  delay: (i * 0.15) % 3,
  duration: 2 + (i % 3) * 0.8,
  color: ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#34d399'][i % 6],
  startY: 110 + (i % 5) * 8,
}))

export default function CompletionStep({ tenantName, onContinue }: CompletionStepProps) {
  const router = useRouter()
  const [phase, setPhase] = useState(0) // 0=hidden, 1=check, 2=glow, 3=content

  // Staggered reveal animation
  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 100),   // Start check animation
      setTimeout(() => setPhase(2), 900),   // Expand glow
      setTimeout(() => setPhase(3), 1400),  // Show content
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const handleContinue = () => {
    onContinue()
    router.push('/chats')
  }

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950 flex items-center justify-center overflow-hidden">
      {/* ─── Ambient background glow ─── */}
      <div className={`absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 
        rounded-full blur-[150px] transition-all duration-[2000ms] ease-out
        ${phase >= 2 ? 'w-[800px] h-[800px] opacity-100' : 'w-[200px] h-[200px] opacity-0'}
        bg-gradient-radial from-emerald-500/15 via-cyan-500/8 to-transparent`} />
      
      {/* Secondary ambient glow */}
      <div className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
        w-[400px] h-[400px] rounded-full blur-[100px] transition-all duration-[1500ms]
        ${phase >= 2 ? 'opacity-60' : 'opacity-0'}
        bg-emerald-500/10`} />

      {/* ─── Floating glitter particles ─── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {PARTICLES.map((p) => (
          <div
            key={p.id}
            className={`absolute transition-opacity duration-700 ${phase >= 2 ? 'opacity-100' : 'opacity-0'}`}
            style={{
              left: `${p.left}%`,
              bottom: `-${p.size}px`,
              animation: phase >= 2 ? `glitterFloat ${p.duration}s ease-out ${p.delay}s infinite` : 'none',
            }}
          >
            <div
              className="rounded-full"
              style={{
                width: p.size,
                height: p.size,
                backgroundColor: p.color,
                boxShadow: `0 0 ${p.size * 3}px ${p.color}60`,
              }}
            />
          </div>
        ))}
      </div>

      {/* ─── Main content ─── */}
      <div className="relative z-10 max-w-lg w-full mx-4 text-center space-y-8">
        
        {/* ─── Animated checkmark ─── */}
        <div className="flex justify-center mb-4">
          <div className="relative">
            {/* Outer glow rings */}
            <div className={`absolute -inset-8 rounded-full transition-all duration-[1200ms] ease-out
              ${phase >= 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}
              border border-emerald-500/10`} />
            <div className={`absolute -inset-14 rounded-full transition-all duration-[1500ms] ease-out
              ${phase >= 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-50'}
              border border-emerald-500/5`} />
            
            {/* Pulsing glow behind checkmark */}
            <div className={`absolute -inset-4 rounded-full transition-all duration-[1000ms]
              ${phase >= 2 ? 'opacity-100' : 'opacity-0'}
              bg-emerald-500/20 blur-xl animate-pulse`} />

            {/* Main circle */}
            <div className={`relative w-28 h-28 rounded-full flex items-center justify-center
              transition-all duration-700 ease-out
              ${phase >= 1 ? 'scale-100 opacity-100' : 'scale-50 opacity-0'}
              bg-gradient-to-br from-emerald-500 to-cyan-500
              shadow-2xl shadow-emerald-500/40`}>
              
              {/* SVG Checkmark with stroke animation */}
              <svg viewBox="0 0 52 52" className="w-14 h-14">
                <path
                  className={`${phase >= 1 ? 'animate-checkDraw' : ''}`}
                  d="M14 27 L22 35 L38 17"
                  fill="none"
                  stroke="white"
                  strokeWidth="4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{
                    strokeDasharray: 50,
                    strokeDashoffset: phase >= 1 ? 0 : 50,
                    transition: 'stroke-dashoffset 0.6s ease-out 0.3s',
                  }}
                />
              </svg>
            </div>

            {/* Sparkle accents */}
            <div className={`absolute -top-2 -right-1 transition-all duration-500 delay-700
              ${phase >= 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-0'}`}>
              <Sparkles className="w-6 h-6 text-amber-400 animate-pulse" />
            </div>
            <div className={`absolute -bottom-1 -left-3 transition-all duration-500 delay-900
              ${phase >= 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-0'}`}>
              <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" style={{ animationDelay: '0.5s' }} />
            </div>
          </div>
        </div>

        {/* ─── Title + Description ─── */}
        <div className={`space-y-3 transition-all duration-700
          ${phase >= 3 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            ¡Todo listo! 🎉
          </h1>
          <p className="text-lg text-slate-400 max-w-md mx-auto leading-relaxed">
            Tu asistente para{' '}
            <span className="text-emerald-400 font-semibold">{tenantName}</span>{' '}
            está configurado y listo para trabajar.
          </p>
        </div>

        {/* ─── Next steps card ─── */}
        <div className={`transition-all duration-700 delay-200
          ${phase >= 3 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 text-left space-y-3 max-w-md mx-auto
            backdrop-blur-sm">
            <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
              <Rocket className="w-4 h-4 text-emerald-400" />
              Próximos pasos
            </h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold mt-0.5">1.</span>
                <span>Prueba tu asistente en el <strong className="text-slate-300">chat de pruebas</strong> — envía mensajes como si fueras un cliente</span>
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
        </div>

        {/* ─── CTA ─── */}
        <div className={`transition-all duration-700 delay-500
          ${phase >= 3 ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          <button
            onClick={handleContinue}
            className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl text-base font-semibold
              bg-gradient-to-r from-emerald-500 to-cyan-500 text-white
              hover:shadow-xl hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98]
              transition-all duration-300"
          >
            Probar mi asistente
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      </div>

      {/* ─── Inline CSS for keyframe animations ─── */}
      <style jsx>{`
        @keyframes glitterFloat {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          100% {
            transform: translateY(-100vh) rotate(720deg);
            opacity: 0;
          }
        }
        @keyframes checkDraw {
          0% { stroke-dashoffset: 50; }
          100% { stroke-dashoffset: 0; }
        }
      `}</style>
    </div>
  )
}
