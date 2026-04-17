// ================================================================================
// Sentry Server-Side Instrumentation (Next.js 15+ file convention)
//
// This file handles server-side error capture on the Edge runtime (Cloudflare Workers).
// The client-side equivalent is `instrumentation-client.ts`.
//
// On Cloudflare Workers (via OpenNext), NEXT_RUNTIME will be 'edge'.
// We initialize Sentry for Edge runtime to capture server-side errors.
//
// Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/#create-initialization-config-files
// Ref: https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation
// ================================================================================
import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = "https://b5b7a769848286fcfcc7f367a970c34f@o4511179991416832.ingest.us.sentry.io/4511184254402560";

export async function register() {
  // On Cloudflare Workers (OpenNext), runtime is 'edge'
  // Initialize Sentry for server/edge error capture
  Sentry.init({
    dsn: SENTRY_DSN,
    tracesSampleRate: 1.0,
    environment: process.env.NODE_ENV || "production",
    debug: false,
  });
}

// Capture unhandled server-side request errors (Next.js 15+)
// Ref: https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation#onrequesterror-optional
export const onRequestError = Sentry.captureRequestError;
