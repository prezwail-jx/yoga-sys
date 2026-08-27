import { describe, expect, it, vi } from "vitest"

import { ApiClient } from "../miniprogram/services/api"
import { NavigationService } from "../miniprogram/services/navigation"
import { BindingTicketExpiredError, SessionService } from "../miniprogram/services/session"
import { StorageService } from "../miniprogram/services/storage"
import { FakeRuntime } from "./helpers/fake-runtime"

function services(runtime: FakeRuntime) {
  const storage = new StorageService(runtime)
  const navigation = new NavigationService(runtime)
  const api = new ApiClient(runtime, "https://api.example.test", () => storage.token(), () => storage.clearSession())
  const session = new SessionService(runtime, api, storage, navigation)
  return { storage, navigation, session }
}

describe("SessionService", () => {
  it("restores a stored token through current-user loading without wx.login", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setToken("stored-token")
    runtime.requestHandler = (options) => options.success({
      data: { username: "member.one", role: "member", memberId: "member-1" },
      statusCode: 200,
      header: {},
    })

    await expect(session.bootstrap()).resolves.toMatchObject({
      state: "authenticated", user: { role: "member" },
    })
    expect(runtime.loginCalls).toBe(0)
    expect(storage.user()?.username).toBe("member.one")
  })

  it("clears a rejected token and recovers through a fresh wx.login binding transition", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setToken("expired-token")
    runtime.requestHandler = (options) => {
      if (options.url.endsWith("/auth/me")) {
        options.success({ data: { detail: "Expired" }, statusCode: 401, header: {} })
        return
      }
      options.success({
        data: { state: "binding_required", bindingTicket: "ticket-1", expiresIn: 600 },
        statusCode: 200,
        header: {},
      })
    }

    await expect(session.bootstrapAndRoute()).resolves.toEqual({ state: "binding_required" })
    expect(runtime.loginCalls).toBe(1)
    expect(storage.token()).toBeNull()
    expect(storage.binding()?.ticket).toBe("ticket-1")
    expect(runtime.relaunches.at(-1)).toBe("/pages/bind/index")
  })

  it("remains signed out after explicit logout until login is requested", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setToken("stored-token")
    storage.setUser({ username: "member.one", role: "member", memberId: "member-1" })
    storage.setBinding({ ticket: "ticket-1", expiresAt: Date.now() + 60_000 })

    session.logout()

    expect(storage.token()).toBeNull()
    expect(storage.user()).toBeNull()
    expect(storage.binding()).toBeNull()
    expect(storage.isSignedOut()).toBe(true)
    expect(storage.authMode()).toBeNull()
    expect(runtime.loginCalls).toBe(0)
    expect(runtime.relaunches.at(-1)).toBe("/pages/startup/index")
  })

  it("clears the signed-out marker when the user starts WeChat login", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.markSignedOut()
    runtime.requestHandler = (options) => options.success({
      data: { state: "binding_required", bindingTicket: "ticket-1", expiresIn: 600 },
      statusCode: 200,
      header: {},
    })

    await session.loginAndRoute()

    expect(storage.isSignedOut()).toBe(false)
    expect(storage.authMode()).toBe("wechat")
    expect(runtime.loginCalls).toBe(1)
    expect(runtime.relaunches.at(-1)).toBe("/pages/bind/index")
  })

  it("logs a member in with trial credentials without calling wx.login or creating a binding", async () => {
    const runtime = new FakeRuntime()
    runtime.envVersion = "trial"
    const { storage, session } = services(runtime)
    runtime.requestHandler = (options) => {
      if (options.url.endsWith("/auth/login")) {
        options.success({
          data: { access_token: "password-token", token_type: "bearer", role: "member" },
          statusCode: 200,
          header: {},
        })
        return
      }
      options.success({
        data: { username: "test.member", role: "member", memberId: "member-1" },
        statusCode: 200,
        header: {},
      })
    }

    await expect(session.passwordLoginAndRoute("test.member", "password123")).resolves.toMatchObject({
      username: "test.member",
      role: "member",
    })

    expect(runtime.loginCalls).toBe(0)
    expect(storage.token()).toBe("password-token")
    expect(storage.authMode()).toBe("password")
    expect(storage.binding()).toBeNull()
    expect(runtime.relaunches.at(-1)).toBe("/pages/workspace/index")
    expect(JSON.stringify([...runtime.storage.entries()])).not.toContain("password123")
  })

  it("accepts administrator credentials in trial without creating a WeChat binding", async () => {
    const runtime = new FakeRuntime()
    runtime.envVersion = "trial"
    const { storage, session } = services(runtime)
    runtime.requestHandler = (options) => options.success({ data: options.url.endsWith("/auth/login") ? { access_token: "admin-token", token_type: "bearer", role: "admin" } : { username: "admin", role: "admin" }, statusCode: 200, header: {} })

    await expect(session.passwordLoginAndRoute("admin", "password123")).resolves.toMatchObject({ role: "admin" })
    expect(storage.token()).toBe("admin-token")
    expect(storage.authMode()).toBe("password")
  })

  it("rejects release member credentials before persisting their token", async () => {
    const runtime = new FakeRuntime()
    runtime.envVersion = "release"
    const { storage, session } = services(runtime)
    runtime.requestHandler = (options) => options.success({ data: { access_token: "member-token", token_type: "bearer", role: "member" }, statusCode: 200, header: {} })

    await expect(session.passwordLoginAndRoute("member", "password123")).rejects.toMatchObject({
      kind: "authorization",
    })
    expect(runtime.requests).toHaveLength(1)
    expect(storage.token()).toBeNull()
    expect(storage.authMode()).toBeNull()
  })

  it("accepts release administrator credentials and validates /auth/me before saving token", async () => {
    const runtime = new FakeRuntime(); runtime.envVersion = "release"
    const { storage, session } = services(runtime)
    storage.setAuthMode("wechat")
    runtime.requestHandler = (options) => options.success({ data: options.url.endsWith("/auth/login") ? { access_token: "admin-token", token_type: "bearer", role: "admin" } : { username: "admin", role: "admin" }, statusCode: 200, header: {} })
    await expect(session.passwordLoginAndRoute("admin", "password123")).resolves.toMatchObject({ role: "admin" })
    expect(storage.token()).toBe("admin-token")
    expect(runtime.requests[1].header.Authorization).toBe("Bearer admin-token")
  })

  it("rejects a stored release password session when it belongs to a member", async () => {
    const runtime = new FakeRuntime(); runtime.envVersion = "release"
    const { storage, session } = services(runtime)
    storage.setToken("legacy-member-token")
    storage.setAuthMode("password")
    runtime.requestHandler = (options) => options.success({ data: { username: "member", role: "member", memberId: "member-1" }, statusCode: 200, header: {} })

    await expect(session.bootstrap()).rejects.toMatchObject({ kind: "authorization" })
    expect(storage.token()).toBeNull()
    expect(storage.authMode()).toBeNull()
    expect(storage.isSignedOut()).toBe(true)
    expect(runtime.loginCalls).toBe(0)
  })

  it("returns an expired administrator password session to password login instead of WeChat", async () => {
    const runtime = new FakeRuntime(); runtime.envVersion = "release"
    const { storage, session } = services(runtime)
    storage.setToken("expired-admin-token")
    storage.setAuthMode("password")
    runtime.requestHandler = (options) => options.success({ data: { detail: "令牌已过期" }, statusCode: 401, header: {} })

    await expect(session.bootstrap()).rejects.toMatchObject({ kind: "authentication" })
    expect(storage.token()).toBeNull()
    expect(storage.authMode()).toBeNull()
    expect(storage.isSignedOut()).toBe(true)
    expect(runtime.loginCalls).toBe(0)
  })

  it("rejects an administrator returned by WeChat login without saving its token", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    runtime.requestHandler = (options) => options.success({ data: { state: "bound", accessToken: "wechat-admin-token", tokenType: "bearer", role: "admin" }, statusCode: 200, header: {} })
    await expect(session.loginAndRoute()).rejects.toMatchObject({ kind: "authorization" })
    expect(storage.token()).toBeNull()
  })

  it("returns expired password sessions to login choice without changing WeChat recovery", () => {
    const runtime = new FakeRuntime()
    const { storage } = services(runtime)
    storage.setToken("password-token")
    storage.setAuthMode("password")
    storage.clearUnauthorizedSession()
    expect(storage.token()).toBeNull()
    expect(storage.authMode()).toBeNull()
    expect(storage.isSignedOut()).toBe(true)

    storage.clearSignedOut()
    storage.setToken("wechat-token")
    storage.setAuthMode("wechat")
    storage.clearUnauthorizedSession()
    expect(storage.token()).toBeNull()
    expect(storage.authMode()).toBe("wechat")
    expect(storage.isSignedOut()).toBe(false)
  })

  it("binds once, does not persist the password and routes from server role", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setBinding({ ticket: "ticket-2", expiresAt: Date.now() + 60_000 })
    runtime.requestHandler = (options) => {
      if (options.url.endsWith("/auth/wechat/bind")) {
        options.success({
          data: { accessToken: "bound-token", tokenType: "bearer", role: "coach" },
          statusCode: 200,
          header: {},
        })
        return
      }
      options.success({
        data: { username: "coach.one", role: "coach", coachProfileId: "coach-1" },
        statusCode: 200,
        header: {},
      })
    }

    await session.bindAndRoute("coach.one", "one-time-password")
    expect(storage.token()).toBe("bound-token")
    expect(storage.binding()).toBeNull()
    expect(runtime.relaunches.at(-1)).toBe("/pages/workspace/index")
    expect(JSON.stringify([...runtime.storage.entries()])).not.toContain("one-time-password")
  })

  it("stores only the intended ticket boundary while binding is pending", async () => {
    const runtime = new FakeRuntime()
    const { session } = services(runtime)
    runtime.requestHandler = (options) => options.success({
      data: { state: "binding_required", bindingTicket: "opaque-ticket", expiresIn: 600 },
      statusCode: 200,
      header: {},
    })

    await session.bootstrap()

    const serialized = JSON.stringify([...runtime.storage.entries()])
    expect(serialized).toContain("opaque-ticket")
    expect(serialized).not.toContain("wx-login-code")
    expect(serialized).not.toContain("session_key")
    expect(serialized).not.toContain("openid")
    expect(serialized).not.toContain("password")
  })

  it("rejects expired tickets before sending credentials", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setBinding({ ticket: "expired", expiresAt: Date.now() - 1 })
    runtime.requestHandler = vi.fn()

    await expect(session.bindAndRoute("member.one", "password")).rejects.toBeInstanceOf(BindingTicketExpiredError)
    expect(runtime.requests).toHaveLength(0)
    expect(storage.binding()).toBeNull()
  })

  it("suppresses duplicate binding submissions while the first is pending", async () => {
    const runtime = new FakeRuntime()
    const { storage, session } = services(runtime)
    storage.setBinding({ ticket: "pending", expiresAt: Date.now() + 60_000 })
    runtime.requestHandler = () => undefined

    void session.bindAndRoute("member.one", "password")
    await expect(session.bindAndRoute("member.one", "password")).rejects.toThrow("already in progress")
    expect(runtime.requests).toHaveLength(1)
  })

  it("changes the password without persisting it to storage", async () => {
    const runtime = new FakeRuntime()
    const { session } = services(runtime)
    runtime.requestHandler = (options) => options.success({ data: null, statusCode: 204, header: {} })

    await session.changePassword("old-password", "new-password-123")

    const request = runtime.requests.find(item => item.url.endsWith("/auth/change-password"))!
    expect(request.method).toBe("POST")
    expect(JSON.stringify(request.data)).toBe(JSON.stringify({ oldPassword: "old-password", newPassword: "new-password-123" }))
    const serialized = JSON.stringify([...runtime.storage.entries()])
    expect(serialized).not.toContain("old-password")
    expect(serialized).not.toContain("new-password-123")
  })
})
