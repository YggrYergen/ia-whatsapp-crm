import { NextResponse, type NextRequest } from 'next/server'
import { createServerSupabaseClient } from '@/lib/supabase-server'

export const runtime = 'edge'

/**
 * Auth callback route handler for Supabase OAuth with PKCE flow.
 * 
 * This runs server-side and has access to cookies where @supabase/ssr
 * stored the PKCE code_verifier. It exchanges the auth code for a session
 * and sets session cookies on the response.
 * 
 * Compatible with Cloudflare Pages edge runtime (uses NextRequest/NextResponse
 * cookies instead of cookies() from next/headers).
 */
export async function GET(request: NextRequest) {
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

        // Create server client that reads/writes cookies via request/response
        const supabase = createServerSupabaseClient(request, response)

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
}
