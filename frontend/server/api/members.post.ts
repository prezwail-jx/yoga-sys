export default defineEventHandler(async (event) =>
  backendRequest(event, "/members", { method: "POST", body: await readBody(event) }),
)
