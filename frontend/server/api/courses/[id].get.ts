export default defineEventHandler((event) =>
  backendRequest(event, `/courses/${encodeURIComponent(getRouterParam(event, "id") || "")}`),
)
