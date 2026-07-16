export default defineEventHandler((event) =>
  backendRequest(event, `/members/${encodeURIComponent(getRouterParam(event, "id") || "")}`),
)
