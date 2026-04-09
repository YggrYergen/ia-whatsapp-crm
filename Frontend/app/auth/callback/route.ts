import { NextResponse, type NextRequest } from 'next/server'

/**
 * Auth callback route handler for Supabase OAuth with PKCE flow.
 *
 * Strategy: Instead of trying to do the PKCE exchange server-side,
 * we redirect to a client-side page that handles the exchange using
 * the browser Supabase client. The browser client has access to both:
 * - The auth code (from the URL)
 * - The code_verifier (stored by @supabase/ssr in cookies accessible
 *   to the browser client via document.cookie)
 *
 * This approach works on Cloudflare Workers (via OpenNext) without
 * needing server-side cookie access for the PKCE exchange.
 */
export async function GET(request: NextRequest) {
    const url = new URL(request.url)
    // Pass all query params to the client-side handler
    const clientUrl = new URL('/auth/confirm', url.origin)
    clientUrl.search = url.search
    return NextResponse.redirect(clientUrl)
}

