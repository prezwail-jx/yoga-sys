import type {
  ClassBooking,
  ClassBookingView,
  ClassScheduleItem,
  ClassSession,
  DayGroup,
  PrivateBooking,
  PrivateBookingView,
  PrivateSlot,
  PrivateSlotView,
  MemberCard,
  MemberCardView,
} from "../types/member"

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
const CARD_TYPE_LABELS: Record<MemberCard["cardType"], string> = {
  times: "次数卡",
  duration: "期限卡",
  private: "私教卡",
  trial: "体验卡",
}
const CARD_STATUS_LABELS = { pending_activation: "待激活", active: "使用中", frozen: "已冻结", expired: "已过期", closed: "已关闭" } as const
const SESSION_STATUS_LABELS = { draft: "草稿", published: "已发布", paused: "已暂停", cancelled: "已取消", completed: "已完成" } as const
const BOOKING_STATUS_LABELS = { reserved: "已预约", checked_in: "已签到", cancelled: "已取消", absent: "缺席" } as const
const PRIVATE_STATUS_LABELS = { pending: "待确认", confirmed: "已确认", rejected: "已拒绝", cancelled: "已取消", completed: "已完成" } as const
const SLOT_STATUS_LABELS = { available: "可预约", locked: "已占用", cancelled: "已取消" } as const
const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000

function pad(value: number): string {
  return String(value).padStart(2, "0")
}

function shanghai(value: string | Date): Date {
  const date = value instanceof Date ? value : new Date(value)
  return new Date(date.getTime() + SHANGHAI_OFFSET_MS)
}

export function dateKey(value: string | Date): string {
  const date = shanghai(value)
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`
}

export function dateLabel(value: string | Date): string {
  const date = shanghai(value)
  return `${date.getUTCMonth() + 1}月${date.getUTCDate()}日 ${WEEKDAYS[date.getUTCDay()]}`
}

export function timeLabel(startAt: string, endAt: string): string {
  const start = new Date(startAt)
  const end = new Date(endAt)
  const localStart = shanghai(start)
  const localEnd = shanghai(end)
  return `${pad(localStart.getUTCHours())}:${pad(localStart.getUTCMinutes())} - ${pad(localEnd.getUTCHours())}:${pad(localEnd.getUTCMinutes())}`
}

export function mondayOf(date: Date): Date {
  const local = shanghai(date)
  const offset = (local.getUTCDay() + 6) % 7
  return new Date(Date.UTC(local.getUTCFullYear(), local.getUTCMonth(), local.getUTCDate() - offset) - SHANGHAI_OFFSET_MS)
}

export function shiftWeek(weekStart: string, weeks: number): string {
  const date = new Date(`${weekStart}T00:00:00+08:00`)
  date.setDate(date.getDate() + weeks * 7)
  return dateKey(date)
}

function groupByDay<T extends { startAt: string; dateLabel: string }>(items: T[]): DayGroup<T>[] {
  const groups = new Map<string, DayGroup<T>>()
  for (const item of [...items].sort((left, right) => left.startAt.localeCompare(right.startAt))) {
    const key = dateKey(item.startAt)
    const group = groups.get(key) ?? { dateKey: key, dateLabel: item.dateLabel, items: [] }
    group.items.push(item)
    groups.set(key, group)
  }
  return [...groups.values()]
}

export function groupClassSchedule(sessions: ClassSession[], bookings: ClassBooking[]): DayGroup<ClassScheduleItem>[] {
  const active = new Map(
    bookings
      .filter((booking) => booking.status === "reserved" || booking.status === "checked_in")
      .map((booking) => [booking.classSessionId, booking]),
  )
  const items = sessions
    .filter((session) => session.status !== "draft")
    .map((session): ClassScheduleItem => {
      const booking = active.get(session.id)
      const canBook = session.status === "published" && !session.isFull && !booking
      return {
        ...session,
        statusLabel: SESSION_STATUS_LABELS[session.status],
        dateLabel: dateLabel(session.startAt),
        timeLabel: timeLabel(session.startAt, session.endAt),
        capacityLabel: `${session.bookedCount}/${session.capacity}`,
        myBookingId: booking?.id ?? null,
        myBookingStatus: booking?.status ?? null,
        canBook,
        actionLabel: booking ? (booking.status === "checked_in" ? "已签到" : "已预约") : session.isFull ? "已满" : session.status === "published" ? "预约" : "不可预约",
      }
    })
  return groupByDay(items)
}

export function classBookingView(booking: ClassBooking, session: ClassSession | null, now = new Date()): ClassBookingView {
  const cutoff = session
    ? new Date(new Date(booking.startAt).getTime() - session.cancelCutoffMinutesBefore * 60_000)
    : null
  const canCancel = booking.status === "reserved"
    && booking.sessionStatus !== "cancelled"
    && booking.sessionStatus !== "completed"
    && Boolean(cutoff && now < cutoff)
  const cutoffMessage = booking.status !== "reserved"
    ? "预约已结束"
    : !cutoff
      ? "取消时间以服务端校验为准"
      : canCancel
        ? `可在 ${dateKey(cutoff).slice(5)} ${timeLabel(cutoff.toISOString(), cutoff.toISOString()).slice(0, 5)} 前取消`
        : "已超过可取消时间"
  return {
    ...booking,
    statusLabel: BOOKING_STATUS_LABELS[booking.status],
    dateLabel: dateLabel(booking.startAt),
    timeLabel: timeLabel(booking.startAt, booking.endAt),
    canCancel,
    cutoffMessage,
  }
}

export function privateSlotGroups(slots: PrivateSlot[]): DayGroup<PrivateSlotView>[] {
  return groupByDay(slots.map((slot) => ({
    ...slot,
    statusLabel: SLOT_STATUS_LABELS[slot.status],
    dateLabel: dateLabel(slot.startAt),
    timeLabel: timeLabel(slot.startAt, slot.endAt),
  })))
}

export function privateBookingView(booking: PrivateBooking): PrivateBookingView {
  return {
    ...booking,
    statusLabel: PRIVATE_STATUS_LABELS[booking.status],
    dateLabel: dateLabel(booking.startAt),
    timeLabel: timeLabel(booking.startAt, booking.endAt),
    canCancel: booking.status === "pending",
  }
}

export function memberCardView(card: MemberCard): MemberCardView {
  return {
    ...card,
    statusLabel: CARD_STATUS_LABELS[card.status],
    typeLabel: CARD_TYPE_LABELS[card.cardType],
    balanceLabel: card.remainingTimes === null ? "按有效期使用" : `剩余 ${card.remainingTimes} 次`,
    validityLabel: card.openedOn || card.expiresOn
      ? `${card.openedOn ?? "待开卡"} 至 ${card.expiresOn ?? "长期"}`
      : "待激活",
    freezeLabel: card.frozenFrom || card.frozenUntil
      ? `${card.frozenFrom ?? ""} 至 ${card.frozenUntil ?? ""}`
      : "",
  }
}
