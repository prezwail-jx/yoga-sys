import type { MiniProgramRuntime, SafeLogManager } from "../platform/runtime"

export type ApiErrorKind = "authentication" | "authorization" | "conflict" | "validation" | "server" | "network" | "timeout"

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: ApiErrorKind,
    readonly statusCode: number | null,
    readonly traceId: string,
    readonly detail?: unknown,
  ) {
    super(message)
    this.name = "ApiError"
  }

  get uncertain(): boolean {
    return this.kind === "network" || this.kind === "timeout"
  }
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"
  body?: unknown
  authenticated?: boolean
  idempotencyKey?: string
  timeoutMs?: number
}

function randomId(): string {
  const random = Math.random().toString(16).slice(2)
  return `mp-${Date.now().toString(16)}-${random}`
}

function errorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback
  const body = data as Record<string, unknown>
  if (typeof body.errorDescription === "string") return body.errorDescription
  if (typeof body.detail === "string") return body.detail
  if (typeof body.error === "string") return body.error
  return fallback
}

function kindForStatus(statusCode: number): ApiErrorKind {
  if (statusCode === 401) return "authentication"
  if (statusCode === 403) return "authorization"
  if (statusCode === 409 || statusCode === 410 || statusCode === 429) return "conflict"
  if (statusCode === 400 || statusCode === 422) return "validation"
  return "server"
}

export class ApiClient {
  private readonly logger: SafeLogManager

  constructor(
    private readonly runtime: MiniProgramRuntime,
    private readonly baseUrl: string,
    private readonly token: () => string | null,
    private readonly onUnauthorized: () => void,
  ) {
    this.logger = runtime.getLogManager?.({ level: 1 }) ?? {
      info: () => undefined,
      warn: () => undefined,
      error: () => undefined,
    }
  }

  request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const method = options.method ?? "GET"
    const traceId = randomId()
    const header: Record<string, string> = {
      "Content-Type": "application/json",
      "X-Trace-Id": traceId,
    }
    const token = options.authenticated === false ? null : this.token()
    if (token) header.Authorization = `Bearer ${token}`
    if (options.idempotencyKey) header["Idempotency-Key"] = options.idempotencyKey

    return new Promise<T>((resolve, reject) => {
      this.runtime.request<T>({
        url: `${this.baseUrl}${path}`,
        method,
        data: options.body,
        header,
        timeout: options.timeoutMs ?? 10_000,
        success: (response) => {
          const responseTrace = response.header["x-trace-id"] ?? response.header["X-Trace-Id"] ?? traceId
          this.logger.info("api.response", { method, path, statusCode: response.statusCode, traceId: responseTrace })
          if (response.statusCode >= 200 && response.statusCode < 300) {
            resolve(response.data)
            return
          }
          if (response.statusCode === 401) this.onUnauthorized()
          reject(new ApiError(
            errorMessage(response.data, `Request failed with status ${response.statusCode}`),
            kindForStatus(response.statusCode),
            response.statusCode,
            responseTrace,
            response.data,
          ))
        },
        fail: (failure) => {
          const timeout = failure.errMsg.toLowerCase().includes("timeout")
          this.logger.warn("api.transport_failure", { method, path, traceId, timeout, errno: failure.errno })
          reject(new ApiError(
            timeout ? "Request timed out" : "Network request failed",
            timeout ? "timeout" : "network",
            null,
            traceId,
          ))
        },
      })
    })
  }
}
