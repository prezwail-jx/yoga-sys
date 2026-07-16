type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE"

type ApiRequestOptions = {
  method?: HttpMethod
  body?: unknown
  headers?: Record<string, string>
  withIdempotency?: boolean
}

function createIdempotencyKey(): string {
  return crypto.randomUUID()
}

export function useApiClient() {
  const request = async <T>(path: string, options: ApiRequestOptions = {}): Promise<T> => {
    const headers: Record<string, string> = { ...(options.headers || {}) }
    if (options.withIdempotency) {
      headers["Idempotency-Key"] ||= createIdempotencyKey()
    }
    const result = await $fetch(`/api${path}`, {
      method: options.method || "GET",
      body: options.body as Record<string, unknown> | undefined,
      headers,
    })
    return result as T
  }

  return { request }
}
