export async function POST() {
  // createCheckout session without rate limit
  return Response.json({ ok: true });
}
