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
  bearerToken?: string
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
    const token = options.authenticated === false ? null : options.bearerToken ?? this.token()
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

  downloadAndOpen(path: string, fileType = "xlsx"): Promise<void> {
    const token = this.token()
    const traceId = randomId()
    if (!token) return Promise.reject(new ApiError("登录已失效，请重新登录", "authentication", 401, traceId))
    return new Promise<void>((resolve, reject) => {
      this.runtime.downloadFile({
        url: `${this.baseUrl}${path}`,
        header: { Authorization: `Bearer ${token}`, "X-Trace-Id": traceId },
        timeout: 30_000,
        success: (result) => {
          this.logger.info("api.download", { path, statusCode: result.statusCode, traceId })
          if (result.statusCode < 200 || result.statusCode >= 300) {
            if (result.statusCode === 401) this.onUnauthorized()
            reject(new ApiError(`报表下载失败（状态码 ${result.statusCode}）`, kindForStatus(result.statusCode), result.statusCode, traceId))
            return
          }
          if (!result.tempFilePath) {
            reject(new ApiError("报表下载成功但未生成临时文件", "server", result.statusCode, traceId))
            return
          }
          this.runtime.openDocument({
            filePath: result.tempFilePath,
            fileType,
            showMenu: true,
            success: resolve,
            fail: (failure) => reject(new ApiError(
              `报表已下载，但无法打开临时文件：${failure.errMsg || "未知错误"}`,
              "server",
              null,
              traceId,
            )),
          })
        },
        fail: (failure) => {
          const timeout = failure.errMsg.toLowerCase().includes("timeout")
          this.logger.warn("api.download_failure", { path, traceId, timeout, errno: failure.errno })
          reject(new ApiError(timeout ? "报表下载超时，请稍后重试" : "报表下载失败，请检查网络后重试", timeout ? "timeout" : "network", null, traceId))
        },
      })
    })
  }
}
