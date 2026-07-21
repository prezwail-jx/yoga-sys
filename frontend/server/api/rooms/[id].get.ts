export default defineEventHandler((event) =>
  backendRequest(event, `/rooms/${encodeURIComponent(getRouterParam(event, "id") || "")}`),
)
