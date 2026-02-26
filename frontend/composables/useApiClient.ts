type HttpMethod = "GET" | "POST" | "PATCH" | "PUT" | "DELETE"

type ApiRequestOptions = {
  method?: HttpMethod
  body?: unknown
  headers?: Record<string, string>
  withIdempotency?: boolean
}

function createIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export function useApiClient() {
  const request = async <T>(path: string, options: ApiRequestOptions = {}): Promise<T> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    }

    if (options.withIdempotency) {
      headers["Idempotency-Key"] = headers["Idempotency-Key"] || createIdempotencyKey()
    }

    return await $fetch<T>(`/api${path}`, {
      method: options.method || "GET",
      body: options.body,
      headers,
    })
  }

  return { request }
}
