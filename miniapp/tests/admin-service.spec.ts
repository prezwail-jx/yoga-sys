import { describe, expect, it, vi } from "vitest"
import { ApiClient } from "../miniprogram/services/api"
import { AdminService } from "../miniprogram/services/admin"
import { IdempotencyService } from "../miniprogram/services/idempotency"
import { StorageService } from "../miniprogram/services/storage"
import { FakeRuntime } from "./helpers/fake-runtime"

function services() {
  const runtime = new FakeRuntime()
  const storage = new StorageService(runtime)
  storage.setToken("admin-token")
  storage.setUser({ username: "admin", role: "admin" })
  const api = new ApiClient(runtime, "https://api.example.test", () => storage.token(), vi.fn())
  return { runtime, admin: new AdminService(api, new IdempotencyService(storage), storage) }
}

describe("AdminService", () => {
  it("copies a class-session week with the existing idempotent endpoint", async () => {
    const { runtime, admin } = services()
    runtime.requestHandler = options => options.success({ data: { created: [], conflicts: [{ sourceSessionId: "session-1", targetStartAt: "2026-09-07T09:00:00+08:00", reason: "room_time_conflict" }] }, statusCode: 200, header: {} })

    await admin.copySessionWeek("2026-08-31", "2026-09-07")

    expect(runtime.requests[0].url).toBe("https://api.example.test/class-sessions/copy-week")
    expect(runtime.requests[0].method).toBe("POST")
    expect(runtime.requests[0].data).toEqual({ sourceWeekStart: "2026-08-31", targetWeekStart: "2026-09-07" })
    expect(runtime.requests[0].header["Idempotency-Key"]).toMatch(/^mp-/)
  })

  it("uses real private-slot week, patch and delete contracts with idempotency keys", async () => {
    const { runtime, admin } = services()
    runtime.requestHandler = options => options.success({ data: options.url.endsWith("generate-week") ? { created: [], conflicts: [] } : { id: "slot-1" }, statusCode: 200, header: {} })

    await admin.generatePrivateWeek({ coachProfileId: "coach-1", weekStart: "2026-08-31T00:00:00+08:00", weekdays: [0, 2, 4], startTime: "09:00", durationMinutes: 60 })
    await admin.updatePrivateSlot("slot-1", "coach-1", "2026-09-01T09:00:00+08:00", "2026-09-01T10:00:00+08:00")
    await admin.deletePrivateSlot("slot-1")

    expect(runtime.requests.map(item => [item.method, item.url.replace("https://api.example.test", "")])).toEqual([
      ["POST", "/private-slots/generate-week"], ["PATCH", "/private-slots/slot-1"], ["DELETE", "/private-slots/slot-1"],
    ])
    expect(runtime.requests.every(item => Boolean(item.header["Idempotency-Key"]))).toBe(true)
  })

  it("exports the selected report through authenticated download and preview", async () => {
    const { runtime, admin } = services()
    await admin.exportReport("attendance", "2026-08-01", "2026-08-31")
    expect(runtime.downloads[0].url).toContain("/reports/export?category=attendance&dateFrom=2026-08-01&dateTo=2026-08-31")
    expect(runtime.openedDocuments[0].filePath).toBe("/tmp/report.xlsx")
  })
})
