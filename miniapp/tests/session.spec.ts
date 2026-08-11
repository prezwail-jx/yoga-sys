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
})
