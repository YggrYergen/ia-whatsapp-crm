import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export const runtime = 'edge';
export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const next = requestUrl.searchParams.get('next') ?? '/'
  const origin = requestUrl.origin

  try {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://nemrjlimrnrusodivtoa.supabase.co'
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'sb_publishable_VgBbGeISLGQy1GSXrS-Drg_IGBoVsyn'

    if (!supabaseUrl || !supabaseAnonKey) {
        throw new Error("Missing Supabase Environment Variables")
    }

    if (code) {
      // For Cloudflare Pages Edge Runtime, we must use request/response cookies
      // instead of next/headers cookies() which is not fully supported
      const response = NextResponse.redirect(`${origin}${next}`)

      const supabase = createServerClient(
        supabaseUrl,
        supabaseAnonKey,
        {
          cookies: {
            get(name: string) {
              return request.cookies.get(name)?.value
            },
            set(name: string, value: string, options: CookieOptions) {
              // Set on the response that will be returned
              response.cookies.set({ name, value, ...options })
            },
            remove(name: string, options: CookieOptions) {
              response.cookies.set({ name, value: '', ...options })
            },
          },
        }
      )

      const { error } = await supabase.auth.exchangeCodeForSession(code)
      if (!error) {
        return response
      } else {
        console.error("Supabase exchange error:", error)
        return NextResponse.redirect(`${origin}/login?error=${encodeURIComponent(error.message)}`)
      }
    }

    return NextResponse.redirect(`${origin}/login?error=auth_callback_missing_code`)
  } catch (err: any) {
    console.error("Critical Auth Callback Failure:", err)
    const failSafeHtml = `
      <!DOCTYPE html>
      <html>
        <head><title>Auth Error</title></head>
        <body style="font-family: sans-serif; padding: 2rem;">
          <h1 style="color: #e11d48;">Error de Autenticación</h1>
          <p>Ocurrió un error crítico durante el proceso de callback.</p>
          <div style="background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;">
            <p><strong>Error:</strong> ${err?.message || "Error desconocido"}</p>
          </div>
          <a href="/login" style="display: inline-block; margin-top: 1rem; padding: 0.5rem 1rem; background: #2563eb; color: white; text-decoration: none; border-radius: 0.25rem;">Volver al Login</a>
        </body>
      </html>
    `
    return new Response(failSafeHtml, { 
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8' } 
    })
  }
}
