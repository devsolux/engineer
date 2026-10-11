export type CspDisposition = "enforce" | "report" | "unknown";

export type CspViolation = {
  documentOrigin: string;
  blockedOrigin: string;
  effectiveDirective: string;
  disposition: CspDisposition;
  statusCode: number | null;
};

export type CspReportHandlerOptions = {
  protectedOrigin: string;
  allow: (request: Request) => Promise<boolean>;
  record: (violations: readonly CspViolation[]) => Promise<void>;
  maxBodyBytes?: number;
  maxReports?: number;
};

const CONTENT_TYPES = new Set([
  "application/csp-report",
  "application/json",
  "application/reports+json",
]);

function boundedString(value: unknown, max = 256): string | null {
  return typeof value === "string" && value.length > 0 && value.length <= max ? value : null;
}

function originOnly(value: unknown): string | null {
  const text = boundedString(value, 2048);
  if (!text) return null;
  if (["inline", "eval", "self"].includes(text)) return text;
  if (text.startsWith("data:")) return "data:";
  if (text.startsWith("blob:")) return "blob:";
  try {
    const url = new URL(text);
    return url.protocol === "http:" || url.protocol === "https:" ? url.origin : null;
  } catch {
    return null;
  }
}

function directiveOnly(value: unknown): string | null {
  const text = boundedString(value, 96)?.toLowerCase();
  return text && /^[a-z][a-z0-9-]*$/.test(text) ? text : null;
}

function statusOnly(value: unknown): number | null {
  return Number.isInteger(value) && Number(value) >= 100 && Number(value) <= 599
    ? Number(value)
    : null;
}

function dispositionOnly(value: unknown): CspDisposition {
  return value === "enforce" || value === "report" ? value : "unknown";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

async function readBoundedBody(request: Request, maxBytes: number): Promise<string | null> {
  if (!request.body) return "";
  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > maxBytes) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  const body = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder("utf-8", { fatal: true }).decode(body);
}

function normalize(body: Record<string, unknown>, protectedOrigin: string): CspViolation | null {
  const documentOrigin = originOnly(body.documentURL ?? body["document-uri"]);
  const blockedOrigin = originOnly(body.blockedURL ?? body["blocked-uri"]);
  const effectiveDirective = directiveOnly(
    body.effectiveDirective ?? body["effective-directive"] ?? body["violated-directive"],
  );
  if (documentOrigin !== protectedOrigin || !blockedOrigin || !effectiveDirective) return null;
  return {
    documentOrigin,
    blockedOrigin,
    effectiveDirective,
    disposition: dispositionOnly(body.disposition),
    statusCode: statusOnly(body.statusCode ?? body["status-code"]),
  };
}

export function parseCspReports(
  payload: unknown,
  protectedOrigin: string,
  maxReports = 20,
): CspViolation[] {
  const canonicalOrigin = new URL(protectedOrigin).origin;
  const top = asRecord(payload);
  const legacy = asRecord(top?.["csp-report"]);
  const reports = legacy ? [legacy] : Array.isArray(payload) ? payload.slice(0, maxReports) : [];
  const normalized: CspViolation[] = [];
  for (const report of reports) {
    const envelope = asRecord(report);
    if (!envelope || (envelope.type !== undefined && envelope.type !== "csp-violation")) continue;
    const body = asRecord(envelope.body) ?? envelope;
    const violation = normalize(body, canonicalOrigin);
    if (violation) normalized.push(violation);
  }
  return normalized;
}

export function createCspReportHandler(options: CspReportHandlerOptions) {
  const maxBodyBytes = options.maxBodyBytes ?? 32_768;
  const maxReports = options.maxReports ?? 20;
  if (!Number.isInteger(maxBodyBytes) || maxBodyBytes < 1 || maxBodyBytes > 1_048_576) {
    throw new Error("maxBodyBytes must be an integer between 1 and 1048576");
  }
  if (!Number.isInteger(maxReports) || maxReports < 1 || maxReports > 100) {
    throw new Error("maxReports must be an integer between 1 and 100");
  }
  return async function POST(request: Request): Promise<Response> {
    const contentType = request.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
    const lengthHeader = request.headers.get("content-length");
    if (lengthHeader !== null && !/^\d+$/.test(lengthHeader)) return new Response(null, { status: 400 });
    const declaredLength = Number(lengthHeader ?? 0);
    if (!contentType || !CONTENT_TYPES.has(contentType)) return new Response(null, { status: 415 });
    if (Number.isFinite(declaredLength) && declaredLength > maxBodyBytes) {
      return new Response(null, { status: 413 });
    }
    try {
      if (!(await options.allow(request))) return new Response(null, { status: 204 });
    } catch {
      return new Response(null, { status: 204 });
    }

    try {
      const text = await readBoundedBody(request, maxBodyBytes);
      if (text === null) return new Response(null, { status: 413 });
      const violations = parseCspReports(JSON.parse(text), options.protectedOrigin, maxReports);
      if (violations.length > 0) await options.record(violations);
    } catch {
      // Reports are untrusted, best-effort telemetry. Never echo or log raw payloads.
    }
    return new Response(null, { status: 204 });
  };
}

export function cspReportingHeaders(origin: string, endpointPath = "/api/csp-report") {
  const endpoint = new URL(endpointPath, origin).toString();
  return {
    "Reporting-Endpoints": `csp-endpoint="${endpoint}"`,
    reportingDirectives: `report-uri ${endpoint}; report-to csp-endpoint`,
  } as const;
}
