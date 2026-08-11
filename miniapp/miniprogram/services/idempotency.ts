import { ApiError, type ApiClient, type ApiRequestOptions } from "./api"
import type { StorageService } from "./storage"

function stable(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value)
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`
  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stable(item)}`)
    .join(",")}}`
}

function createKey(): string {
  return `mp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`
}

export class IdempotencyService {
  constructor(private readonly storage: StorageService) {}

  keyFor(operationId: string, request: unknown): string {
    const fingerprint = stable(request)
    const existing = this.storage.pendingIdempotency(operationId)
    if (existing?.fingerprint === fingerprint) return existing.key
    const key = createKey()
    this.storage.setPendingIdempotency(operationId, { key, fingerprint, createdAt: Date.now() })
    return key
  }

  complete(operationId: string, key: string): void {
    if (this.storage.pendingIdempotency(operationId)?.key === key) {
      this.storage.clearPendingIdempotency(operationId)
    }
  }

  restart(operationId: string): void {
    this.storage.clearPendingIdempotency(operationId)
  }
}

export async function idempotentMutation<T>(
  api: ApiClient,
  idempotency: IdempotencyService,
  operationId: string,
  path: string,
  options: Omit<ApiRequestOptions, "idempotencyKey">,
): Promise<T> {
  const fingerprint = { path, method: options.method ?? "POST", body: options.body }
  const key = idempotency.keyFor(operationId, fingerprint)
  try {
    const response = await api.request<T>(path, { ...options, idempotencyKey: key })
    idempotency.complete(operationId, key)
    return response
  } catch (error) {
    if (!(error instanceof ApiError) || !error.uncertain) {
      idempotency.complete(operationId, key)
    }
    throw error
  }
}
