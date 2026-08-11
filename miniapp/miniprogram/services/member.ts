import type { ApiClient } from "./api"
import type { IdempotencyService } from "./idempotency"
import { idempotentMutation } from "./idempotency"
import type { StorageService } from "./storage"
import type {
  ClassBooking,
  ClassBookingView,
  ClassSession,
  ClassSessionList,
  DayGroup,
  MemberCard,
  PageResult,
  PrivateBooking,
  PrivateBookingView,
  PrivateSlotList,
  PrivateSlotView,
  ClassScheduleItem,
} from "../types/member"
import {
  classBookingView,
  groupClassSchedule,
  privateBookingView,
  privateSlotGroups,
} from "../utils/member-presenter"

export class MemberService {
  constructor(
    private readonly api: ApiClient,
    private readonly idempotency: IdempotencyService,
    private readonly storage: StorageService,
  ) {}

  async schedule(weekStart: string): Promise<DayGroup<ClassScheduleItem>[]> {
    const [sessions, bookings] = await Promise.all([
      this.api.request<ClassSessionList>(`/class-sessions?weekStart=${encodeURIComponent(weekStart)}`),
      this.allClassBookings(),
    ])
    return groupClassSchedule(sessions.items, bookings)
  }

  async bookClass(sessionId: string): Promise<ClassBooking> {
    return idempotentMutation<ClassBooking>(
      this.api,
      this.idempotency,
      this.operationId("class-book", sessionId),
      `/class-sessions/${encodeURIComponent(sessionId)}/bookings`,
      { method: "POST", body: {} },
    )
  }

  async cancelClass(bookingId: string, reason?: string): Promise<ClassBooking> {
    return idempotentMutation<ClassBooking>(
      this.api,
      this.idempotency,
      this.operationId("class-cancel", bookingId),
      `/class-bookings/${encodeURIComponent(bookingId)}/cancel`,
      { method: "POST", body: { reason: reason || null } },
    )
  }

  async classBookings(skip = 0, limit = 20): Promise<PageResult<ClassBookingView>> {
    const page = await this.api.request<PageResult<ClassBooking>>(
      `/members/me/bookings?skip=${skip}&limit=${limit}`,
    )
    const sessionIds = [...new Set(
      page.items.filter((item) => item.status === "reserved").map((item) => item.classSessionId),
    )]
    const sessions = new Map<string, ClassSession>()
    await Promise.all(sessionIds.map(async (sessionId) => {
      const session = await this.api.request<ClassSession>(`/class-sessions/${encodeURIComponent(sessionId)}`)
      sessions.set(sessionId, session)
    }))
    return {
      ...page,
      items: page.items.map((booking) => classBookingView(
        booking,
        sessions.get(booking.classSessionId) ?? null,
      )),
    }
  }

  async privateSlots(dateFrom: string, dateTo: string): Promise<DayGroup<PrivateSlotView>[]> {
    const response = await this.api.request<PrivateSlotList>(
      `/private-slots?dateFrom=${encodeURIComponent(dateFrom)}&dateTo=${encodeURIComponent(dateTo)}`,
    )
    return privateSlotGroups(response.items)
  }

  async requestPrivateSlot(availabilityId: string, memberMessage?: string): Promise<PrivateBooking> {
    return idempotentMutation<PrivateBooking>(
      this.api,
      this.idempotency,
      this.operationId("private-book", availabilityId),
      "/private-bookings",
      { method: "POST", body: { availabilityId, memberMessage: memberMessage || null } },
    )
  }

  async privateBookings(skip = 0, limit = 20): Promise<PageResult<PrivateBookingView>> {
    const page = await this.api.request<PageResult<PrivateBooking>>(
      `/private-bookings?skip=${skip}&limit=${limit}`,
    )
    return { ...page, items: page.items.map(privateBookingView) }
  }

  async cancelPrivateBooking(bookingId: string, reason?: string): Promise<PrivateBooking> {
    return idempotentMutation<PrivateBooking>(
      this.api,
      this.idempotency,
      this.operationId("private-cancel", bookingId),
      `/private-bookings/${encodeURIComponent(bookingId)}/cancel`,
      { method: "POST", body: { reason: reason || null } },
    )
  }

  async cards(): Promise<MemberCard[]> {
    const response = await this.api.request<{ items: MemberCard[]; total: number }>("/members/me/cards")
    return response.items
  }

  private async allClassBookings(): Promise<ClassBooking[]> {
    const items: ClassBooking[] = []
    const limit = 100
    let skip = 0
    let total = 1
    while (skip < total) {
      const page = await this.api.request<PageResult<ClassBooking>>(
        `/members/me/bookings?skip=${skip}&limit=${limit}`,
      )
      items.push(...page.items)
      total = page.total
      if (page.items.length === 0) break
      skip += page.items.length
    }
    return items
  }

  private operationId(action: string, resourceId: string): string {
    return `${this.storage.user()?.username ?? "member"}:${action}:${resourceId}`
  }
}
