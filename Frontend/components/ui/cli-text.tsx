'use client'

import { useEffect, useState } from 'react'
import { Tektur } from 'next/font/google'

const tektur = Tektur({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-tektur',
  display: 'swap',
})

/**
 * Pre-Suasion optimized phrases for Chilean SMB owners.
 *
 * Design principles applied (Cialdini, Pre-Suasion):
 * - "What's Focal Is Causal": each phrase focuses attention on power, readiness, and identity
 * - "The Self-Relevant": uses "tú" framing — the system exists for THIS person
 * - Achievement words: "listo", "activo", "control", "operando" prime for action
 * - The Unfinished + Mystery: trailing "..." creates Zeigarnik tension, pulls forward
 * - Authority by implication: system speaks, not a UI — it KNOWS they are here
 * - Chilean register: natural, direct, no formal "usted" — peer-level AI
 */
const PHRASES = [
  'Hola...',
  'Bienvenido.',
  'Te estaba esperando.',
  'Está todo listo.',
  'Tu IA ya está activa.',
  'Tus clientes están siendo atendidos.',
  'Sin perder una venta.',
  'Las 24 horas.',
  'Modo automático.',
  'Tu negocio no para.',
  'Respondiendo por ti.',
  'Todo bajo control.',
  'Sistema en línea.',
  'Listos para hoy.',
  'Nunca más perderás un cliente.',
]

// Timing (ms)
const TYPE_SPEED = 69   // per character (~33% slower)
const ERASE_SPEED = 37   // per character (faster than typing, also 33% slower)
const PAUSE_AFTER = 1800 // hold full phrase before erasing
const PAUSE_BEFORE = 320  // gap between phrases

type Phase = 'typing' | 'holding' | 'erasing' | 'waiting'

export function CliText() {
  const [displayed, setDisplayed] = useState('')
  const [phraseIndex, setPhraseIndex] = useState(0)
  const [phase, setPhase] = useState<Phase>('typing')
  const [charIndex, setCharIndex] = useState(0)
  const [cursorVisible, setCursorVisible] = useState(true)

  // Cursor blink
  useEffect(() => {
    const id = setInterval(() => setCursorVisible(v => !v), 530)
    return () => clearInterval(id)
  }, [])

  // Typewriter engine
  useEffect(() => {
    const phrase = PHRASES[phraseIndex]

    if (phase === 'typing') {
      if (charIndex < phrase.length) {
        const t = setTimeout(() => {
          setDisplayed(phrase.slice(0, charIndex + 1))
          setCharIndex(i => i + 1)
        }, TYPE_SPEED)
        return () => clearTimeout(t)
      } else {
        // Finished typing → hold
        const t = setTimeout(() => setPhase('erasing'), PAUSE_AFTER)
        return () => clearTimeout(t)
      }
    }

    if (phase === 'erasing') {
      if (charIndex > 0) {
        const t = setTimeout(() => {
          setDisplayed(phrase.slice(0, charIndex - 1))
          setCharIndex(i => i - 1)
        }, ERASE_SPEED)
        return () => clearTimeout(t)
      } else {
        // Fully erased → wait then advance phrase
        const t = setTimeout(() => {
          setPhraseIndex(i => (i + 1) % PHRASES.length)
          setPhase('typing')
        }, PAUSE_BEFORE)
        return () => clearTimeout(t)
      }
    }
  }, [charIndex, phase, phraseIndex])

  return (
    <div
      className={tektur.className}
      style={{
        width: '100%',
        maxWidth: '290px',
        minHeight: '2.2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        // Transparent light-blue — matches accretion disk hue
        color: 'rgba(147, 197, 253, 0.72)', // blue-300 at 72%
        fontSize: '1.56rem',
        fontWeight: 500,
        letterSpacing: '0.04em',
        lineHeight: 1.4,
        // Subtle glow so it reads over the vortex
        textShadow: '0 0 18px rgba(147,197,253,0.35), 0 0 4px rgba(147,197,253,0.15)',
        userSelect: 'none',
      }}
    >
      <span>{displayed}</span>
      {/* Blinking block cursor — thinner, matches CLI aesthetic */}
      <span
        style={{
          display: 'inline-block',
          width: '1.5px',
          height: '0.85em',
          marginLeft: '2px',
          verticalAlign: 'text-bottom',
          backgroundColor: cursorVisible
            ? 'rgba(147, 197, 253, 0.85)'
            : 'transparent',
          boxShadow: cursorVisible
            ? '0 0 6px rgba(147,197,253,0.6)'
            : 'none',
          transition: 'background-color 0.08s, box-shadow 0.08s',
        }}
      />
    </div>
  )
}
