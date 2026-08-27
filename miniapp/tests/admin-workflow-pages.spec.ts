import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest"

const mocks = vi.hoisted(() => ({
  copySessionWeek: vi.fn(), sessions: vi.fn(), courses: vi.fn(), coaches: vi.fn(), rooms: vi.fn(),
  privateSlots: vi.fn(), privateBookings: vi.fn(), generatePrivateWeek: vi.fn(), deletePrivateSlot: vi.fn(),
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
    adminService: {
      copySessionWeek: mocks.copySessionWeek, sessions: mocks.sessions, courses: mocks.courses, coaches: mocks.coaches, rooms: mocks.rooms,
      privateSlots: mocks.privateSlots, privateBookings: mocks.privateBookings, generatePrivateWeek: mocks.generatePrivateWeek, deletePrivateSlot: mocks.deletePrivateSlot,
    },
    navigationService: { routeForbidden: vi.fn() }, storageService: { user: () => ({ username: "admin", role: "admin" }) },
  }
})
vi.mock("../miniprogram/utils/modal", () => ({ confirmAction: mocks.confirmAction, promptAction: mocks.promptAction }))

const definitions: Array<Record<string, any>> = []
beforeAll(async () => {
  vi.stubGlobal("Page", (value: Record<string, any>) => definitions.push(value))
  vi.stubGlobal("wx", { showToast: vi.fn() })
  await import("../miniprogram/packageAdmin/pages/classes/index")
  await import("../miniprogram/packageAdmin/pages/private/index")
})
beforeEach(() => {
  vi.clearAllMocks()
  mocks.sessions.mockResolvedValue({ items: [] })
  mocks.courses.mockResolvedValue({ items: [] })
  mocks.coaches.mockResolvedValue({ items: [] })
  mocks.rooms.mockResolvedValue({ items: [] })
  mocks.privateSlots.mockResolvedValue({ items: [] })
  mocks.privateBookings.mockResolvedValue({ items: [] })
})

function mount(index: number): any {
  const page: any = { ...definitions[index], data: structuredClone(definitions[index].data) }
  page.setData = (values: Record<string, unknown>) => Object.assign(page.data, values)
  return page
}

describe("admin workflow pages", () => {
  it("shows localized conflicts after copying a class week", async () => {
    const page = mount(0)
    page.data.copySourceWeek = "2026-08-31"
    page.data.copyTargetWeek = "2026-09-07"
    mocks.copySessionWeek.mockResolvedValue({ created: [{ id: "session-2" }], conflicts: [{ targetStartAt: "2026-09-08T09:00:00+08:00", reason: "room_time_conflict" }] })

    await page.copyWeek()

    expect(mocks.copySessionWeek).toHaveBeenCalledWith("2026-08-31", "2026-09-07")
    expect(page.data.copyFeedback).toContain("成功创建 1 个课次")
    expect(page.data.copyConflicts[0]).toContain("教室同期已被占用")
  })

  it("generates a private-training week and localizes conflicts", async () => {
    const page = mount(1)
    page.data.coaches = [{ id: "coach-1", name: "李教练" }]
    page.data.coachIndex = 0
    page.data.weekStart = "2026-08-31"
    page.data.weekStartTime = "09:00"
    page.data.durationMinutes = "60"
    page.data.selectedWeekdays = [0, 2, 4]
    mocks.generatePrivateWeek.mockResolvedValue({ created: [], conflicts: [{ startAt: "2026-08-31T09:00:00+08:00", endAt: "2026-08-31T10:00:00+08:00", reason: "private_slot_time_conflict" }] })

    await page.generateWeek()

    expect(mocks.generatePrivateWeek).toHaveBeenCalledWith({ coachProfileId: "coach-1", weekStart: "2026-08-31T00:00:00+08:00", weekdays: [0, 2, 4], startTime: "09:00", durationMinutes: 60 })
    expect(page.data.batchConflicts[0]).toContain("教练已有重叠私教时段")
  })
})
