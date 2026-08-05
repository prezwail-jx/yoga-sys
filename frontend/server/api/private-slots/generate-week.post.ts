export default defineEventHandler(async (event) => backendRequest(event, "/private-slots/generate-week", {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
