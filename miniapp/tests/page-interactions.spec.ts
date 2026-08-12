import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  bindAndRoute: vi.fn(),
  isSignedOut: vi.fn(),
  isPasswordLoginEnabled: vi.fn(),
  shouldShowLoginChoice: vi.fn(),
  loginAndRoute: vi.fn(),
  passwordLoginAndRoute: vi.fn(),
  changePassword: vi.fn(),
  logout: vi.fn(),
  bookClass: vi.fn(),
  schedule: vi.fn(),
  confirmAction: vi.fn().mockResolvedValue(true),
}))

vi.mock("../miniprogram/services", () => {
  class ActionGuard {
    private readonly pending = new Set<string>()

    isPending(actionId: string): boolean {
      return this.pending.has(actionId)
    }

    async run<T>(actionId: string, action: () => Promise<T>): Promise<T | null> {
      if (this.pending.has(actionId)) return null
      this.pending.add(actionId)
      try {
        return await action()
      } finally {
        this.pending.delete(actionId)
      }
    }
  }

  return {
    ActionGuard,
    ApiError: class ApiError extends Error {},
    BindingTicketExpiredError: class BindingTicketExpiredError extends Error {},
    memberService: { bookClass: mocks.bookClass, schedule: mocks.schedule },
    navigationService: { routeForbidden: vi.fn() },
    sessionService: {
      bindAndRoute: mocks.bindAndRoute,
      isSignedOut: mocks.isSignedOut,
      isPasswordLoginEnabled: mocks.isPasswordLoginEnabled,
      shouldShowLoginChoice: mocks.shouldShowLoginChoice,
      loginAndRoute: mocks.loginAndRoute,
      passwordLoginAndRoute: mocks.passwordLoginAndRoute,
      changePassword: mocks.changePassword,
      logout: mocks.logout,
    },
    storageService: { user: () => ({ role: "member" }) },
  }
})

vi.mock("../miniprogram/utils/modal", () => ({ confirmAction: mocks.confirmAction }))

const definitions: any[] = []

