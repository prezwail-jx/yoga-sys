export type ClassSessionStatus = "draft" | "published" | "paused" | "cancelled" | "completed"
export type ClassBookingStatus = "reserved" | "checked_in" | "cancelled" | "absent"
export type PrivateBookingStatus = "pending" | "confirmed" | "rejected" | "cancelled" | "completed"
export type MemberCardStatus = "pending_activation" | "active" | "frozen" | "expired" | "closed"

export interface ClassSession {
  id: string
  courseId: string
  coachProfileId: string
  roomId: string
  courseName: string
  coachName: string
  roomName: string
  startAt: string
  endAt: string
  capacity: number
  bookingOpenHoursBefore: number
  bookingCloseMinutesBefore: number
  cancelCutoffMinutesBefore: number
  status: ClassSessionStatus
  bookedCount: number
  remainingCapacity: number
  isFull: boolean
}

export interface ClassSessionList {
  items: ClassSession[]
  weekStart: string
  weekEnd: string
}

export interface ClassBooking {
  id: string
  classSessionId: string
  memberId: string
  memberName: string
  courseName: string
  coachName: string
  roomName: string
  startAt: string
  endAt: string
  sessionStatus: ClassSessionStatus
  status: ClassBookingStatus
  bookedAt: string
  terminalAt?: string
  cancellationReason?: string
}

export interface PrivateSlot {
  id: string
  coachProfileId: string
  coachName: string
  startAt: string
  endAt: string
  durationMinutes: number
  status: "available" | "locked" | "cancelled"
}

export interface PrivateSlotList {
  items: PrivateSlot[]
  total: number
}

export interface PrivateBooking {
  id: string
  availabilityId: string
  memberId: string
  memberName: string
  coachProfileId: string
  coachName: string
  startAt: string
  endAt: string
  durationMinutes: number
  status: PrivateBookingStatus
  memberMessage?: string
  rejectionReason?: string
  cancellationReason?: string
  confirmedAt?: string
}

export interface MemberCard {
  id: string
  productName: string
  cardType: "times" | "duration" | "private" | "trial"
  status: MemberCardStatus
  remainingTimes: number | null
  openedOn: string | null
  expiresOn: string | null
  frozenFrom: string | null
  frozenUntil: string | null
}

export interface MemberCardView extends MemberCard {
  statusLabel: string
  typeLabel: string
  balanceLabel: string
  validityLabel: string
  freezeLabel: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export interface ClassScheduleItem extends ClassSession {
  statusLabel: string
  dateLabel: string
  timeLabel: string
  capacityLabel: string
  myBookingId: string | null
  myBookingStatus: ClassBookingStatus | null
  canBook: boolean
  actionLabel: string
}

export interface ClassBookingView extends ClassBooking {
  statusLabel: string
  dateLabel: string
  timeLabel: string
  canCancel: boolean
  cutoffMessage: string
}

export interface PrivateSlotView extends PrivateSlot {
  statusLabel: string
  dateLabel: string
  timeLabel: string
}

export interface PrivateBookingView extends PrivateBooking {
  statusLabel: string
  dateLabel: string
  timeLabel: string
  canCancel: boolean
}

export interface DayGroup<T> {
  dateKey: string
  dateLabel: string
  items: T[]
}
