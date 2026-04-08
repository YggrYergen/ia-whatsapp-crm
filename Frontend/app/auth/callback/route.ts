import { NextResponse, type NextRequest } from 'next/server'
import { createServerClient } from '@supabase/ssr'

export const runtime = 'edge'

/**
 * Auth callback route handler for Supabase OAuth with PKCE flow.
 *
 * Creates the Supabase server client inline (instead of importing) to minimize
 * potential module resolution issues on Cloudflare Pages edge runtime.
 *
 * Uses NextRequest/NextResponse cookies (NOT cookies() from next/headers)
 * for CF Pages compatibility.
 */
export async function GET(request: NextRequest) {
    try {
        const requestUrl = new URL(request.url)
        const code = requestUrl.searchParams.get('code')
        const errorParam = requestUrl.searchParams.get('error')
        const errorDescription = requestUrl.searchParams.get('error_description')

        // Handle OAuth errors from provider
        if (errorParam) {
            const loginUrl = new URL('/login', requestUrl.origin)
            loginUrl.searchParams.set('error', errorDescription || errorParam)
            return NextResponse.redirect(loginUrl)
        }

        if (code) {
            // Build the redirect response FIRST so we can set cookies on it
            const redirectUrl = new URL('/dashboard', requestUrl.origin)
            const response = NextResponse.redirect(redirectUrl)

            // Create server client inline with cookie handlers
            const supabase = createServerClient(
                process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://nemrjlimrnrusodivtoa.supabase.co',
                process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_VgBbGeISLGQy1GSXrS-Drg_IGBoVsyn',
                {
                    cookies: {
                        getAll() {
                            return request.cookies.getAll()
                        },
                        setAll(cookiesToSet) {
                            cookiesToSet.forEach(({ name, value }) => {
                                request.cookies.set(name, value)
                            })
                            cookiesToSet.forEach(({ name, value, options }) => {
                                response.cookies.set(name, value, options)
                            })
                        },
                    },
                }
            )

            const { error } = await supabase.auth.exchangeCodeForSession(code)

            if (!error) {
                // Session cookies are already set on response by the server client
                return response
            }

            // Exchange failed — redirect to login with error
            console.error('Auth code exchange failed:', error.message)
            const loginUrl = new URL('/login', requestUrl.origin)
            loginUrl.searchParams.set('error', error.message)
            return NextResponse.redirect(loginUrl)
        }

        // No code provided — redirect to login
        return NextResponse.redirect(new URL('/login', requestUrl.origin))
    } catch (err: unknown) {
        // Catch-all: return the actual error message for debugging
        const message = err instanceof Error ? err.message : String(err)
        const stack = err instanceof Error ? err.stack : ''
        console.error('Auth callback crashed:', message, stack)

        // In production, redirect to login with the error message visible
        const requestUrl = new URL(request.url)
        const loginUrl = new URL('/login', requestUrl.origin)
        loginUrl.searchParams.set('error', `Callback error: ${message}`)
        return NextResponse.redirect(loginUrl)
    }
}
