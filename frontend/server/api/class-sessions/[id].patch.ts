export default defineEventHandler(async (event) =>
  backendRequest(event, `/class-sessions/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
