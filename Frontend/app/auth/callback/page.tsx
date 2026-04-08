'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase'

/**
 * Client-side auth callback page.
 * 
 * Supabase JS v2 uses PKCE flow by default. The code_verifier is stored
 * in the browser's localStorage, so the token exchange MUST happen
 * client-side (not in an edge function / route handler).
 * 
 * This page extracts the code from the URL, exchanges it for a session
 * using the browser's Supabase client, and redirects to the dashboard.
 */
export default function AuthCallbackPage() {
    const router = useRouter()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const handleCallback = async () => {
            const supabase = createClient()
            const url = new URL(window.location.href)
            const code = url.searchParams.get('code')
            const errorParam = url.searchParams.get('error')
            const errorDescription = url.searchParams.get('error_description')

            if (errorParam) {
                setError(errorDescription || errorParam)
                return
            }

            if (code) {
                try {
                    const { error } = await supabase.auth.exchangeCodeForSession(code)
                    if (error) {
                        console.error('Session exchange error:', error)
                        setError(error.message)
                        return
                    }
                    // Success — redirect to dashboard
                    router.replace('/dashboard')
                    return
                } catch (err: any) {
                    console.error('Auth callback error:', err)
                    setError(err?.message || 'Error desconocido durante la autenticación')
                    return
                }
            }

            // No code and no error — try getSession as fallback
            // (handles implicit flow or already-authenticated redirects)
            const { data: { session } } = await supabase.auth.getSession()
            if (session) {
                router.replace('/dashboard')
            } else {
                setError('No se recibió código de autenticación')
            }
        }

        handleCallback()
    }, [router])

    if (error) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
                    <h1 className="text-xl font-bold text-red-600 mb-4">Error de Autenticación</h1>
                    <p className="text-slate-600 mb-4">{error}</p>
                    <button
                        onClick={() => router.replace('/login')}
                        className="w-full py-2 px-4 bg-emerald-600 text-white rounded-md hover:bg-emerald-700 transition-colors"
                    >
                        Volver al Login
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center">
            <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto mb-4"></div>
                <p className="text-slate-600">Autenticando...</p>
            </div>
        </div>
    )
}
