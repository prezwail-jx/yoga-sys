export default defineEventHandler(async (event) =>
  backendRequest(event, `/coaches/${encodeURIComponent(getRouterParam(event, "id") || "")}`, {
    method: "PATCH",
    body: await readBody(event),
  }),
)
