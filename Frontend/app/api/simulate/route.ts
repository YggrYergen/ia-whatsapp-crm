import { NextResponse } from 'next/server'

export const runtime = 'edge';

export async function POST(req: Request) {
    try {
        const { phone, message, tenantId } = await req.json()

        const payload = {
            object: "whatsapp_business_account",
            entry: [{
                changes: [{
                    value: {
                        metadata: {
                            phone_number_id: "123456789012345" // ID semilla
                        },
                        messages: [{
                            from: phone,
                            text: { body: message }
                        }]
                    }
                }]
            }]
        }

        const res = await fetch(process.env.BACKEND_URL || 'http://127.0.0.1:8000/webhook', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            throw new Error('Failed to reach backend')
        }

        return NextResponse.json({ success: true })
    } catch (error) {
        return NextResponse.json({ success: false, error: 'Simulation failed' }, { status: 500 })
    }
}
