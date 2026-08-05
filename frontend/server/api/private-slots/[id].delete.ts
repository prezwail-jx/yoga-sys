export default defineEventHandler((event) => backendRequest(event, `/private-slots/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
  method: "DELETE",
}))
