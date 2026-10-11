"use server";

export async function deleteAccount() {
  // no rate limit — should warn/fail
  await db.from("profiles").delete().eq("id", "x");
  return { ok: true };
}
