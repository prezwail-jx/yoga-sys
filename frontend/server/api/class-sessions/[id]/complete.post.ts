export default defineEventHandler((event) =>
  backendRequest(event, `/class-sessions/${encodeURIComponent(getRouterParam(event, "id") || "")}/complete`, {
    method: "POST",
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
