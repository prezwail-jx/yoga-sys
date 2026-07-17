export default defineEventHandler(async (event) => backendRequest(event, "/writeoff/events", {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
