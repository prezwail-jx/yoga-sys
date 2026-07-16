export default defineEventHandler((event) => {
  const query = getQuery(event)
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") search.set(key, String(value))
  }
  return backendRequest(event, `/members?${search}`)
})
