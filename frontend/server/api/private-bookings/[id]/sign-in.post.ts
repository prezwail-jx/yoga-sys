export default defineEventHandler(async (event) => backendRequest(event, `/private-bookings/${encodeURIComponent(getRouterParam(event, "id") || "")}/sign-in`, {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
