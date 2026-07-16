export default defineEventHandler(async (event) => backendRequest(event, `/member-cards/${encodeURIComponent(getRouterParam(event, "id") || "")}/unfreeze`, {
  method: "POST", body: await readBody(event), headers: { "Idempotency-Key": getHeader(event, "idempotency-key") || "" },
}))
