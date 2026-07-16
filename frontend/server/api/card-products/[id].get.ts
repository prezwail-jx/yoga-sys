export default defineEventHandler((event) =>
  backendRequest(event, `/card-products/${encodeURIComponent(getRouterParam(event, "id") || "")}`),
)
