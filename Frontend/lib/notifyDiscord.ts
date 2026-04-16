'use client'

/**
 * notifyDiscord — Fire-and-forget Discord webhook alert from the frontend.
 *
 * Rule 5 compliance: Every error handler reports to 3 channels:
 *   1. console.error (logger)
 *   2. Sentry.captureException/captureMessage (error tracking)
 *   3. This function (Discord notification)
 *
 * Uses the same NEXT_PUBLIC_DISCORD_WEBHOOK_URL env var.
 * Non-fatal: swallows all errors silently (errors in error-reporting
 * should NEVER crash the app).
 *
 * Usage:
 *   notifyDiscord('🔴 Config Save Failed', `tenant=${tenantId}\nerr=${error.message}`, 'error')
 */

type Severity = 'error' | 'warning' | 'info'

const COLOR_MAP: Record<Severity, number> = {
  error: 16711680,   // Red
  warning: 16776960, // Yellow
  info: 3447003,     // Blue
}

const IS_PRODUCTION = typeof window !== 'undefined' && window.location.hostname === 'ohno.tuasistentevirtual.cl'
const ENV_PREFIX = IS_PRODUCTION ? '' : '[🔧 DEV] '
const ENV_LABEL = IS_PRODUCTION ? 'production' : 'desarrollo'

export function notifyDiscord(
  title: string,
  description: string,
  severity: Severity = 'error'
): void {
  const webhookUrl = process.env.NEXT_PUBLIC_DISCORD_WEBHOOK_URL
  if (!webhookUrl) {
    console.warn('[notifyDiscord] NEXT_PUBLIC_DISCORD_WEBHOOK_URL not set — skipping')
    return
  }

  // Fire-and-forget — don't await, don't block UI
  fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      embeds: [{
        title: `${ENV_PREFIX}${title}`,
        description: description.slice(0, 2000), // Discord field limit
        color: COLOR_MAP[severity] ?? COLOR_MAP.error,
        fields: [
          { name: '🌍 Environment', value: `\`${ENV_LABEL}\``, inline: true },
          { name: '📍 Source', value: '`Frontend`', inline: true },
        ],
        timestamp: new Date().toISOString(),
      }],
    }),
  }).catch(() => {
    // Swallow — errors in error-reporting must not crash the app
  })
}
