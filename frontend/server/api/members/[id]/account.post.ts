export default defineEventHandler(async (event) =>
  backendRequest(event, `/members/${encodeURIComponent(getRouterParam(event, "id") || "")}/account`, {
    method: "POST",
    body: await readBody(event),
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
