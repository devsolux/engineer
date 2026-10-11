/**
 * Next.js OpenTelemetry bootstrap (copy to app root or src/ as instrumentation.ts).
 * Requires: pnpm add @vercel/otel
 *
 * Docs: references/observability.md
 * Next loads instrumentation.ts once at server start (root or src/).
 *
 * IMPORTANT: Next may invoke register for more than one runtime. Only load
 * Node-specific SDKs when NEXT_RUNTIME === "nodejs". Edge must not import
 * Node-only OTel packages.
 */
export async function register() {
 if (process.env.NEXT_RUNTIME === "edge") {
 // Optional: edge-safe tracing only. Do not import NodeSDK here.
 return;
 }

 if (process.env.NEXT_RUNTIME && process.env.NEXT_RUNTIME !== "nodejs") {
 return;
 }

 const { registerOTel } = await import("@vercel/otel");
 registerOTel({
 serviceName: process.env.OTEL_SERVICE_NAME ?? "app",
 });
}

/**
 * Optional (Next 15+): report request errors to your tracker.
 * Keep PII scrubbing in Sentry beforeSend - see observability.md.
 */
// export async function onRequestError(err: unknown) {
// if (process.env.NEXT_RUNTIME !== "nodejs") return;
// const Sentry = await import("@sentry/nextjs");
// Sentry.captureException(err);
// }

/**
 * Span attribute conventions (set on custom spans / Sentry tags):
 * - app.user_id (hashed if PII policy requires)
 * - app.org_id
 * - app.route (route pattern, not full URL with ids if sensitive)
 * - app.action (server action name)
 * - app.job_id (background job)
 * - app.trace_kind (request | job | webhook)
 *
 * Correlate Sentry: set tag `trace_id` from active OTel span context.
 */
