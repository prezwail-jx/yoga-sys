export default defineEventHandler(async (event) => backendRequest(event, `/private-slots/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
  method: "PATCH",
  body: await readBody(event),
}))
