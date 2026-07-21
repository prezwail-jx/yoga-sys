export default defineEventHandler((event) =>
  backendRequest(event, `/coaches/${encodeURIComponent(getRouterParam(event, "id") || "")}`),
)
