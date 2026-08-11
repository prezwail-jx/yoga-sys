import { beforeAll, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  bindAndRoute: vi.fn(),
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
    sessionService: { bindAndRoute: mocks.bindAndRoute, logout: mocks.logout },
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
})
