export default defineEventHandler(async (event) =>
  backendRequest(event, `/members/${encodeURIComponent(getRouterParam(event, "id") || "")}/account/reset-password`, {
    method: "POST",
    body: await readBody(event),
  }),
)
