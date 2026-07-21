export default defineEventHandler((event) =>
  backendRequest(event, `/class-bookings/${encodeURIComponent(getRouterParam(event, "id") || "")}/check-in`, {
    method: "POST",
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
