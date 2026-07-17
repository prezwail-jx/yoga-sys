export default defineEventHandler(async (event) => {
  const memberId = getRouterParam(event, "id")
  const query = getQuery(event)
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value))
  }
  const suffix = params.size ? `?${params.toString()}` : ""
  return backendRequest(event, `/members/${memberId}/timeline${suffix}`)
})
