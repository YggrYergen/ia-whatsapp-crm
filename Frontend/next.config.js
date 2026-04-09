// ================================================================================
// Next.js Configuration — with Sentry + OpenNext integration
//
// ⚠️ DO NOT add `disableClientInstrumentation: true` — it KILLS all client-side
//    Sentry error capture silently. This was the root cause of broken frontend
//    observability (discovered 2026-04-08).
//
// ⚠️ DO NOT downgrade Next.js below 15.x — the Sentry SDK v10 requires
//    `instrumentation-client.ts` which is a Next.js 15+ file convention.
//    See: .ai-context/implementation_plan.md for full rationale.
//
// ⚠️ DO NOT downgrade `lucide-react` below ^1.7.0 — older versions have
//    React 19 peer dep conflicts that fail the build.
//
// Sentry docs: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
// OpenNext docs: https://opennext.js.org/cloudflare/get-started#12-develop-locally
// Next.js 15 upgrade: https://nextjs.org/docs/app/building-your-application/upgrading/version-15
// ================================================================================
const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // With OpenNext, rewrites WORK (no longer static export).
  // These proxy frontend /api/* calls to the backend Cloud Run service.
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

// OpenNext: enable Cloudflare bindings during local development
// Per docs: https://opennext.js.org/cloudflare/get-started#12-develop-locally
const { initOpenNextCloudflareForDev } = require("@opennextjs/cloudflare");
initOpenNextCloudflareForDev();
