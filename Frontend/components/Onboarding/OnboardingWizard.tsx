'use client'

/**
 * OnboardingWizard — 3-step orchestrator for newcomer onboarding.
 *
 * Steps:
 *   1. WelcomeStep — "Bienvenido" + provision tenant on CTA click
 *   2. ConfigChat — AI-guided configuration with SSE streaming
 *   3. CompletionStep — Celebration (confetti/fireworks) + redirect to /chats/sandbox
 *
 * This component is rendered as a full-screen overlay by OnboardingGate
 * when `isNewcomer || !isSetupComplete`.
 *
 * ROOT CAUSE FIX (2026-04-15): The wizard now receives `onDismiss` from
 * OnboardingGate. CompletionStep calls it when the user clicks the CTA,
 * ensuring the wizard stays mounted through the entire celebration animation.
 * Previously, `markSetupComplete()` caused the gate to unmount the wizard
 * before confetti could render.
 *
 * Observability: Step transitions logged to console + Sentry breadcrumbs.
 */

import React, { useState, useCallback } from 'react'
import { useTenant } from '@/contexts/TenantContext'
import { useAuth } from '@/contexts/AuthContext'
import WelcomeStep from './WelcomeStep'
import ConfigChat from './ConfigChat'
import CompletionStep from './CompletionStep'
import * as Sentry from '@sentry/nextjs'

type WizardStep = 'welcome' | 'config' | 'complete'

interface OnboardingWizardProps {
  /** Called when the user dismisses the wizard (clicks CTA on CompletionStep) */
  onDismiss: () => void
}

export default function OnboardingWizard({ onDismiss }: OnboardingWizardProps) {
  const { user } = useAuth()
  const { currentTenantId, currentTenant, isNewcomer, isSetupComplete, setProvisionedTenant, markSetupComplete } = useTenant()

  // Determine initial step based on state
  // IMPORTANT: Always start at 'welcome' when setup is not complete OR user is a newcomer.
  // This ensures /api/onboarding/provision is called, which creates the tenant_onboarding
  // row that the ConfigChat (Step 2) needs to persist field data via UPDATE.
  // Skipping welcome → missing tenant_onboarding row → PGRST116 on every _save_field.
  const getInitialStep = (): WizardStep => {
    if (!currentTenantId || isNewcomer) return 'welcome'   // No tenant yet
    if (!isSetupComplete) return 'welcome'                  // Has tenant but not configured — must re-provision row
    return 'complete'
  }

  const [step, setStep] = useState<WizardStep>(getInitialStep)
  const [wizardTenantId, setWizardTenantId] = useState<string | null>(currentTenantId)
  const [wizardTenantName, setWizardTenantName] = useState<string>(currentTenant?.name || '')

  // ─── Step 1 → 2: After provisioning ───
  const handleProvisionComplete = useCallback((tenantId: string, tenantName: string) => {
    const _where = 'OnboardingWizard.handleProvisionComplete'
    console.info(`[${_where}] Provisioned: ${tenantName} (${tenantId})`)
    Sentry.addBreadcrumb({
      category: 'onboarding',
      message: `Step 1→2: Tenant provisioned (${tenantId})`,
      level: 'info',
    })

    setWizardTenantId(tenantId)
    setWizardTenantName(tenantName)
    setProvisionedTenant(tenantId, tenantName)
    setStep('config')
  }, [setProvisionedTenant])

  // ─── Step 2 → 3: After config is done ───
  const handleConfigComplete = useCallback(() => {
    const _where = 'OnboardingWizard.handleConfigComplete'
    console.info(`[${_where}] Configuration complete for tenant ${wizardTenantId}`)
    Sentry.addBreadcrumb({
      category: 'onboarding',
      message: `Step 2→3: Config complete (${wizardTenantId})`,
      level: 'info',
    })

    markSetupComplete()
    setStep('complete')
  }, [wizardTenantId, markSetupComplete])

  // ─── Step 3 → Dismiss: After user clicks CTA on CompletionStep ───
  const handleFinalContinue = useCallback(() => {
    const _where = 'OnboardingWizard.handleFinalContinue'
    console.info(`[${_where}] Onboarding finished — dismissing wizard, redirecting to /chats/sandbox`)
    Sentry.addBreadcrumb({
      category: 'onboarding',
      message: 'Step 3→Dismiss: Onboarding complete',
      level: 'info',
    })
    // Tell OnboardingGate to unmount us AFTER the user has seen the celebration
    onDismiss()
  }, [onDismiss])

  // ─── Render current step ───
  switch (step) {
    case 'welcome':
      return (
        <WelcomeStep
          userId={user?.id || ''}
          userEmail={user?.email || ''}
          userName={user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Usuario'}
          onComplete={handleProvisionComplete}
        />
      )

    case 'config':
      if (!wizardTenantId) {
        // Safety fallback — should never happen
        console.error('[OnboardingWizard] config step but no tenant ID — resetting to welcome')
        Sentry.captureMessage('OnboardingWizard: config step without tenant ID', 'error')
        setStep('welcome')
        return null
      }
      return (
        <ConfigChat
          tenantId={wizardTenantId}
          onConfigComplete={handleConfigComplete}
        />
      )

    case 'complete':
      return (
        <CompletionStep
          tenantName={wizardTenantName || 'tu negocio'}
          onContinue={handleFinalContinue}
        />
      )

    default:
      console.error(`[OnboardingWizard] Unknown step: ${step}`)
      Sentry.captureMessage(`OnboardingWizard: unknown step ${step}`, 'error')
      return null
  }
}
