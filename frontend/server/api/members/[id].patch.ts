export default defineEventHandler(async (event) =>
  backendRequest(event, `/members/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
