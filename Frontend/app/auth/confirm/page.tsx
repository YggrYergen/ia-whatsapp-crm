'use client'

import { createClient } from '@/lib/supabase'
import { useRouter, useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'

function ConfirmAuth() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const code = searchParams.get('code')
        const errorParam = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')

        if (errorParam) {
            router.replace(`/login?error=${encodeURIComponent(errorDescription || errorParam)}`)
            return
        }

        if (!code) {
            router.replace('/login')
            return
        }

        // Exchange the code for a session using the browser client.
        // The browser client (createBrowserClient from @supabase/ssr) has access
        // to the code_verifier stored in cookies via document.cookie.
        const supabase = createClient()
        supabase.auth.exchangeCodeForSession(code)
            .then(({ error: exchangeError }) => {
                if (exchangeError) {
                    console.error('PKCE exchange error:', exchangeError.message)
                    router.replace(`/login?error=${encodeURIComponent(exchangeError.message)}`)
                } else {
                    router.replace('/dashboard')
                }
            })
            .catch((err) => {
                console.error('PKCE exchange crash:', err)
                router.replace(`/login?error=${encodeURIComponent(err.message || 'Unknown error')}`)
            })
    }, [searchParams, router])

    if (error) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <div className="bg-white p-6 rounded-lg shadow max-w-md">
                    <p className="text-red-600 font-medium">Error de autenticación</p>
                    <p className="text-sm text-slate-600 mt-2">{error}</p>
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
