'use client'

import { createClient } from '@/lib/supabase'
import { useSearchParams } from 'next/navigation'
import { Suspense, useState } from 'react'
import { Vortex } from '@/components/ui/vortex'
import { CliText } from '@/components/ui/cli-text'
import * as Sentry from '@sentry/nextjs'

function LoginForm() {
    const supabase = createClient()
    const searchParams = useSearchParams()
    const error = searchParams.get('error')
    const [isLoading, setIsLoading] = useState(false)

    const handleGoogleLogin = async () => {
        setIsLoading(true)
        try {
            await supabase.auth.signInWithOAuth({
                provider: 'google',
                options: {
                    redirectTo: `${window.location.origin}/auth/confirm`,
                },
            })
        } catch (err) {
            console.error('[Login] Google OAuth error:', err)
            Sentry.captureException(err)
            setIsLoading(false)
        }
    }

    return (
        <div className="h-[100dvh] min-h-screen w-full overflow-hidden relative bg-[#06060e]">
            {/* Vortex Background — full viewport magnetic field simulation */}
            <div className="absolute inset-0 z-0">
                <Vortex
                    backgroundColor="#06060e"
                    particleCount={920}
                    baseHue={220}
                    rangeSpeed={1.5}
                    baseRadius={1}
                    rangeRadius={2}
                    containerClassName="w-full h-full"
                />
            </div>

            {/* Glassmorphic Login Card — centered */}
            <div className="absolute inset-0 z-20 flex items-center justify-center px-4">
                <div className="w-full max-w-[340px] flex flex-col items-center gap-5">

                    {/* CLI Animated Text — Pre-Suasion primer above the card */}
                    <CliText />

                    {/* Card */}
                    <div
                        className="w-full rounded-2xl p-6 space-y-5"
                        style={{
                            background: 'rgba(255,255,255,0.03)',
                            backdropFilter: 'blur(40px) saturate(130%)',
                            WebkitBackdropFilter: 'blur(40px) saturate(130%)',
                            border: '1px solid rgba(255,255,255,0.06)',
                            boxShadow: '0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
                        }}
                    >
                        {/* Error message */}
                        {error && (
                            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                                <p className="text-[11px] font-bold text-red-400">Error de Autenticación</p>
                                <p className="text-[10px] text-red-300/60 mt-0.5 break-all">{error}</p>
                            </div>
                        )}

                        {/* Google Sign-In Button */}
                        <button
                            onClick={handleGoogleLogin}
                            disabled={isLoading}
                            className="group w-full flex items-center justify-center gap-3 py-3.5 px-4 rounded-xl text-sm font-semibold text-white/90 transition-all duration-300 disabled:opacity-40 relative overflow-hidden"
                            style={{
                                background: 'rgba(255,255,255,0.05)',
                                border: '1px solid rgba(255,255,255,0.08)',
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(255,255,255,0.09)';
                                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)';
                                e.currentTarget.style.boxShadow = '0 0 20px rgba(99,102,241,0.1)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
                                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                                e.currentTarget.style.boxShadow = 'none';
                            }}
                        >
                            {isLoading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <svg className="w-[18px] h-[18px] flex-shrink-0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                </svg>
                            )}
                            {isLoading ? 'Conectando...' : 'Continuar con Google'}
                        </button>

                        {/* Divider line */}
                        <div className="h-px bg-gradient-to-r from-transparent via-white/[0.06] to-transparent" />

                        {/* Footer text */}
                        <p className="text-[10px] text-white/15 text-center font-medium leading-relaxed">
                            Al continuar, aceptas los{' '}
                            <a href="https://www.tuasistentevirtual.cl/terminos" target="_blank" rel="noopener noreferrer" className="underline hover:text-white/30 transition-colors">términos de servicio</a>
                            {' '}y la{' '}
                            <a href="https://www.tuasistentevirtual.cl/privacidad" target="_blank" rel="noopener noreferrer" className="underline hover:text-white/30 transition-colors">política de privacidad</a>
                        </p>
                    </div>

                    {/* Bottom badge */}
                    <div className="flex items-center gap-1.5 opacity-20">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400/80" />
                        <span className="text-[10px] text-white/60 font-medium">Protegido con cifrado de extremo a extremo</span>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="h-[100dvh] min-h-screen bg-[#06060e] flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
        }>
            <LoginForm />
        </Suspense>
    )
}
