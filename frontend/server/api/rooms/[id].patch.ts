export default defineEventHandler(async (event) =>
  backendRequest(event, `/rooms/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
