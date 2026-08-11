export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  return backendRequest(event, `/accounts/${encodeURIComponent(getRouterParam(event, "id") || "")}/wechat-binding`, {
    method: "DELETE",
    body,
  })
})
