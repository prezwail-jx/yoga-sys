import type { ClassBooking, ClassSession, DayGroup, PrivateBooking, PrivateBookingView } from "../types/member"
import type { CoachScheduleItem, RosterBooking } from "../types/coach"
import { dateKey, dateLabel, privateBookingView, timeLabel } from "./member-presenter"

const SESSION_STATUS_LABELS = { draft: "草稿", published: "已发布", paused: "已暂停", cancelled: "已取消", completed: "已完成" } as const
const BOOKING_STATUS_LABELS = { reserved: "已预约", checked_in: "已签到", cancelled: "已取消", absent: "缺席" } as const

function groupByDay(items: CoachScheduleItem[]): DayGroup<CoachScheduleItem>[] {
  const groups = new Map<string, DayGroup<CoachScheduleItem>>()
  for (const item of [...items].sort((left, right) => left.startAt.localeCompare(right.startAt))) {
    const key = dateKey(item.startAt)
    const group = groups.get(key) ?? { dateKey: key, dateLabel: item.dateLabel, items: [] }
    group.items.push(item)
    groups.set(key, group)
  }
  return [...groups.values()]
}

export function assignedSchedule(sessions: ClassSession[]): DayGroup<CoachScheduleItem>[] {
  return groupByDay(sessions.map((session) => ({
    ...session,
    statusLabel: SESSION_STATUS_LABELS[session.status],
    dateLabel: dateLabel(session.startAt),
    timeLabel: timeLabel(session.startAt, session.endAt),
    capacityLabel: `${session.bookedCount}/${session.capacity}`,
  })))
}

export function rosterBooking(
  booking: ClassBooking,
  session: ClassSession,
  now = new Date(),
): RosterBooking {
  const opensAt = new Date(new Date(session.startAt).getTime() - 30 * 60_000)
  const canCheckIn = booking.status === "reserved"
    && session.status === "published"
    && now >= opensAt
  const checkInMessage = booking.status !== "reserved"
    ? booking.status === "checked_in" ? "已签到" : "预约已结束"
    : session.status !== "published"
      ? "课次不可签到"
      : now < opensAt
        ? "开课前 30 分钟开放签到"
        : "可签到"
  return { ...booking, statusLabel: BOOKING_STATUS_LABELS[booking.status], canCheckIn, checkInMessage }
}

export function workloadBooking(booking: PrivateBooking): PrivateBookingView {
  return privateBookingView(booking)
}

export function validateLessonInput(content: string, consumedHours: number): string | null {
  if (!content.trim()) return "请填写本次训练内容"
  if (!Number.isFinite(consumedHours) || consumedHours <= 0 || consumedHours > 24) {
    return "消耗课时必须大于 0 且不超过 24"
  }
  return null
}
