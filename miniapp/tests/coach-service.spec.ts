import { describe, expect, it, vi } from "vitest"

import { ApiClient } from "../miniprogram/services/api"
import { CoachService } from "../miniprogram/services/coach"
import { IdempotencyService } from "../miniprogram/services/idempotency"
import { StorageService } from "../miniprogram/services/storage"
import { FakeRuntime } from "./helpers/fake-runtime"

function coachService(runtime: FakeRuntime): CoachService {
  const storage = new StorageService(runtime)
  storage.setUser({ username: "coach.one", role: "coach", coachProfileId: "coach-1" })
  const api = new ApiClient(runtime, "https://api.example.test", () => "coach-token", vi.fn())
  return new CoachService(api, new IdempotencyService(storage), storage)
}

describe("CoachService", () => {
  it("loads assigned schedule without accepting a client-selected coach id", async () => {
    const runtime = new FakeRuntime()
    const service = coachService(runtime)
    runtime.requestHandler = (options) => options.success({
      data: { items: [], weekStart: "2030-01-07", weekEnd: "2030-01-13" },
      statusCode: 200,
      header: {},
    })

    await expect(service.schedule("2030-01-07")).resolves.toEqual([])
    expect(runtime.requests[0].url).toBe("https://api.example.test/class-sessions?weekStart=2030-01-07")
    expect(runtime.requests[0].url).not.toContain("coach")
  })

  it("uses persisted idempotency keys and sends no coachProfileId for mutations", async () => {
    const runtime = new FakeRuntime()
    const service = coachService(runtime)
    runtime.requestHandler = (options) => options.success({
      data: { id: "result-1", status: "confirmed" },
      statusCode: 200,
      header: {},
    })

    await service.createSlot({ startAt: "2030-01-10T01:00:00Z", endAt: "2030-01-10T02:00:00Z" })
    await service.confirmPrivate("private-1")
    await service.signInPrivate("private-1", {
      content: "肩颈拉伸",
      consumedHours: 1,
      memberStatusNotes: "状态良好",
    })

    expect(runtime.requests.every((request) => request.header["Idempotency-Key"]?.length >= 8)).toBe(true)
    expect(JSON.stringify(runtime.requests.map((request) => request.data))).not.toContain("coachProfileId")
    expect(runtime.requests.map((request) => request.url)).toEqual([
      "https://api.example.test/private-slots",
      "https://api.example.test/private-bookings/private-1/confirm",
      "https://api.example.test/private-bookings/private-1/sign-in",
    ])
  })

  it("reuses the same operation key after an uncertain network result", async () => {
    const runtime = new FakeRuntime()
    const service = coachService(runtime)
    runtime.requestHandler = (options) => options.fail({ errMsg: "request:fail timeout" })

    await expect(service.checkIn("booking-1")).rejects.toMatchObject({ uncertain: true })
    const firstKey = runtime.requests[0].header["Idempotency-Key"]
    runtime.requestHandler = (options) => options.success({ data: { id: "booking-1" }, statusCode: 200, header: {} })
    await service.checkIn("booking-1")

    expect(runtime.requests[1].header["Idempotency-Key"]).toBe(firstKey)
  })

  it("returns explicit weekly availability conflicts from the backend", async () => {
    const runtime = new FakeRuntime()
    const service = coachService(runtime)
    runtime.requestHandler = (options) => options.success({
      data: {
        created: [],
        conflicts: [{
          startAt: "2030-01-11T01:00:00Z",
          endAt: "2030-01-11T02:00:00Z",
          reason: "coach_class_time_conflict",
        }],
      },
      statusCode: 200,
      header: {},
    })

    const result = await service.generateWeek({
      weekStart: "2030-01-07T00:00:00+08:00",
      weekdays: [5],
      startTime: "09:00",
      durationMinutes: 60,
    })

    expect(result.conflicts[0].reason).toBe("coach_class_time_conflict")
    expect(runtime.requests[0].header["Idempotency-Key"]).toBeTruthy()
    expect(JSON.stringify(runtime.requests[0].data)).not.toContain("coachProfileId")
  })
})
