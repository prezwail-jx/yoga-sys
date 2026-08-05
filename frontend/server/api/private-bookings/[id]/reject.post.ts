export default defineEventHandler(async (event) => backendRequest(event, `/private-bookings/${encodeURIComponent(getRouterParam(event, "id") || "")}/reject`, {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
