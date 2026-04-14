'use client'

/**
 * TenantContext — Tenant resolution, newcomer detection, and superadmin switching.
 *
 * Responsibilities:
 * - Resolves the current user's tenant from `tenant_users` table
 * - Detects newcomers (no tenant_users row = first login)
 * - Checks `is_setup_complete` to gate the onboarding wizard
 * - Checks `profiles.is_superadmin` for tenant switching
 * - Superadmin can override `currentTenantId` to view any tenant's data
 *
 * Observability: Every failure → console.error + Sentry with full context.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase'
import { useAuth } from './AuthContext'
import * as Sentry from '@sentry/nextjs'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TenantInfo {
  id: string
  name: string
  is_setup_complete: boolean
}

interface TenantContextType {
  /** The current active tenant ID */
  currentTenantId: string | null
  /** Current tenant details */
  currentTenant: TenantInfo | null
  /** Whether this is a first-time user with no tenant */
  isNewcomer: boolean
  /** Whether the current tenant has completed setup */
  isSetupComplete: boolean
  /** Whether the user has superadmin privileges */
  isSuperadmin: boolean
  /** All tenants (only populated for superadmins) */
  allTenants: TenantInfo[]
  /** Whether we're still loading tenant info */
  isLoadingTenant: boolean
  /** Error state */
  tenantError: string | null
  /** Switch to a different tenant (superadmin only) */
  switchTenant: (tenantId: string) => void
  /** Mark the current onboarding as complete and refresh */
  markSetupComplete: () => void
  /** Set tenant after provisioning */
  setProvisionedTenant: (tenantId: string, tenantName: string) => void
}

const TenantContext = createContext<TenantContextType | undefined>(undefined)

