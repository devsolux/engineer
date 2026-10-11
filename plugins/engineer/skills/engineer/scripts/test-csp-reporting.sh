#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cp "$ROOT/templates/security/csp-reporting.ts" "$TMP/csp-reporting.ts"
cat >"$TMP/test.ts" <<'TS'
import { cspReportingHeaders, createCspReportHandler, parseCspReports } from "./csp-reporting";

const modern = parseCspReports([{
  type: "csp-violation",
  body: {
    documentURL: "https://app.example/account?token=secret#private",
    blockedURL: "https://cdn.example/x.js?key=secret",
    effectiveDirective: "script-src-elem",
    disposition: "report",
    statusCode: 200,
    sample: "never persist me",
    sourceFile: "https://app.example/private.ts",
    originalPolicy: "raw policy",
  },
}], "https://app.example");
if (JSON.stringify(modern) !== JSON.stringify([{
  documentOrigin: "https://app.example",
  blockedOrigin: "https://cdn.example",
  effectiveDirective: "script-src-elem",
  disposition: "report",
  statusCode: 200,
}])) throw new Error("modern report was not privacy-normalized");

const legacy = parseCspReports({ "csp-report": {
  "document-uri": "https://app.example/",
  "blocked-uri": "inline",
  "violated-directive": "style-src-attr",
  disposition: "enforce",
  "status-code": 200,
}}, "https://app.example");
if (legacy.length !== 1 || legacy[0]?.blockedOrigin !== "inline") throw new Error("legacy report rejected");

if (parseCspReports([{ type: "csp-violation", body: {
  documentURL: "https://poison.example/", blockedURL: "https://cdn.example/x", effectiveDirective: "script-src",
}}], "https://app.example").length !== 0) throw new Error("foreign-origin poison accepted");

const headers = cspReportingHeaders("https://app.example");
if (!headers["Reporting-Endpoints"].includes("https://app.example/api/csp-report")) throw new Error("endpoint header drift");
if (!headers.reportingDirectives.includes("report-uri") || !headers.reportingDirectives.includes("report-to")) throw new Error("compatibility directives missing");

async function handlerChecks() {
  let recorded = 0;
  const handler = createCspReportHandler({
    protectedOrigin: "https://app.example",
    maxBodyBytes: 64,
    allow: async () => true,
    record: async () => { recorded += 1; },
  });
  const oversized = await handler(new Request("https://app.example/api/csp-report", {
    method: "POST",
    headers: { "content-type": "application/reports+json" },
    body: "x".repeat(65),
  }));
  if (oversized.status !== 413 || recorded !== 0) throw new Error("chunked oversized body reached sink");
}
void handlerChecks();
TS

tsc --strict --target ES2022 --module commonjs --lib ES2022,DOM --outDir "$TMP/out" "$TMP/test.ts"
node "$TMP/out/test.js"
grep -q 'maxBodyBytes.*32_768' "$ROOT/templates/security/csp-reporting.ts"
grep -q 'Never echo or log raw payloads' "$ROOT/templates/security/csp-reporting.ts"
! grep -Eq 'userAgent|user-agent|request\.headers\.get\("cookie"\)|console\.(log|error)|request\.text\(' "$ROOT/templates/security/csp-reporting.ts"

echo "csp reporting fixtures passed"
