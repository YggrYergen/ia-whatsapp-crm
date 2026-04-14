'use client'

/**
 * OnboardingGate — Decides whether to show the onboarding wizard overlay.
 * 
 * Logic:
 *   - If tenant is still loading → show nothing (let layout spinner handle it)
 *   - If user is a newcomer (no tenant) → show OnboardingWizard (Step 1: Welcome)
 *   - If user has tenant but setup not complete → show OnboardingWizard (Step 2: Config)
 *   - If setup is complete → show nothing (normal panel)
 *
 * This component is rendered inside CrmProvider, so it has access to
 * TenantContext and AuthContext.
 *
 * Observability: State transitions logged to console.
 */

import React from 'react'
import { useTenant } from '@/contexts/TenantContext'
import OnboardingWizard from '@/components/Onboarding/OnboardingWizard'

export default function OnboardingGate() {
  const { isNewcomer, isSetupComplete, isLoadingTenant, tenantError } = useTenant()

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

  // Newcomer or setup not complete → show onboarding wizard
  if (isNewcomer || !isSetupComplete) {
    return <OnboardingWizard />
  }

  // Setup complete — render nothing, let the normal panel show
  return null
}
