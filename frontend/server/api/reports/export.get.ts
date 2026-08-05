export default defineEventHandler((event) => {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(getQuery(event))) {
    if (value !== undefined && value !== "") search.set(key, String(value))
  }
  const config = useRuntimeConfig(event)
  const token = getCookie(event, "yoga_token")
  if (!token) throw createError({ statusCode: 401, statusMessage: "请先登录" })
  return $fetch.raw<ArrayBuffer>(`${config.backendBaseUrl}/reports/export?${search}`, {
    responseType: "arrayBuffer",
    headers: { Authorization: `Bearer ${token}` },
  }).then((response) => {
    setHeader(event, "Content-Type", response.headers.get("content-type") || "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    const disposition = response.headers.get("content-disposition")
    if (disposition) setHeader(event, "Content-Disposition", disposition)
    return response._data
  })
})
