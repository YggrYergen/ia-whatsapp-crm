'use client'

import { createClient } from '@/lib/supabase'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'
import * as Sentry from '@sentry/nextjs'

/**
 * Auth confirm page — handles the OAuth PKCE callback.
 *
 * How it works (per official Supabase docs):
 * 1. signInWithOAuth stores the code_verifier in a cookie
 * 2. After Google OAuth, Supabase redirects here with ?code=XXX
 * 3. createBrowserClient (singleton) auto-detects ?code= in the URL
 *    during its _initialize() and calls exchangeCodeForSession internally
 * 4. On success, onAuthStateChange fires with SIGNED_IN
 * 5. We listen for that event and redirect to /dashboard
 *
 * We do NOT call exchangeCodeForSession manually — that causes a race
 * condition with the auto-initialization.
 */
function ConfirmAuth() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const errorParam = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')

        if (errorParam) {
            router.replace(`/login?error=${encodeURIComponent(errorDescription || errorParam)}`)
            return
        }

        // Create the browser client — this singleton auto-initializes and
        // detects ?code= in window.location, performing the PKCE exchange.
        const supabase = createClient()

        // Listen for the auth state change that fires after auto-exchange
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
            if (event === 'SIGNED_IN' && session) {
                router.replace('/dashboard')
            }
            if (event === 'TOKEN_REFRESHED' && session) {
                router.replace('/dashboard')
            }
        })

        // Also check if session already exists (e.g., auto-init already completed)
        supabase.auth.getSession().then(({ data: { session }, error: sessionError }) => {
            if (sessionError) {
                console.error('[auth/confirm] Session error:', sessionError.message)
                Sentry.captureMessage(`Auth PKCE session error: ${sessionError.message}`, 'error')
                setError(sessionError.message)
                return
            }
            if (session) {
                router.replace('/dashboard')
            }
        })

        // Timeout: if nothing happens in 10 seconds, show an error
        const timeout = setTimeout(() => {
            setError('La autenticación está tardando demasiado. Intenta de nuevo.')
        }, 10000)

        return () => {
            subscription.unsubscribe()
            clearTimeout(timeout)
        }
    }, [searchParams, router])

    if (error) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <div className="bg-white p-6 rounded-lg shadow max-w-md w-full text-center">
                    <p className="text-red-600 font-bold text-lg">Error de autenticación</p>
                    <p className="text-sm text-red-500 mt-2">{error}</p>
                    <button
                        onClick={() => router.replace('/login')}
                        className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700"
                    >
                        Volver al login
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
            <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto"></div>
                <p className="mt-4 text-slate-600">Completando inicio de sesión...</p>
            </div>
        </div>
    )
}

export default function ConfirmPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <p className="text-slate-500">Cargando...</p>
            </div>
        }>
            <ConfirmAuth />
        </Suspense>
    )
}
