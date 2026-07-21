export default defineEventHandler(async (event) =>
  backendRequest(event, `/courses/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
