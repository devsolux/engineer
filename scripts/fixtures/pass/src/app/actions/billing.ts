"use server";

import { isRateLimited } from "@/lib/rate-limit";

export async function createCheckout() {
  if (await isRateLimited("user", "checkout")) {
    throw new Error("rate limited");
  }
  // mutate...
  return { ok: true };
}
