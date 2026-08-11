import { describe, expect, it, vi } from "vitest"

import { ApiClient } from "../miniprogram/services/api"
import { ActionGuard } from "../miniprogram/services/action-guard"
import { IdempotencyService } from "../miniprogram/services/idempotency"
import { MemberService } from "../miniprogram/services/member"
import { StorageService } from "../miniprogram/services/storage"
import type { ClassBooking, ClassSession } from "../miniprogram/types/member"
import { FakeRuntime } from "./helpers/fake-runtime"

function memberService(runtime: FakeRuntime): { service: MemberService; storage: StorageService } {
  const storage = new StorageService(runtime)
  storage.setUser({ username: "member.one", role: "member", memberId: "member-1" })
  const api = new ApiClient(runtime, "https://api.example.test", () => "member-token", vi.fn())
  return { service: new MemberService(api, new IdempotencyService(storage), storage), storage }
}

function session(): ClassSession {
  return {
    id: "session-1", courseId: "course-1", coachProfileId: "coach-1", roomId: "room-1",
    courseName: "流瑜伽", coachName: "周教练", roomName: "一号教室",
    startAt: "2030-01-07T01:00:00Z", endAt: "2030-01-07T02:00:00Z",
    capacity: 10, bookingOpenHoursBefore: 168, bookingCloseMinutesBefore: 0,
    cancelCutoffMinutesBefore: 120, status: "published", bookedCount: 0,
    remainingCapacity: 10, isFull: false,
  }
}

function booking(id: number): ClassBooking {
  return {
    id: `booking-${id}`, classSessionId: `session-${id}`, memberId: "member-1", memberName: "林会员",
    courseName: "流瑜伽", coachName: "周教练", roomName: "一号教室",
    startAt: "2030-01-07T01:00:00Z", endAt: "2030-01-07T02:00:00Z",
    sessionStatus: "published", status: "cancelled", bookedAt: "2030-01-01T00:00:00Z",
  }
}

describe("MemberService", () => {
  it("loads every booking page before joining schedule state", async () => {
    const runtime = new FakeRuntime()
    const { service } = memberService(runtime)
    const firstPage = Array.from({ length: 100 }, (_, index) => booking(index))
    firstPage[0] = { ...firstPage[0], id: "active", classSessionId: "session-1", status: "reserved" }
    runtime.requestHandler = (options) => {
      if (options.url.includes("/class-sessions?")) {
        options.success({ data: { items: [session()], weekStart: "2030-01-07", weekEnd: "2030-01-13" }, statusCode: 200, header: {} })
      } else if (options.url.includes("skip=0")) {
        options.success({ data: { items: firstPage, total: 101, skip: 0, limit: 100 }, statusCode: 200, header: {} })
      } else {
        options.success({ data: { items: [booking(100)], total: 101, skip: 100, limit: 100 }, statusCode: 200, header: {} })
      }
    }

    const groups = await service.schedule("2030-01-07")
    expect(groups[0].items[0].myBookingId).toBe("active")
    expect(runtime.requests.filter((request) => request.url.includes("/members/me/bookings"))).toHaveLength(2)
  })

  it("sends no client-selected memberId and uses idempotency for class/private mutations", async () => {
    const runtime = new FakeRuntime()
    const { service } = memberService(runtime)
    runtime.requestHandler = (options) => options.success({
      data: options.url === "/private-bookings" ? { id: "private-1" } : { id: "class-1" },
      statusCode: 201,
      header: {},
    })

    await service.bookClass("session-1")
    await service.requestPrivateSlot("slot-1", "肩颈训练")

    expect(runtime.requests.every((request) => request.header["Idempotency-Key"]?.length >= 8)).toBe(true)
    expect(runtime.requests[0].data).toEqual({})
    expect(runtime.requests[1].data).toEqual({ availabilityId: "slot-1", memberMessage: "肩颈训练" })
    expect(JSON.stringify(runtime.requests.map((request) => request.data))).not.toContain("memberId")
  })

  it("suppresses duplicate taps until the first action settles", async () => {
    const guard = new ActionGuard()
    let resolve: (() => void) | undefined
    const action = vi.fn(() => new Promise<void>((done) => { resolve = done }))
    const first = guard.run("booking-1", action)
    const duplicate = await guard.run("booking-1", action)
    expect(duplicate).toBeNull()
    expect(action).toHaveBeenCalledOnce()
    resolve?.()
    await first
    await guard.run("booking-1", async () => undefined)
    expect(guard.isPending("booking-1")).toBe(false)
  })

  it("loads private history and read-only cards from self-service routes", async () => {
    const runtime = new FakeRuntime()
    const { service } = memberService(runtime)
    runtime.requestHandler = (options) => {
      if (options.url.startsWith("https://api.example.test/private-bookings")) {
        options.success({ data: { items: [], total: 0, skip: 0, limit: 20 }, statusCode: 200, header: {} })
      } else {
        options.success({ data: { items: [{ id: "card-1", productName: "十次卡", cardType: "times", status: "active", remainingTimes: 10, openedOn: null, expiresOn: null, frozenFrom: null, frozenUntil: null }], total: 1 }, statusCode: 200, header: {} })
      }
    }

    await expect(service.privateBookings()).resolves.toMatchObject({ total: 0, items: [] })
    await expect(service.cards()).resolves.toHaveLength(1)
    expect(runtime.requests.map((request) => request.url)).toEqual([
      "https://api.example.test/private-bookings?skip=0&limit=20",
      "https://api.example.test/members/me/cards",
    ])
  })
})
