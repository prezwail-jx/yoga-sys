import type { ApiClient } from "./api"
import type { IdempotencyService } from "./idempotency"
import { idempotentMutation } from "./idempotency"
import type { StorageService } from "./storage"
import type {
  CoachScheduleGroups,
  LessonInput,
  PrivateAvailabilityInput,
  PrivateWeekInput,
  PrivateWeekResult,
  RosterBooking,
} from "../types/coach"
import type {
  ClassBooking,
  ClassSession,
  ClassSessionList,
  DayGroup,
  PageResult,
  PrivateBooking,
  PrivateBookingStatus,
  PrivateBookingView,
  PrivateSlotList,
  PrivateSlotView,
} from "../types/member"
import { assignedSchedule, rosterBooking, workloadBooking } from "../utils/coach-presenter"
import { privateSlotGroups } from "../utils/member-presenter"

export class CoachService {
  constructor(
    private readonly api: ApiClient,
    private readonly idempotency: IdempotencyService,
    private readonly storage: StorageService,
  ) {}

  async schedule(weekStart: string): Promise<CoachScheduleGroups> {
    const response = await this.api.request<ClassSessionList>(
      `/class-sessions?weekStart=${encodeURIComponent(weekStart)}`,
    )
    return assignedSchedule(response.items)
  }

  async roster(sessionId: string): Promise<{ session: ClassSession; items: RosterBooking[] }> {
    const [session, bookings] = await Promise.all([
      this.api.request<ClassSession>(`/class-sessions/${encodeURIComponent(sessionId)}`),
      this.api.request<PageResult<ClassBooking>>(
        `/class-sessions/${encodeURIComponent(sessionId)}/bookings`,
      ),
    ])
    return { session, items: bookings.items.map((booking) => rosterBooking(booking, session)) }
  }

  async checkIn(bookingId: string): Promise<ClassBooking> {
    return idempotentMutation<ClassBooking>(
      this.api,
      this.idempotency,
      this.operationId("class-check-in", bookingId),
      `/class-bookings/${encodeURIComponent(bookingId)}/check-in`,
      { method: "POST", body: {} },
    )
  }

  async availability(dateFrom: string, dateTo: string): Promise<DayGroup<PrivateSlotView>[]> {
    const response = await this.api.request<PrivateSlotList>(
      `/private-slots?dateFrom=${encodeURIComponent(dateFrom)}&dateTo=${encodeURIComponent(dateTo)}`,
    )
    return privateSlotGroups(response.items)
  }

  async createSlot(input: PrivateAvailabilityInput): Promise<unknown> {
    return idempotentMutation(
      this.api,
      this.idempotency,
      this.operationId("slot-create", `${input.startAt}:${input.endAt}`),
      "/private-slots",
      { method: "POST", body: input },
    )
  }

  async updateSlot(slotId: string, input: PrivateAvailabilityInput): Promise<unknown> {
    return idempotentMutation(
      this.api,
      this.idempotency,
      this.operationId("slot-update", slotId),
      `/private-slots/${encodeURIComponent(slotId)}`,
      { method: "PATCH", body: input },
    )
  }

  async cancelSlot(slotId: string): Promise<unknown> {
    return idempotentMutation(
      this.api,
      this.idempotency,
      this.operationId("slot-cancel", slotId),
      `/private-slots/${encodeURIComponent(slotId)}`,
      { method: "DELETE" },
    )
  }

  async generateWeek(input: PrivateWeekInput): Promise<PrivateWeekResult> {
    return idempotentMutation<PrivateWeekResult>(
      this.api,
      this.idempotency,
      this.operationId("slot-generate-week", input.weekStart),
      "/private-slots/generate-week",
      { method: "POST", body: input },
    )
  }

  async workload(
    status: PrivateBookingStatus,
    skip = 0,
    limit = 20,
  ): Promise<PageResult<PrivateBookingView>> {
    const page = await this.api.request<PageResult<PrivateBooking>>(
      `/private-bookings?status=${encodeURIComponent(status)}&skip=${skip}&limit=${limit}`,
    )
    return { ...page, items: page.items.map(workloadBooking) }
  }

  async booking(bookingId: string): Promise<PrivateBooking> {
    return this.api.request(`/private-bookings/${encodeURIComponent(bookingId)}`)
  }

  async confirmPrivate(bookingId: string): Promise<PrivateBooking> {
    return this.privateAction("confirm", bookingId)
  }

  async rejectPrivate(bookingId: string, reason?: string): Promise<PrivateBooking> {
    return this.privateAction("reject", bookingId, { reason: reason || null })
  }

  async signInPrivate(bookingId: string, input: LessonInput): Promise<PrivateBooking> {
    return idempotentMutation<PrivateBooking>(
      this.api,
      this.idempotency,
      this.operationId("private-sign-in", bookingId),
      `/private-bookings/${encodeURIComponent(bookingId)}/sign-in`,
      { method: "POST", body: input },
    )
  }

  private async privateAction(
    action: "confirm" | "reject",
    bookingId: string,
    body: unknown = {},
  ): Promise<PrivateBooking> {
    return idempotentMutation<PrivateBooking>(
      this.api,
      this.idempotency,
      this.operationId(`private-${action}`, bookingId),
      `/private-bookings/${encodeURIComponent(bookingId)}/${action}`,
      { method: "POST", body },
    )
  }

  private operationId(action: string, resourceId: string): string {
    return `${this.storage.user()?.username ?? "coach"}:${action}:${resourceId}`
  }
}
