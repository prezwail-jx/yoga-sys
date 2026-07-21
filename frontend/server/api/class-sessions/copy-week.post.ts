export default defineEventHandler(async (event) =>
  backendRequest(event, "/class-sessions/copy-week", {
    method: "POST",
    body: await readBody(event),
    headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
  }),
)
