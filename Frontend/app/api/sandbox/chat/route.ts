import { NextResponse } from 'next/server'
import * as Sentry from '@sentry/nextjs'

/**
 * Proxy for /api/sandbox/chat → Backend Cloud Run
 * 
 * This proxies requests from the Cloudflare Pages frontend
 * to the Cloud Run backend's /api/sandbox/chat endpoint.
 * 
 * ISOLATION: The backend endpoint uses the Responses API and
 * does NOT touch ProcessMessageUseCase or MetaGraphAPIClient.
 */
export async function POST(req: Request) {
  const _where = 'proxy:sandbox/chat'
  try {
    const body = await req.json()
    const baseUrl = process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-uc.a.run.app'

    const response = await fetch(`${baseUrl}/api/sandbox/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
      const text = await response.text()
      console.error(`[${_where}] Backend returned HTTP ${response.status}: ${text.slice(0, 200)}`)
      Sentry.captureMessage(`Sandbox proxy error: ${response.status} - ${text.slice(0, 200)}`, 'error')
      return NextResponse.json(
        { status: 'error', message: text },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error(`[${_where}] Proxy crashed:`, error)
    Sentry.captureException(error, { extra: { where: _where } })
    return NextResponse.json(
      { status: 'error', message: `Proxy fetch failed: ${error.message}` },
      { status: 500 }
    )
  }
}