function mount(definition: any): any {
  const page = { ...definition, data: structuredClone(definition.data) }
  page.setData = (values: Record<string, unknown>) => Object.assign(page.data, values)
  return page
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

beforeAll(async () => {
  vi.stubGlobal("Page", (definition: any) => definitions.push(definition))
  await import("../miniprogram/pages/bind/index")
  await import("../miniprogram/pages/member/schedule/index")
  await import("../miniprogram/pages/startup/index")
  await import("../miniprogram/pages/account/index")
  await import("../miniprogram/pages/account/security/index")
})

beforeEach(() => {
  vi.clearAllMocks()
  mocks.isSignedOut.mockReturnValue(false)
  mocks.isPasswordLoginEnabled.mockReturnValue(true)
  mocks.shouldShowLoginChoice.mockReturnValue(false)
})

describe("Mini Program page interactions", () => {
  it("suppresses duplicate binding taps and clears the password", async () => {
    const page = mount(definitions[0])
    const pending = deferred<Record<string, unknown>>()
    mocks.bindAndRoute.mockReturnValueOnce(pending.promise)
    page.data.username = "member.one"
    page.data.password = "one-time-password"

    const first = page.submit()
    const second = page.submit()

    expect(mocks.bindAndRoute).toHaveBeenCalledOnce()
    expect(page.data.pending).toBe(true)
    await second
    pending.resolve({ role: "member" })
    await first
    expect(page.data.password).toBe("")
    expect(page.data.pending).toBe(false)
  })

  it("submits one booking mutation for repeated taps and refreshes state", async () => {
    const page = mount(definitions[1])
    const pending = deferred<Record<string, unknown>>()
    mocks.bookClass.mockReturnValueOnce(pending.promise)
    mocks.schedule.mockResolvedValue([])
    const event = { currentTarget: { dataset: { id: "session-1", name: "晨间瑜伽" } } }

    const first = page.book(event)
    await Promise.resolve()
    const second = page.book(event)
    pending.resolve({ id: "booking-1" })
    await Promise.all([first, second])

    expect(mocks.bookClass).toHaveBeenCalledOnce()
    expect(mocks.schedule).toHaveBeenCalled()
    expect(page.data.pendingId).toBe("")
    expect(page.data.mode).toBe("empty")
  })

  it("does not restart WeChat login while explicitly signed out", () => {
    const page = mount(definitions[2])
    mocks.isSignedOut.mockReturnValueOnce(true)

    page.onLoad()

    expect(page.data.mode).toBe("signed_out")
    expect(mocks.loginAndRoute).not.toHaveBeenCalled()
  })

  it("shows the trial login choice without automatically calling wx.login", () => {
    const page = mount(definitions[2])
    mocks.shouldShowLoginChoice.mockReturnValueOnce(true)

    page.onLoad()

    expect(page.data.mode).toBe("login_choice")
    expect(page.data.accountLoginEnabled).toBe(true)
    expect(mocks.loginAndRoute).not.toHaveBeenCalled()
  })

  it("logs in with credentials once and clears the password", async () => {
    const page = mount(definitions[2])
    const pending = deferred<Record<string, unknown>>()
    mocks.passwordLoginAndRoute.mockReturnValueOnce(pending.promise)
    page.data.username = "test.member"
    page.data.password = "password123"

    const first = page.passwordLogin()
    const second = page.passwordLogin()

    expect(mocks.passwordLoginAndRoute).toHaveBeenCalledOnce()
    expect(page.data.pending).toBe(true)
    await second
    pending.resolve({ role: "member" })
    await first
    expect(page.data.password).toBe("")
    expect(page.data.pending).toBe(false)
  })

  it("starts WeChat login only after the signed-out user requests it", async () => {
    const page = mount(definitions[2])
    mocks.loginAndRoute.mockResolvedValueOnce({ state: "authenticated" })

    await page.start()

    expect(mocks.loginAndRoute).toHaveBeenCalledOnce()
    expect(page.data.mode).toBe("loading")
  })

  it("returns to the trial login choice when WeChat login fails", async () => {
    const page = mount(definitions[2])
    page.data.accountLoginEnabled = true
    mocks.loginAndRoute.mockRejectedValueOnce(new Error("wechat unavailable"))

    await page.start()

    expect(page.data.mode).toBe("login_choice")
    expect(page.data.error).toContain("微信登录失败")
  })

  it("delegates account logout to the session service", () => {
    const page = mount(definitions[3])

    page.logout()

    expect(mocks.logout).toHaveBeenCalledOnce()
  })

  it("validates password change form before submitting", async () => {
    const page = mount(definitions[4])
    page.data.oldPassword = "old-password"
    page.data.newPassword = "short"
    page.data.confirmation = "short"

    await page.submit()

    expect(mocks.changePassword).not.toHaveBeenCalled()
    expect(page.data.error).toContain("8")

    page.data.newPassword = "new-password-123"
    page.data.confirmation = "different-123"
    await page.submit()
    expect(mocks.changePassword).not.toHaveBeenCalled()
    expect(page.data.error).toContain("不一致")
  })

  it("submits password change once and clears the password fields", async () => {
    const page = mount(definitions[4])
    mocks.changePassword.mockResolvedValueOnce(undefined)
    page.data.oldPassword = "old-password"
    page.data.newPassword = "new-password-123"
    page.data.confirmation = "new-password-123"

    await page.submit()

    expect(mocks.changePassword).toHaveBeenCalledOnce()
    expect(mocks.changePassword).toHaveBeenCalledWith("old-password", "new-password-123")
    expect(page.data.oldPassword).toBe("")
    expect(page.data.newPassword).toBe("")
    expect(page.data.confirmation).toBe("")
    expect(page.data.success).toContain("密码修改成功")
  })
})
