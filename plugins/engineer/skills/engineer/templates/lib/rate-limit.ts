/**
 * Rate-limit helper (copy to app lib/rate-limit.ts).
 * Pair with references/backend-api.md + references/enforcement.md scanner rules.
 *
 * Env: UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
 * Dev without Redis: fails open or use a memory limiter - pick explicitly.
 */
import "server-only";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

type Window = `${number} ${"s" | "m" | "h" | "d"}`;

const redis =
 process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
 ? Redis.fromEnv()
 : null;

/** Named limiters - keep keys stable for ops dashboards */
const limiters = new Map<string, Ratelimit>();

function getLimiter(name: string, max: number, window: Window): Ratelimit | null {
 if (!redis) return null;
 const key = `${name}:${max}:${window}`;
 let limiter = limiters.get(key);
 if (!limiter) {
 limiter = new Ratelimit({
 redis,
 limiter: Ratelimit.slidingWindow(max, window),
 prefix: `rl:${name}`,
 });
 limiters.set(key, limiter);
 }
 return limiter;
}

export type RateLimitResult =
 | { ok: true }
 | { ok: false; error: string; code: "RATE_LIMIT" };

/**
 * @param name - action name (e.g. create-project, checkout, auth-login)
 * @param id - user id or ip
 */
export async function rateLimit(
 name: string,
 id: string,
 opts: { max?: number; window?: Window } = {},
): Promise<RateLimitResult> {
 const max = opts.max ?? 10;
 const window = opts.window ?? "1 m";
 const limiter = getLimiter(name, max, window);

 // Explicit fail-open when Redis missing - document in prod runbook
 if (!limiter) {
 if (process.env.NODE_ENV === "production") {
 console.warn(`[rate-limit] Redis not configured; allowing ${name}`);
 }
 return { ok: true };
 }

 const { success } = await limiter.limit(`${name}:${id}`);
 if (!success) {
 return { ok: false, error: "Too many requests", code: "RATE_LIMIT" };
 }
 return { ok: true };
}

/** Use after getUser() in Server Actions */
export async function rateLimitUser(
 name: string,
 userId: string,
 opts?: { max?: number; window?: Window },
): Promise<RateLimitResult> {
 return rateLimit(name, userId, opts);
}
