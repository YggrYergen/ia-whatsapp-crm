'use client'

import { createClient } from '@/lib/supabase'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'

function ConfirmAuth() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [debugInfo, setDebugInfo] = useState<string>('')
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const code = searchParams.get('code')
        const errorParam = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')

        // Collect debug info about storage state
        const cookies = document.cookie
        const cookieNames = cookies
            ? cookies.split(';').map(c => c.trim().split('=')[0])
            : []
        const debugData = {
            url: window.location.href,
            hasCode: !!code,
            cookieCount: cookieNames.length,
            cookieNames,
            hasPKCECookie: cookieNames.some(n =>
                n.includes('code-verifier') || n.includes('pkce')
            ),
            localStorageKeys: Object.keys(localStorage).filter(k =>
                k.includes('supabase') || k.includes('sb-') || k.includes('pkce') || k.includes('code')
            ),
        }
        setDebugInfo(JSON.stringify(debugData, null, 2))
        console.log('[auth/confirm] Debug:', debugData)
        console.log('[auth/confirm] Raw cookies:', cookies)

        if (errorParam) {
            router.replace(`/login?error=${encodeURIComponent(errorDescription || errorParam)}`)
            return
        }

        if (!code) {
            router.replace('/login')
            return
        }

        // Create a new browser client - this is the same singleton as in the login page.
        // The browser client uses document.cookie for storage, so the code_verifier
        // stored during signInWithOAuth should be available here.
        const supabase = createClient()

        supabase.auth.exchangeCodeForSession(code)
            .then(({ data, error: exchangeError }) => {
                if (exchangeError) {
                    console.error('[auth/confirm] Exchange error:', exchangeError.message)
                    setError(exchangeError.message)
                    // Don't redirect immediately - show debug info
                } else {
                    console.log('[auth/confirm] Exchange success! Redirecting to dashboard.')
                    router.replace('/dashboard')
                }
            })
            .catch((err) => {
                console.error('[auth/confirm] Exchange crash:', err)
                setError(err.message || 'Unknown error')
            })
    }, [searchParams, router])

    // Show debug info on screen for diagnosis
    if (error) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <div className="bg-white p-6 rounded-lg shadow max-w-2xl w-full">
                    <p className="text-red-600 font-bold text-lg">Error de autenticación</p>
                    <p className="text-sm text-red-500 mt-2 break-all">{error}</p>
                    <details className="mt-4" open>
                        <summary className="cursor-pointer text-sm text-slate-500 font-medium">
                            Debug Info (cookies & storage)
                        </summary>
                        <pre className="mt-2 text-xs bg-slate-100 p-3 rounded overflow-auto max-h-64">
                            {debugInfo}
                        </pre>
                    </details>
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
