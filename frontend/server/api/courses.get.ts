export default defineEventHandler((event) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(getQuery(event))) {
    if (value !== undefined && value !== "") search.set(key, String(value))
  }
  return backendRequest(event, `/courses?${search}`)
})
