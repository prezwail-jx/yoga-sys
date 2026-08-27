import type {
  ClassBooking,
  ClassSession,
  DayGroup,
  PageResult,
  PrivateBooking,
  PrivateBookingStatus,
  PrivateSlot,
} from "./member"

export interface CoachScheduleItem extends ClassSession {
  statusLabel: string
  dateLabel: string
  timeLabel: string
  capacityLabel: string
}

export interface RosterBooking extends ClassBooking {
  statusLabel: string
  canCheckIn: boolean
  checkInMessage: string
}

export interface PrivateAvailabilityInput {
  startAt: string
  endAt: string
}

export interface PrivateWeekInput {
  weekStart: string
  weekdays: number[]
  startTime: string
  durationMinutes: number
}

export interface PrivateWeekConflict {
  startAt: string
  endAt: string
  reason: string
}

export interface PrivateWeekResult {
  created: PrivateSlot[]
  conflicts: PrivateWeekConflict[]
}

export interface LessonInput {
  content: string
  consumedHours: number
  memberStatusNotes?: string
}

export interface CoachWorkloadPage extends PageResult<PrivateBooking> {
  status: PrivateBookingStatus
}

export type CoachScheduleGroups = DayGroup<CoachScheduleItem>[]
