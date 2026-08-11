export default defineEventHandler((event) =>
  backendRequest(event, `/accounts/${encodeURIComponent(getRouterParam(event, "id") || "")}/wechat-binding`),
)
