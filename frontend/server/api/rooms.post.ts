export default defineEventHandler(async (event) =>
  backendRequest(event, "/rooms", { method: "POST", body: await readBody(event) }),
)
