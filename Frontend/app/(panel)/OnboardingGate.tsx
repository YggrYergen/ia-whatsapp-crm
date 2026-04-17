'use client'

/**
 * OnboardingGate — Decides whether to show the onboarding wizard overlay.
 *
 * Logic:
 *   - If tenant is still loading → show nothing (let layout spinner handle it)
 *   - If user is a newcomer (no tenant) → show OnboardingWizard (Step 1: Welcome)
 *   - If user has tenant but setup not complete → show OnboardingWizard (Step 2: Config)
 *   - If setup is complete AND wizard was never shown → show nothing (normal panel)
 *   - If setup becomes complete WHILE wizard is showing → KEEP wizard mounted
 *     so CompletionStep (confetti/fireworks) can render. The wizard self-dismisses
 *     when the user clicks the CTA.
 *
 * ROOT CAUSE FIX (2026-04-15): markSetupComplete() used to flip isSetupComplete=true,
 * which immediately unmounted OnboardingWizard before CompletionStep could render.
 * Now we track `wizardActive` locally so the wizard stays alive.
 *
 * Observability: State transitions logged to console + Sentry.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useTenant } from '@/contexts/TenantContext'
import OnboardingWizard from '@/components/Onboarding/OnboardingWizard'
import * as Sentry from '@sentry/nextjs'

export default function OnboardingGate() {
  const { isNewcomer, isSetupComplete, isLoadingTenant, tenantError } = useTenant()

  // Track whether the wizard has been activated this session.
  // Once true, stays true until explicitly dismissed by CompletionStep CTA.
  const [wizardActive, setWizardActive] = useState(false)

  // Activate wizard when conditions are met
  useEffect(() => {
    if (isLoadingTenant) return
    if (wizardActive) return // Already showing — don't re-evaluate

    if (isNewcomer || !isSetupComplete) {
      console.info('[OnboardingGate] Activating wizard | isNewcomer=%s | isSetupComplete=%s', isNewcomer, isSetupComplete)
      Sentry.addBreadcrumb({ category: 'onboarding', message: 'Wizard activated', level: 'info' })
      setWizardActive(true)
    }
  }, [isLoadingTenant, isNewcomer, isSetupComplete, wizardActive])

  // Called by OnboardingWizard when the user clicks the final CTA
  const handleWizardDismiss = useCallback(() => {
    console.info('[OnboardingGate] Wizard dismissed by user')
    Sentry.addBreadcrumb({ category: 'onboarding', message: 'Wizard dismissed', level: 'info' })
    setWizardActive(false)
  }, [])

  // Still resolving tenant — don't render anything
  if (isLoadingTenant) {
    return null
  }

  // Tenant error — show recoverable error in panel context
  if (tenantError) {
    return (
      <div className="fixed inset-0 z-[99] bg-slate-950/90 flex items-center justify-center">
        <div className="bg-slate-900 border border-red-500/30 rounded-xl p-6 max-w-md mx-4 text-center space-y-4">
          <p className="text-red-400 font-semibold">Error al cargar tu cuenta</p>
          <p className="text-sm text-slate-400">{tenantError}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-emerald-500 text-white rounded-lg text-sm hover:bg-emerald-400 transition-colors"
          >
            Reintentar
          </button>
        </div>
      </div>
    )
  }

  // Wizard is active — keep it mounted regardless of isSetupComplete
  if (wizardActive) {
    return <OnboardingWizard onDismiss={handleWizardDismiss} />
  }

  // Setup complete and wizard never activated — render nothing, show normal panel
  return null
}
