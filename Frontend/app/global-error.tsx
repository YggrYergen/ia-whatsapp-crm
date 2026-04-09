// ================================================================================
// Global Error Boundary for App Router (captures React render errors)
//
// Per Sentry docs: https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/#capture-react-render-errors
// Per Next.js docs: https://nextjs.org/docs/app/api-reference/file-conventions/error
//
// This file catches errors that occur anywhere in the App Router and
// reports them to Sentry. Without this file, React render errors may
// not be captured by Sentry.
//
// ⚠️ DO NOT REMOVE THIS FILE — it is required for Sentry error capture.
// ================================================================================
"use client";

import * as Sentry from "@sentry/nextjs";
import NextError from "next/error";
import { useEffect } from "react";

export default function GlobalError({
    error,
}: {
    error: Error & { digest?: string };
}) {
    useEffect(() => {
        Sentry.captureException(error);
    }, [error]);

    return (
        <html>
            <body>
                {/* `NextError` is the default Next.js error page component.
                    Its type definition requires a `statusCode` prop. However,
                    since the App Router does not expose status codes for errors,
                    we simply pass 0 to render a generic error message. */}
                <NextError statusCode={0} />
            </body>
        </html>
    );
}
