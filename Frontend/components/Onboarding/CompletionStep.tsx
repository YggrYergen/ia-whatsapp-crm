'use client'

/**
 * CompletionStep — Step 3: Premium celebration screen after onboarding is complete.
 * 
 * Features:
 *   - Animated SVG checkmark with stroke drawing animation
 *   - Pulsing glow rings with emerald/cyan gradient
 *   - Confetti explosion from center outwards
 *   - Firework bursts at staggered positions
 *   - Floating glitter particles with random trajectories
 *   - Staggered content reveal
 *   - CTA redirects to /chats (sandbox testing)
 *
 * Ref: User requested "confetti and shit exploding from the center outwards with fireworks"
 */

import React, { useEffect, useState } from 'react'
import { ArrowRight, Rocket, Sparkles } from 'lucide-react'
import { useRouter } from 'next/navigation'

interface CompletionStepProps {
  tenantName: string
  onContinue: () => void
}

// ─── Confetti pieces ───────────────────────────────────────────────────────────
// Generate stable configs at module level (avoids SSR hydration mismatch)
const CONFETTI_COLORS = ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#34d399', '#f472b6', '#fbbf24', '#818cf8', '#2dd4bf']

const CONFETTI = Array.from({ length: 80 }, (_, i) => ({
  id: i,
  // Spread from center outward in all directions
  angle: (i * 4.5) % 360,
  distance: 30 + (i * 7) % 400,
  size: 4 + (i % 6) * 2,
  color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  delay: (i * 0.02) % 0.8,
  duration: 0.8 + (i % 4) * 0.3,
  rotation: (i * 37) % 360,
  shape: i % 3, // 0=square, 1=circle, 2=rectangle
}))

// ─── Firework bursts ──────────────────────────────────────────────────────────
const FIREWORKS = Array.from({ length: 6 }, (_, i) => ({
  id: i,
  x: 15 + (i * 14) % 75,
  y: 10 + (i * 11) % 60,
  delay: 0.3 + i * 0.25,
  color: CONFETTI_COLORS[i * 2 % CONFETTI_COLORS.length],
  sparks: Array.from({ length: 8 }, (_, j) => ({
    angle: j * 45,
    distance: 20 + (j * 5),
  })),
}))

// ─── Floating glitter ─────────────────────────────────────────────────────────
const PARTICLES = Array.from({ length: 40 }, (_, i) => ({
  id: i,
  left: 5 + (i * 2.3) % 90,
  size: 2 + (i % 4),
  delay: (i * 0.15) % 3,
  duration: 2 + (i % 3) * 0.8,
  color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  startY: 110 + (i % 5) * 8,
}))

