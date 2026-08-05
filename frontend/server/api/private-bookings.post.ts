export default defineEventHandler(async (event) => backendRequest(event, "/private-bookings", {
  method: "POST",
  body: await readBody(event),
  headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
