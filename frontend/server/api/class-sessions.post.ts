export default defineEventHandler(async (event) =>
  backendRequest(event, "/class-sessions", { method: "POST", body: await readBody(event) }),
)