export default function CompletionStep({ tenantName, onContinue }: CompletionStepProps) {
  const router = useRouter()
  const [phase, setPhase] = useState(0) // 0=hidden, 1=check, 2=glow+confetti, 3=content
  const [confettiDone, setConfettiDone] = useState(false)

  // Staggered reveal animation
  useEffect(() => {
    const timers = [
      setTimeout(() => setPhase(1), 100),   // Start check animation
      setTimeout(() => setPhase(2), 700),   // Confetti explosion + glow
      setTimeout(() => setPhase(3), 1600),  // Show content
      setTimeout(() => setConfettiDone(true), 3500), // Clean up confetti DOM
    ]
    return () => timers.forEach(clearTimeout)
  }, [])

  const handleContinue = () => {
    onContinue()
    router.push('/chats/sandbox')
  }

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950 flex items-center justify-center overflow-hidden">
      {/* ─── INJECTED KEYFRAMES (Bypasses CSS caching and scoping issues) ─── */}
      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes confettiBurst {
            0% { transform: translate(-50%, -50%) rotate(0deg) scale(1); opacity: 1; }
            70% { opacity: 1; }
            100% { transform: translate(calc(-50% + var(--tx)), calc(-50% + var(--ty))) rotate(var(--rot)) scale(0.3); opacity: 0; }
        }
        @keyframes fireworkFlash {
            0% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
            30% { transform: translate(-50%, -50%) scale(3); opacity: 1; }
            100% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
        }
        @keyframes fireworkSpark {
            0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
            100% { transform: translate(calc(-50% + var(--sx)), calc(-50% + var(--sy))) scale(0); opacity: 0; }
        }
        @keyframes glitterFloat {
            0% { transform: translateY(0) scale(1); opacity: 0; }
            20% { transform: translateY(-20px) scale(1.2); opacity: 1; }
            80% { transform: translateY(-80px) scale(0.8); opacity: 0.8; }
            100% { transform: translateY(-120px) scale(0.5); opacity: 0; }
        }
      `}} />

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

      {/* ─── CONFETTI EXPLOSION ─── */}
      {phase >= 2 && !confettiDone && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-[20]">
          {CONFETTI.map((c) => {
            const rad = (c.angle * Math.PI) / 180
            const tx = Math.cos(rad) * c.distance
            const ty = Math.sin(rad) * c.distance
            return (
              <div
                key={`confetti-${c.id}`}
                className="absolute left-1/2 top-1/2"
                style={{
                  animation: `confettiBurst ${c.duration}s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${c.delay}s forwards`,
                  '--tx': `${tx}px`,
                  '--ty': `${ty}px`,
                  '--rot': `${c.rotation + 720}deg`,
                } as React.CSSProperties}
              >
                <div
                  style={{
                    width: c.shape === 2 ? c.size * 2.5 : c.size,
                    height: c.size,
                    backgroundColor: c.color,
                    borderRadius: c.shape === 1 ? '50%' : c.shape === 2 ? '2px' : '1px',
                    boxShadow: `0 0 ${c.size * 2}px ${c.color}80`,
                  }}
                />
              </div>
            )
          })}
        </div>
      )}

      {/* ─── FIREWORK BURSTS ─── */}
      {phase >= 2 && !confettiDone && (
        <div className="absolute inset-0 pointer-events-none overflow-hidden z-[15]">
          {FIREWORKS.map((fw) => (
            <div
              key={`fw-${fw.id}`}
              className="absolute"
              style={{ left: `${fw.x}%`, top: `${fw.y}%` }}
            >
              {/* Central flash */}
              <div
                className="absolute -translate-x-1/2 -translate-y-1/2"
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  backgroundColor: fw.color,
                  boxShadow: `0 0 20px ${fw.color}, 0 0 40px ${fw.color}60`,
                  animation: `fireworkFlash 0.6s ease-out ${fw.delay}s both`,
                }}
              />
              {/* Sparks */}
              {fw.sparks.map((spark, si) => {
                const rad = (spark.angle * Math.PI) / 180
                const sx = Math.cos(rad) * spark.distance
                const sy = Math.sin(rad) * spark.distance
                return (
                  <div
                    key={si}
                    className="absolute -translate-x-1/2 -translate-y-1/2"
                    style={{
                      width: 3,
                      height: 3,
                      borderRadius: '50%',
                      backgroundColor: fw.color,
                      boxShadow: `0 0 8px ${fw.color}`,
                      animation: `fireworkSpark 0.8s ease-out ${fw.delay + 0.05}s both`,
                      '--sx': `${sx}px`,
                      '--sy': `${sy}px`,
                    } as React.CSSProperties}
                  />
                )
              })}
            </div>
          ))}
        </div>
      )}

      {/* ─── Floating glitter particles (continuous) ─── */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden hover:pointer-events-none">
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

            {/* Shockwave ring */}
            {phase >= 2 && (
              <div
                className="absolute -inset-4 rounded-full border-2 border-emerald-400/40"
                style={{
                  animation: 'shockwave 1s ease-out forwards',
                }}
              />
            )}

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
            <div className={`absolute top-0 -left-6 transition-all duration-500
              ${phase >= 2 ? 'opacity-100 scale-100' : 'opacity-0 scale-0'}`}
              style={{ animationDelay: '1.2s' }}>
              <Sparkles className="w-4 h-4 text-purple-400 animate-pulse" style={{ animationDelay: '0.8s' }} />
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
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 text-left space-y-3 max-w-md mx-auto backdrop-blur-sm">
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

    </div>
  )
}
