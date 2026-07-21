import type { ClassBooking, ClassSession } from "~/types/domain"

export type MemberBookingAvailability =
  | { available: true; opensAt: number; closesAt: number }
  | {
    available: false
    reason: "already_booked" | "not_published" | "full" | "not_open" | "closed"
    opensAt: number
    closesAt: number
  }

export type MemberCancellationAvailability =
  | { available: true; cutoffAt: number }
  | { available: false; reason: "not_reserved" | "session_terminal" | "cutoff_passed"; cutoffAt: number }

export function getMemberBookingAvailability(
  session: ClassSession,
  alreadyBooked: boolean,
  now: number,
): MemberBookingAvailability {
  const opensAt = new Date(session.startAt).getTime() - session.bookingOpenHoursBefore * 60 * 60 * 1000
  const closesAt = new Date(session.startAt).getTime() - session.bookingCloseMinutesBefore * 60 * 1000

  if (alreadyBooked) return { available: false, reason: "already_booked", opensAt, closesAt }
  if (session.status !== "published") return { available: false, reason: "not_published", opensAt, closesAt }
  if (now < opensAt) return { available: false, reason: "not_open", opensAt, closesAt }
  if (now >= closesAt) return { available: false, reason: "closed", opensAt, closesAt }
  if (session.isFull || session.remainingCapacity <= 0) {
    return { available: false, reason: "full", opensAt, closesAt }
  }
  return { available: true, opensAt, closesAt }
}

export function getMemberCancellationAvailability(
  booking: ClassBooking,
  cancelCutoffMinutesBefore: number,
  now: number,
): MemberCancellationAvailability {
  const cutoffAt = new Date(booking.startAt).getTime() - cancelCutoffMinutesBefore * 60 * 1000
  if (booking.status !== "reserved") return { available: false, reason: "not_reserved", cutoffAt }
  if (booking.sessionStatus === "cancelled" || booking.sessionStatus === "completed") {
    return { available: false, reason: "session_terminal", cutoffAt }
  }
  if (now > cutoffAt) return { available: false, reason: "cutoff_passed", cutoffAt }
  return { available: true, cutoffAt }
}

export type CheckInAvailability =
  | { available: true; opensAt: number }
  | { available: false; reason: "not_open" | "not_published" | "terminal"; opensAt: number }

export function getCheckInAvailability(session: ClassSession, now: number): CheckInAvailability {
  const opensAt = new Date(session.startAt).getTime() - 30 * 60 * 1000
  if (session.status === "cancelled" || session.status === "completed") {
    return { available: false, reason: "terminal", opensAt }
  }
  if (session.status !== "published") {
    return { available: false, reason: "not_published", opensAt }
  }
  if (now < opensAt) {
    return { available: false, reason: "not_open", opensAt }
  }
  return { available: true, opensAt }
}
