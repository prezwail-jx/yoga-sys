export default defineEventHandler(async (event) => backendRequest(event, "/private-slots", {
  method: "POST",
  body: await readBody(event),
}))
