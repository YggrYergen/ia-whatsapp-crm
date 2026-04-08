import { NextResponse } from 'next/server'

export const runtime = 'edge';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const start_iso = searchParams.get('start_iso')
    const end_iso = searchParams.get('end_iso')
    const baseUrl = process.env.BACKEND_URL || 'https://ia-backend-prod-645489345350.europe-west1.run.app'
    
    const response = await fetch(`${baseUrl}/api/calendar/events?start_iso=${start_iso}&end_iso=${end_iso}`)
    
    if (!response.ok) {
        const text = await response.text();
        return NextResponse.json({ status: 'error', message: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Proxy Calendar Events Error:', error)
    return NextResponse.json({ status: 'error', message: `Fetch failed: ${error.message}` }, { status: 500 })
  }
}
