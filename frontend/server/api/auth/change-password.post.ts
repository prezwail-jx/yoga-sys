export default defineEventHandler(async (event) =>
  backendRequest(event, "/auth/change-password", { method: "POST", body: await readBody(event) }),
)
