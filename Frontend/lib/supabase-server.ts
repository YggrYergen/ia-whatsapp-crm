import { createServerClient } from '@supabase/ssr'
import { type NextRequest, NextResponse } from 'next/server'

/**
 * Creates a Supabase server client for use in Route Handlers on Cloudflare Pages.
 * 
 * Uses request.cookies (NextRequest) instead of cookies() from next/headers,
 * since the latter is not supported on Cloudflare Pages edge runtime.
 * 
 * Based on official Supabase SSR docs:
 * https://supabase.com/docs/guides/auth/server-side/nextjs
 */
export function createServerSupabaseClient(request: NextRequest, response: NextResponse) {
    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://nemrjlimrnrusodivtoa.supabase.co',
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_VgBbGeISLGQy1GSXrS-Drg_IGBoVsyn',
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => {
                        request.cookies.set(name, value)
                    })
                    cookiesToSet.forEach(({ name, value, options }) => {
                        response.cookies.set(name, value, options)
                    })
                },
            },
        }
    )
}
