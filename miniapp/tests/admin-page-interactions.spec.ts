import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  transaction: vi.fn(), updateMember: vi.fn(), member: vi.fn(), memberCards: vi.fn(), memberTimeline: vi.fn(), products: vi.fn(),
  confirmAction: vi.fn().mockResolvedValue(true), promptAction: vi.fn(),
}))

vi.mock("../miniprogram/services/index", () => {
  class ActionGuard {
    private pending = new Set<string>()
    async run<T>(id: string, action: () => Promise<T>): Promise<T | null> {
      if (this.pending.has(id)) return null
      this.pending.add(id)
      try { return await action() } finally { this.pending.delete(id) }
    }
  }
  return {
    ActionGuard,
    adminService: { transaction: mocks.transaction, updateMember: mocks.updateMember, member: mocks.member, memberCards: mocks.memberCards, memberTimeline: mocks.memberTimeline, products: mocks.products },
    navigationService: { routeForbidden: vi.fn() }, storageService: { user: () => ({ username: "admin", role: "admin" }) },
  }
})
vi.mock("../miniprogram/utils/modal", () => ({ confirmAction: mocks.confirmAction, promptAction: mocks.promptAction }))

let definition: Record<string, unknown>
beforeAll(async () => {
  vi.stubGlobal("Page", (value: Record<string, unknown>) => { definition = value })
  vi.stubGlobal("wx", { showToast: vi.fn() })
  await import("../miniprogram/packageAdmin/pages/member-detail/index")
})
beforeEach(() => {
  vi.clearAllMocks()
  mocks.member.mockResolvedValue({ id: "member-1", name: "测试会员", phone: "13800000000", joinDate: "2026-01-01", gender: "female", birthday: "1990-01-01", note: "旧备注", emergencyContact: "家属 13900000000", status: "normal", cardSummaries: [] })
  mocks.memberCards.mockResolvedValue({ items: [], total: 0 })
  mocks.memberTimeline.mockResolvedValue({ items: [], total: 0 })
  mocks.products.mockResolvedValue({ items: [{ id: "product-1", name: "十次卡", price: "1000.00" }], total: 1 })
})

function mount() {
  const page = { ...definition, data: structuredClone(definition.data) } as Record<string, any>
  page.setData = (values: Record<string, unknown>) => Object.assign(page.data, values)
  page.data.id = "member-1"
  page.data.member = { id: "member-1", name: "测试会员" }
  page.data.products = [{ id: "product-1", name: "十次卡", price: "1000.00" }]
  return page
}

describe("admin member-card page", () => {
  it("confirms a purchase and suppresses duplicate submissions", async () => {
    let resolve!: () => void
    mocks.transaction.mockReturnValueOnce(new Promise<void>(done => { resolve = done }))
    const page = mount()
    const first = page.purchase()
    await Promise.resolve()
    const second = page.purchase()
    await Promise.resolve()
    expect(mocks.transaction).toHaveBeenCalledOnce()
    expect(mocks.transaction).toHaveBeenCalledWith({ txnType: "purchase", memberId: "member-1", cardProductId: "product-1" })
    resolve()
    await Promise.all([first, second])
  })

  it("requires an adjustment reason before calling the API", async () => {
    const page = mount()
    page.data.cards = [{ id: "card-1", productName: "十次卡", remainingTimes: 8 }]
    mocks.promptAction.mockResolvedValueOnce("-2").mockResolvedValueOnce("")
    await page.cardAction({ currentTarget: { dataset: { id: "card-1", action: "adjust" } } })
    expect(page.data.error).toContain("原因不能为空")
  })

  it("updates only member fields supported by the backend", async () => {
    const page = mount()
    page.data.profileForm = { name: "  新姓名  ", gender: "other", birthday: "1992-02-02", note: "  新备注  ", emergencyContact: "  家属 13700000000  " }
    mocks.updateMember.mockResolvedValueOnce({})

    await page.saveProfile()

    expect(mocks.updateMember).toHaveBeenCalledWith("member-1", { name: "新姓名", gender: "other", birthday: "1992-02-02", note: "新备注", emergencyContact: "家属 13700000000" })
    expect(mocks.updateMember.mock.calls[0][1]).not.toHaveProperty("phone")
    expect(mocks.updateMember.mock.calls[0][1]).not.toHaveProperty("joinDate")
  })
})
