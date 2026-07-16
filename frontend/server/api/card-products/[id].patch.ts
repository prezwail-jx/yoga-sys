export default defineEventHandler(async (event) =>
  backendRequest(event, `/card-products/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
