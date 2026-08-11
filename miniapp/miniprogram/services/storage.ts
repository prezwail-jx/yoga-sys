import type { CurrentUser } from "../types/contracts"
import type { MiniProgramRuntime } from "../platform/runtime"

const TOKEN_KEY = "yoga.auth.token"
const USER_KEY = "yoga.auth.user"
const BINDING_KEY = "yoga.auth.binding"
const IDEMPOTENCY_PREFIX = "yoga.idempotency."

export interface BindingChallenge {
  ticket: string
  expiresAt: number
}

export interface PendingIdempotency {
  key: string
  fingerprint: string
  createdAt: number
}

export class StorageService {
  constructor(private readonly runtime: MiniProgramRuntime) {}

  token(): string | null {
    const value = this.runtime.getStorageSync(TOKEN_KEY)
    return typeof value === "string" && value ? value : null
  }

  setToken(token: string): void {
    this.runtime.setStorageSync(TOKEN_KEY, token)
  }

  user(): CurrentUser | null {
    const value = this.runtime.getStorageSync(USER_KEY)
    return value && typeof value === "object" ? value as CurrentUser : null
  }

  setUser(user: CurrentUser): void {
    this.runtime.setStorageSync(USER_KEY, user)
  }

  binding(): BindingChallenge | null {
    const value = this.runtime.getStorageSync(BINDING_KEY)
    return value && typeof value === "object" ? value as BindingChallenge : null
  }

  setBinding(challenge: BindingChallenge): void {
    this.runtime.setStorageSync(BINDING_KEY, challenge)
  }

  clearBinding(): void {
    this.runtime.removeStorageSync(BINDING_KEY)
  }

  pendingIdempotency(operationId: string): PendingIdempotency | null {
    const value = this.runtime.getStorageSync(`${IDEMPOTENCY_PREFIX}${operationId}`)
    return value && typeof value === "object" ? value as PendingIdempotency : null
  }

  setPendingIdempotency(operationId: string, pending: PendingIdempotency): void {
    this.runtime.setStorageSync(`${IDEMPOTENCY_PREFIX}${operationId}`, pending)
  }

  clearPendingIdempotency(operationId: string): void {
    this.runtime.removeStorageSync(`${IDEMPOTENCY_PREFIX}${operationId}`)
  }

  clearSession(): void {
    this.runtime.removeStorageSync(TOKEN_KEY)
    this.runtime.removeStorageSync(USER_KEY)
  }
}
