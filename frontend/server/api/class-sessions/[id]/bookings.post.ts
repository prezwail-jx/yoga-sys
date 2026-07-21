export default defineEventHandler(async (event) =>
  backendRequest(event, `/class-sessions/${encodeURIComponent(getRouterParam(event, "id") || "")}/bookings`, {
    method: "POST",
    body: await readBody(event),
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
