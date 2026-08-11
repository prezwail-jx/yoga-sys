import type { H3Event } from "h3"

type BackendOptions = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"
  body?: unknown
  auth?: boolean
  headers?: Record<string, string>
}

type BackendError = {
  statusCode?: number
  data?: { detail?: string }
  response?: { status?: number; _data?: { detail?: string }; headers?: Headers }
}

export async function backendRequest<T>(event: H3Event, path: string, options: BackendOptions = {}): Promise<T> {
  const config = useRuntimeConfig(event)
  const token = getCookie(event, "yoga_token")
  if (options.auth !== false && !token) throw createError({ statusCode: 401, statusMessage: "请先登录" })
  try {
    const result = await $fetch(`${config.backendBaseUrl}${path}`, {
      method: options.method || "GET",
      body: options.body as Record<string, unknown> | undefined,
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
    })
    return result as T
  } catch (error: unknown) {
    const backendError = error as BackendError
    const statusCode = backendError.response?.status || backendError.statusCode || 502
    const detail = backendError.response?._data?.detail || backendError.data?.detail || "后端服务不可用"
    const traceId = backendError.response?.headers?.get("x-trace-id") || undefined
    throw createError({
      statusCode,
      statusMessage: detail,
      data: { ...(backendError.response?._data || {}), ...(traceId ? { traceId } : {}) },
    })
  }
}
