export default defineEventHandler(async (event) =>
  backendRequest(event, "/coaches", { method: "POST", body: await readBody(event) }),
)
