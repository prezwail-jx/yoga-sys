import { ApiError, type ApiClient } from "./api"
import { passwordLoginEnabled } from "../config/environment"
import type { NavigationService } from "./navigation"
import type { MiniProgramRuntime } from "../platform/runtime"
import type { StorageService } from "./storage"
import type { CurrentUser, PasswordLoginResult, WechatBindResult, WechatSession } from "../types/contracts"

export type BootstrapResult =
  | { state: "authenticated"; user: CurrentUser }
  | { state: "binding_required" }

export class BindingTicketExpiredError extends Error {
  constructor() {
    super("Binding ticket expired. Start WeChat login again.")
    this.name = "BindingTicketExpiredError"
  }
}

function wechatCode(runtime: MiniProgramRuntime): Promise<string> {
  return new Promise((resolve, reject) => {
    runtime.login({
      success: ({ code }) => code ? resolve(code) : reject(new Error("wx.login returned no code")),
      fail: ({ errMsg }) => reject(new Error(errMsg || "wx.login failed")),
    })
  })
}

export class SessionService {
  private bindingPending = false
  private passwordLoginPending = false
  private bootstrapPending: Promise<BootstrapResult> | null = null

  constructor(
    private readonly runtime: MiniProgramRuntime,
    private readonly api: ApiClient,
    private readonly storage: StorageService,
    private readonly navigation: NavigationService,
  ) {}

  bootstrap(): Promise<BootstrapResult> {
    if (this.bootstrapPending) return this.bootstrapPending
    this.bootstrapPending = this.restoreOrLogin().finally(() => {
      this.bootstrapPending = null
    })
    return this.bootstrapPending
  }

  async bootstrapAndRoute(): Promise<BootstrapResult> {
    const result = await this.bootstrap()
    if (result.state === "binding_required") {
      this.navigation.routeBinding()
    } else {
      this.navigation.routeAuthenticated(result.user)
    }
    return result
  }

  isSignedOut(): boolean {
    return this.storage.isSignedOut()
  }

  isPasswordLoginEnabled(): boolean {
    return passwordLoginEnabled(this.runtime)
  }

  shouldShowLoginChoice(): boolean {
    return this.isPasswordLoginEnabled()
      && !this.storage.token()
      && (this.storage.isSignedOut() || this.storage.authMode() !== "wechat")
  }

  loginAndRoute(): Promise<BootstrapResult> {
    this.storage.clearSignedOut()
    this.storage.setAuthMode("wechat")
    return this.bootstrapAndRoute()
  }

  async passwordLoginAndRoute(username: string, password: string): Promise<CurrentUser> {
    if (!this.isPasswordLoginEnabled()) {
      throw new ApiError("正式版仅支持微信登录", "authorization", 403, "local-password-login-disabled")
    }
    if (this.passwordLoginPending) throw new Error("Password login is already in progress")
    this.passwordLoginPending = true
    try {
      const result = await this.api.request<PasswordLoginResult>("/auth/login", {
        method: "POST",
        authenticated: false,
        body: { username, password },
      })
      if (result.role !== "member" && result.role !== "coach") {
        throw new ApiError("仅会员和教练账号可以登录小程序", "authorization", 403, "local-role-check")
      }
      this.storage.setToken(result.access_token)
      this.storage.setAuthMode("password")
      this.storage.clearSignedOut()
      this.storage.clearBinding()
      const user = await this.loadCurrentUser()
      this.navigation.routeAuthenticated(user)
      return user
    } finally {
      this.passwordLoginPending = false
    }
  }

  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await this.api.request<never>("/auth/change-password", {
      method: "POST",
      body: { oldPassword, newPassword },
    })
  }

  async bindAndRoute(username: string, password: string): Promise<CurrentUser> {
    if (this.bindingPending) throw new Error("Binding is already in progress")
    const challenge = this.storage.binding()
    if (!challenge || challenge.expiresAt <= Date.now()) {
      this.storage.clearBinding()
      throw new BindingTicketExpiredError()
    }
    this.bindingPending = true
    try {
      const result = await this.api.request<WechatBindResult>("/auth/wechat/bind", {
        method: "POST",
        authenticated: false,
        body: { bindingTicket: challenge.ticket, username, password },
      })
      this.storage.setToken(result.accessToken)
      this.storage.setAuthMode("wechat")
      this.storage.clearBinding()
      const user = await this.loadCurrentUser()
      this.navigation.routeAuthenticated(user)
      return user
    } finally {
      this.bindingPending = false
    }
  }

  logout(): void {
    this.storage.clearSession()
    this.storage.clearBinding()
    this.storage.clearAuthMode()
    this.storage.markSignedOut()
    this.navigation.routeStartup()
  }

  restartLogin(): void {
    this.storage.clearSession()
    this.storage.clearBinding()
    this.storage.clearSignedOut()
    this.storage.setAuthMode("wechat")
    this.navigation.routeStartup()
  }

  private async restoreOrLogin(): Promise<BootstrapResult> {
    if (this.storage.token()) {
      try {
        return { state: "authenticated", user: await this.loadCurrentUser() }
      } catch (error) {
        if (!(error instanceof ApiError) || error.kind !== "authentication") throw error
      }
    }
    return this.startWechatSession()
  }

  private async startWechatSession(): Promise<BootstrapResult> {
    const code = await wechatCode(this.runtime)
    const session = await this.api.request<WechatSession>("/auth/wechat/session", {
      method: "POST",
      authenticated: false,
      body: { code },
    })
    if (session.state === "binding_required") {
      this.storage.clearSession()
      this.storage.setAuthMode("wechat")
      this.storage.setBinding({
        ticket: session.bindingTicket,
        expiresAt: Date.now() + session.expiresIn * 1000,
      })
      return { state: "binding_required" }
    }
    this.storage.setToken(session.accessToken)
    this.storage.setAuthMode("wechat")
    this.storage.clearBinding()
    return { state: "authenticated", user: await this.loadCurrentUser() }
  }

  private async loadCurrentUser(): Promise<CurrentUser> {
    const user = await this.api.request<CurrentUser>("/auth/me")
    if (user.role !== "member" && user.role !== "coach") {
      this.storage.clearSession()
      this.navigation.routeForbidden()
      throw new ApiError("Role is not supported by the Mini Program", "authorization", 403, "local-role-check")
    }
    this.storage.setUser(user)
    return user
  }
}
