export default defineEventHandler(async (event) =>
  backendRequest(event, "/card-products", { method: "POST", body: await readBody(event) }),
)
