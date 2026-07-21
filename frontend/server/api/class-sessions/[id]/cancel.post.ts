export default defineEventHandler((event) =>
  backendRequest(event, `/class-sessions/${encodeURIComponent(getRouterParam(event, "id") || "")}/cancel`, {
    method: "POST",
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