// ─── Provider ─────────────────────────────────────────────────────────────────

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoadingAuth } = useAuth()

  const [currentTenantId, setCurrentTenantId] = useState<string | null>(null)
  const [currentTenant, setCurrentTenant] = useState<TenantInfo | null>(null)
  const [isNewcomer, setIsNewcomer] = useState(false)
  const [isSetupComplete, setIsSetupComplete] = useState(false)
  const [isSuperadmin, setIsSuperadmin] = useState(false)
  const [allTenants, setAllTenants] = useState<TenantInfo[]>([])
  const [isLoadingTenant, setIsLoadingTenant] = useState(true)
  const [tenantError, setTenantError] = useState<string | null>(null)

  // ─── Resolve tenant on user change ───
  useEffect(() => {
    if (isLoadingAuth) return
    if (!user) {
      // Not logged in — reset everything
      setCurrentTenantId(null)
      setCurrentTenant(null)
      setIsNewcomer(false)
      setIsSetupComplete(false)
      setIsSuperadmin(false)
      setAllTenants([])
      setIsLoadingTenant(false)
      return
    }

    const resolveTenant = async () => {
      const _where = 'TenantContext.resolveTenant'
      setIsLoadingTenant(true)
      setTenantError(null)

      try {
        const supabase = createClient()
        const userId = user.id

        // Set Sentry user context
        Sentry.setUser({ id: userId, email: user.email })
        Sentry.setTag('feature', 'tenant_resolution')

        // Step 1: Check if user is superadmin
        let superadmin = false
        try {
          const { data: profileData, error: profileErr } = await supabase
            .from('profiles')
            .select('is_superadmin')
            .eq('id', userId)
            .single()

          if (profileErr) {
            // This might fail for brand new users (profile not yet created by trigger)
            console.warn(
              `[${_where}] Profile fetch failed (may be new user) | ` +
              `user=${userId} | error=${profileErr.message}`
            )
          } else if (profileData) {
            superadmin = profileData.is_superadmin === true
          }
        } catch (profileCatchErr: any) {
          console.error(
            `[${_where}] Profile query CRASHED | user=${userId} | error=${String(profileCatchErr).slice(0, 200)}`
          )
          Sentry.captureException(profileCatchErr, {
            extra: { where: _where, step: 'check_superadmin', user_id: userId },
          })
        }

        setIsSuperadmin(superadmin)
        Sentry.setTag('is_superadmin', String(superadmin))

        // Step 2: Get user's tenant
        try {
          const { data: tuData, error: tuErr } = await supabase
            .from('tenant_users')
            .select('tenant_id')
            .eq('user_id', userId)

          if (tuErr) {
            const errMsg = `[${_where}] tenant_users query failed | user=${userId} | error=${tuErr.message}`
            console.error(errMsg)
            Sentry.captureMessage(errMsg, 'error')
            setTenantError('Error al buscar tu empresa. Intenta recargar.')
            setIsLoadingTenant(false)
            return
          }

          if (!tuData || tuData.length === 0) {
            // NEWCOMER — no tenant yet
            console.info(`[${_where}] NEWCOMER detected | user=${userId} | email=${user.email}`)
            Sentry.setTag('is_newcomer', 'true')
            setIsNewcomer(true)
            setIsSetupComplete(false)
            setIsLoadingTenant(false)
            return
          }

          // User has a tenant
          const tenantId = tuData[0].tenant_id
          setCurrentTenantId(tenantId)
          setIsNewcomer(false)
          Sentry.setTag('tenant_id', tenantId)

          // Fetch tenant details
          const { data: tenantData, error: tenantErr } = await supabase
            .from('tenants')
            .select('id, name, is_setup_complete')
            .eq('id', tenantId)
            .single()

          if (tenantErr) {
            const errMsg = `[${_where}] Tenant fetch failed | tenant=${tenantId} | error=${tenantErr.message}`
            console.error(errMsg)
            Sentry.captureMessage(errMsg, 'error')
            setTenantError('Error al cargar datos de tu empresa.')
            setIsLoadingTenant(false)
            return
          }

          if (tenantData) {
            setCurrentTenant({
              id: tenantData.id,
              name: tenantData.name,
              is_setup_complete: tenantData.is_setup_complete ?? false,
            })
            setIsSetupComplete(tenantData.is_setup_complete ?? false)
            Sentry.setTag('is_setup_complete', String(tenantData.is_setup_complete))
          }

        } catch (tuCatchErr: any) {
          const errMsg = `[${_where}] Tenant resolution CRASHED | user=${userId} | error=${String(tuCatchErr).slice(0, 300)}`
          console.error(errMsg, tuCatchErr)
          Sentry.captureException(tuCatchErr, {
            extra: { where: _where, step: 'resolve_tenant', user_id: userId },
          })
          setTenantError('Error inesperado al resolver tu empresa.')
        }

        // Step 3: Superadmin — fetch all tenants for switcher
        if (superadmin) {
          try {
            const { data: allTenantsData, error: allErr } = await supabase
              .from('tenants')
              .select('id, name, is_setup_complete')
              .order('created_at', { ascending: false })

            if (allErr) {
              console.warn(
                `[${_where}] All-tenants query failed (non-fatal) | error=${allErr.message}`
              )
            } else if (allTenantsData) {
              setAllTenants(
                allTenantsData.map((t: any) => ({
                  id: t.id,
                  name: t.name,
                  is_setup_complete: t.is_setup_complete ?? false,
                }))
              )
            }
          } catch (allCatchErr: any) {
            console.warn(
              `[${_where}] All-tenants fetch CRASHED (non-fatal) | error=${String(allCatchErr).slice(0, 200)}`
            )
            Sentry.captureException(allCatchErr, {
              extra: { where: _where, step: 'fetch_all_tenants' },
            })
          }
        }

      } finally {
        setIsLoadingTenant(false)
      }
    }

    resolveTenant()
  }, [user, isLoadingAuth])

  // ─── Superadmin: switch tenant ───
  const switchTenant = useCallback((tenantId: string) => {
    const _where = 'TenantContext.switchTenant'
    const target = allTenants.find(t => t.id === tenantId)
    if (!target) {
      console.error(`[${_where}] Tenant not found in allTenants: ${tenantId}`)
      Sentry.captureMessage(`switchTenant called with unknown id: ${tenantId}`, 'warning')
      return
    }

    console.info(`[${_where}] Switching to tenant: ${target.name} (${tenantId})`)
    Sentry.setTag('tenant_id', tenantId)
    setCurrentTenantId(tenantId)
    setCurrentTenant(target)
    setIsSetupComplete(target.is_setup_complete)
  }, [allTenants])

  // ─── Mark onboarding complete ───
  const markSetupComplete = useCallback(() => {
    setIsSetupComplete(true)
    if (currentTenant) {
      setCurrentTenant({ ...currentTenant, is_setup_complete: true })
    }
  }, [currentTenant])

  // ─── After provisioning: set tenant immediately ───
  const setProvisionedTenant = useCallback((tenantId: string, tenantName: string) => {
    const _where = 'TenantContext.setProvisionedTenant'
    console.info(`[${_where}] Tenant provisioned: ${tenantName} (${tenantId})`)
    Sentry.setTag('tenant_id', tenantId)
    setCurrentTenantId(tenantId)
    setCurrentTenant({ id: tenantId, name: tenantName, is_setup_complete: false })
    setIsNewcomer(false)
    setIsSetupComplete(false)
  }, [])

  return (
    <TenantContext.Provider value={{
      currentTenantId,
      currentTenant,
      isNewcomer,
      isSetupComplete,
      isSuperadmin,
      allTenants,
      isLoadingTenant,
      tenantError,
      switchTenant,
      markSetupComplete,
      setProvisionedTenant,
    }}>
      {children}
    </TenantContext.Provider>
  )
}

export function useTenant() {
  const context = useContext(TenantContext)
  if (context === undefined) {
    throw new Error('useTenant must be used within a TenantProvider')
  }
  return context
}
