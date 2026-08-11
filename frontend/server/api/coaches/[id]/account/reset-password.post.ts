export default defineEventHandler(async (event) =>
  backendRequest(event, `/coaches/${encodeURIComponent(getRouterParam(event, "id") || "")}/account/reset-password`, {
    method: "POST",
    body: await readBody(event),
  }),
)
