// ================================================================================
// Next.js Configuration — with Sentry integration
//
// ⚠️ DO NOT add `disableClientInstrumentation: true` — it KILLS all client-side
//    Sentry error capture silently. This was the root cause of broken frontend
//    observability (discovered 2026-04-08).
//
// ⚠️ DO NOT downgrade Next.js below 15.x — the Sentry SDK v10 requires
//    `instrumentation-client.ts` which is a Next.js 15+ file convention.
//    See: .ai-context/implementation_plan.md for full rationale.
//
// Sentry docs: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
// Next.js 15 upgrade: https://nextjs.org/docs/app/building-your-application/upgrading/version-15
// ================================================================================
const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export for Cloudflare Pages
  // Rewrites below do NOT work in static export mode — they only work with a
  // Node.js server. The frontend uses direct fetch calls to the backend URL
  // configured via NEXT_PUBLIC_ env vars instead. Keeping rewrites here as
  // documentation of the intended proxy pattern for future migration to
  // server-rendered deployment (e.g., OpenNext).
  async rewrites() {
    return [
      {
        source: '/api/calendar/:path*',
        destination: `${process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'}/api/calendar/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL || 'https://ia-backend-prod-ftyhfnvyla-ew.a.run.app'}/api/:path*`,
      },
    ]
  },
}

module.exports = withSentryConfig(nextConfig, {
  // Sentry build options
  org: process.env.SENTRY_ORG || "",
  project: process.env.SENTRY_PROJECT || "",

  // Suppress Sentry debug output in production builds
  // Note: disableLogger is deprecated, using silent instead
  silent: !process.env.CI,

  // Hide source maps from the client bundle
  hideSourceMaps: true,
});

// Suppress the "missing instrumentation.ts" warning — we are a static export
// on Cloudflare Pages with no Node.js server runtime, so server-side Sentry
// instrumentation is not applicable.
// Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
process.env.SENTRY_SUPPRESS_INSTRUMENTATION_FILE_WARNING = "1";
