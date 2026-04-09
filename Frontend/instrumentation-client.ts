// ================================================================================
// Sentry Client-Side Instrumentation (Next.js 15+ file convention)
//
// ⚠️ DO NOT RENAME OR MOVE THIS FILE.
// ⚠️ DO NOT CREATE a `sentry.client.config.ts` — that file is DEPRECATED.
// ⚠️ DO NOT add `disableClientInstrumentation: true` to next.config.js — it
//    KILLS all client-side error capture silently.
//
// This file replaces the deprecated `sentry.client.config.ts`.
// Per Sentry docs: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/
// Per Next.js docs: https://nextjs.org/docs/app/api-reference/file-conventions/instrumentation-client
//
// This runs in the browser. For static exports (Cloudflare Pages),
// this is the ONLY Sentry config that matters — no server runtime.
//
// NEXT_PUBLIC_SENTRY_DSN must be available at BUILD TIME
// (set in wrangler.toml or Cloudflare Pages environment variables)
//
// History:
// - 2026-04-08: Created as part of Next.js 14→15 upgrade to fix broken
//   Sentry frontend integration. The old sentry.client.config.ts was
//   deprecated by Sentry SDK v10 and disableClientInstrumentation was
//   silently preventing ALL client-side error capture.
// ================================================================================
import * as Sentry from "@sentry/nextjs";

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || "",

    // Per docs: sendDefaultPii attaches request headers and IP for users
    sendDefaultPii: true,

    // 1.0 during stabilization to capture 100% of traces
    // Reduce to 0.1 after go-live
    // Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/configuration/sampling/
    tracesSampleRate: 1.0,

    // Session Replay: record 0% of normal sessions, 100% of error sessions
    // Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/session-replay/
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: 1.0,

    // Enable structured logs (NEW feature in Sentry SDK v10)
    // Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/logs/
    enableLogs: true,

    environment: process.env.NODE_ENV || "development",

    debug: false,

    integrations: [
        Sentry.replayIntegration(),
    ],
});

// Per Sentry build warning: required to instrument App Router navigations
// Ref: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/#tracing
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
