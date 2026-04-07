import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export const runtime = 'edge';
export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
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
      const cookieStore = cookies()
      const supabase = createServerClient(
        supabaseUrl,
        supabaseAnonKey,
        {
          cookies: {
            get(name: string) {
              return cookieStore.get(name)?.value
            },
            set(name: string, value: string, options: CookieOptions) {
              try {
                cookieStore.set({ name, value, ...options })
              } catch (e) {
                console.warn("Cookie set warning (non-critical in GET):", e)
              }
            },
            remove(name: string, options: CookieOptions) {
              try {
                cookieStore.delete({ name, ...options })
              } catch (e) {}
            },
          },
        }
      )
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      if (!error) {
        return NextResponse.redirect(`${origin}${next}`)
      } else {
        console.error("Supabase exchange error:", error)
        return NextResponse.redirect(`${origin}/login?error=${encodeURIComponent(error.message)}`)
      }
    }

    return NextResponse.redirect(`${origin}/login?error=auth_callback_missing_code`)
  } catch (err: any) {
    console.error("Critical Auth Callback Failure:", err)
    // Fail-safe HTML response to prevent generic 500
    const failSafeHtml = `
      <!DOCTYPE html>
      <html>
        <head><title>Auth Error</title></head>
        <body style="font-family: sans-serif; padding: 2rem;">
          <h1 style="color: #e11d48;">Error de Autenticación</h1>
          <p>Ocurrió un error crítico durante el proceso de callback.</p>
          <div style="background: #f1f5f9; padding: 1rem; border-radius: 0.5rem; margin-top: 1rem;">
            <p><strong>Error:</strong> ${err?.message || "Error desconocido"}</p>
            <p><strong>Detalles:</strong> ${err?.name || "N/A"}</p>
          </div>
          <a href="/login" style="display: inline-block; margin-top: 1rem; padding: 0.5rem 1rem; background: #2563eb; color: white; text-decoration: none; border-radius: 0.25rem;">Volver al Login</a>
        </body>
      </html>
    `
    return new Response(failSafeHtml, { 
        status: 200, // Return 200 to ensure Cloudflare displays the content
        headers: { 'Content-Type': 'text/html; charset=utf-8' } 
    })
  }
}
