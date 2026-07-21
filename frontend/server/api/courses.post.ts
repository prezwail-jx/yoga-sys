export default defineEventHandler(async (event) =>
  backendRequest(event, "/courses", { method: "POST", body: await readBody(event) }),
)
