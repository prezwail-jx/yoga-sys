export default defineEventHandler(async (event) => backendRequest(event, "/transactions", {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
