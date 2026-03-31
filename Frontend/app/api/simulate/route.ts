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

        const baseUrl = process.env.BACKEND_URL || 'https://ia-backend-prod-645489345350.europe-west1.run.app'
        const webhookUrl = baseUrl.endsWith('/webhook') ? baseUrl : `${baseUrl}/webhook`

        const res = await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Failed to reach backend: HTTP ${res.status} - ${errText}`)
        }

        return NextResponse.json({ success: true })
    } catch (error: any) {
        console.error("Simulation Error:", error);
        return NextResponse.json({ success: false, error: error.message || 'Simulation failed' }, { status: 500 })
    }
}
