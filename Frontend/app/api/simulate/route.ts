import { NextResponse } from 'next/server'

export const runtime = 'edge';

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const baseUrl = process.env.BACKEND_URL || 'https://ia-backend-prod-645489345350.europe-west1.run.app'
    
    const response = await fetch(`${baseUrl}/api/simulate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    if (!response.ok) {
        const text = await response.text();
        return NextResponse.json({ status: 'error', message: text }, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('Proxy Simulation Error Trace:', error)
    return NextResponse.json({ status: 'error', message: `Fetch failed: ${error.message}` }, { status: 500 })
  }
}
