import { NextResponse } from 'next/server'
import * as Sentry from '@sentry/nextjs'


export async function POST(req: Request) {
  try {
    const body = await req.json()
    const baseUrl = process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'
    
    const response = await fetch(`${baseUrl}/api/calendar/book`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
        const text = await response.text();
        Sentry.captureMessage(`Calendar book proxy error: ${response.status} - ${text}`, 'error')
        return NextResponse.json({ status: 'error', message: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Proxy Calendar Book Error:', error)
    Sentry.captureException(error)
    return NextResponse.json({ status: 'error', message: `Fetch failed: ${error.message}` }, { status: 500 })
  }
}
