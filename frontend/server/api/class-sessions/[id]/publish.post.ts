export default defineEventHandler((event) =>
  backendRequest(event, `/class-sessions/${encodeURIComponent(getRouterParam(event, "id") || "")}/publish`, { method: "POST" }),
)
