export default defineEventHandler((event) => backendRequest(event, `/private-bookings/${encodeURIComponent(getRouterParam(event, "id") || "")}/confirm`, {
  method: "POST",
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
