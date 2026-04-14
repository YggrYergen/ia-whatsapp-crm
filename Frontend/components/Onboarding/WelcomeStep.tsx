'use client'

/**
 * WelcomeStep — Step 1 of the onboarding wizard.
 * Full-screen dark overlay with animated welcome message.
 * On "Comenzar" click, provisions the tenant via backend and advances to Step 2.
 *
 * Observability: Provisioning errors → console.error + Sentry.
 */

import React, { useState } from 'react'
import { Sparkles, ArrowRight, Zap } from 'lucide-react'
import * as Sentry from '@sentry/nextjs'

interface WelcomeStepProps {
  userId: string
  userEmail: string
  userName: string
  onComplete: (tenantId: string, tenantName: string) => void
}

export default function WelcomeStep({ userId, userEmail, userName, onComplete }: WelcomeStepProps) {
  const [isProvisioning, setIsProvisioning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async () => {
    const _where = 'WelcomeStep.handleStart'
    setIsProvisioning(true)
    setError(null)

    try {
      const response = await fetch('/api/onboarding/provision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          email: userEmail,
          full_name: userName,
        }),
      })

      if (!response.ok) {
        const errText = await response.text().catch(() => 'Unknown error')
        const errMsg = `[${_where}] Provision HTTP ${response.status}: ${errText.slice(0, 300)}`
        console.error(errMsg)
        Sentry.captureMessage(errMsg, 'error')
        setError('Error al crear tu cuenta. Intenta de nuevo.')
        setIsProvisioning(false)
        return
      }

      const data = await response.json()

      if (data.status === 'error') {
        const errMsg = `[${_where}] Provision returned error: ${data.message}`
        console.error(errMsg)
        Sentry.captureMessage(errMsg, 'error')
        setError(data.message || 'Error desconocido.')
        setIsProvisioning(false)
        return
      }

      // Success — existing or newly created
      console.info(`[${_where}] Provision success: ${data.status} | tenant=${data.tenant_id}`)
      onComplete(data.tenant_id, data.tenant_name || userName)

    } catch (fetchErr: any) {
      const errMsg = `[${_where}] Provision fetch CRASHED | error=${String(fetchErr).slice(0, 300)}`
      console.error(errMsg, fetchErr)
      Sentry.captureException(fetchErr, {
        extra: { where: _where, user_id: userId, email: userEmail },
      })
      setError('Error de conexión. Verifica tu internet e intenta de nuevo.')
      setIsProvisioning(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] bg-slate-950 flex items-center justify-center animate-onboarding-in">
      {/* Background subtle grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem]" />

      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-emerald-500/5 rounded-full blur-[100px]" />

      <div className="relative z-10 max-w-lg w-full mx-4 text-center space-y-8">
        {/* Logo / Icon */}
        <div className="flex justify-center">
          <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-2xl flex items-center justify-center shadow-2xl shadow-emerald-500/20 ring-4 ring-emerald-500/10">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
        </div>

        {/* Title */}
        <div className="space-y-3">
          <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
            Bienvenido a{' '}
            <span className="bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
              tuAsistenteVirtual
            </span>
          </h1>
          <p className="text-lg text-slate-400 max-w-md mx-auto leading-relaxed">
            Vamos a configurar tu asistente de WhatsApp con inteligencia artificial en pocos minutos.
          </p>
        </div>

        {/* Feature highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-md mx-auto">
          {[
            { icon: '🤖', label: 'Asistente IA 24/7' },
            { icon: '⚡', label: 'Configuración guiada' },
            { icon: '📱', label: 'WhatsApp integrado' },
          ].map((f) => (
            <div key={f.label} className="bg-slate-900/80 border border-slate-800 rounded-xl px-3 py-2.5 text-center">
              <div className="text-xl mb-1">{f.icon}</div>
              <div className="text-xs text-slate-400 font-medium">{f.label}</div>
            </div>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {/* CTA Button */}
        <button
          onClick={handleStart}
          disabled={isProvisioning}
          className={`
            group inline-flex items-center gap-2 px-8 py-4 rounded-xl text-base font-semibold
            transition-all duration-300
            ${isProvisioning
              ? 'bg-slate-700 text-slate-400 cursor-wait'
              : 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white hover:shadow-xl hover:shadow-emerald-500/25 hover:scale-[1.02] active:scale-[0.98]'
            }
          `}
        >
          {isProvisioning ? (
            <>
              <div className="w-5 h-5 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
              Preparando tu espacio...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Comenzar configuración
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </>
          )}
        </button>

        <p className="text-xs text-slate-600">
          Solo toma 3-5 minutos • Sin tarjeta de crédito
        </p>
      </div>
    </div>
  )
}
