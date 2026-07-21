import { describe, expect, it } from "vitest"
import type { ClassBooking, ClassSession } from "../../types/domain"
import { getMemberBookingAvailability, getMemberCancellationAvailability } from "../../utils/classBooking"

const startAt = "2026-07-20T10:00:00.000Z"
const session = {
  startAt,
  bookingOpenHoursBefore: 24,
  bookingCloseMinutesBefore: 60,
  cancelCutoffMinutesBefore: 120,
  status: "published",
  isFull: false,
  remainingCapacity: 3,
} as ClassSession

const booking = {
  startAt,
  status: "reserved",
  sessionStatus: "published",
} as ClassBooking

describe("member class booking availability", () => {
  it("allows booking only inside the configured window with capacity", () => {
    expect(getMemberBookingAvailability(session, false, Date.parse("2026-07-19T11:00:00.000Z")).available).toBe(true)
    expect(getMemberBookingAvailability(session, false, Date.parse("2026-07-19T09:00:00.000Z"))).toMatchObject({ available: false, reason: "not_open" })
    expect(getMemberBookingAvailability(session, true, Date.parse("2026-07-19T11:00:00.000Z"))).toMatchObject({ available: false, reason: "already_booked" })
    expect(getMemberBookingAvailability({ ...session, isFull: true }, false, Date.parse("2026-07-19T11:00:00.000Z"))).toMatchObject({ available: false, reason: "full" })
  })

  it("allows cancellation through the cutoff and rejects terminal bookings", () => {
    expect(getMemberCancellationAvailability(booking, 120, Date.parse("2026-07-20T08:00:00.000Z")).available).toBe(true)
    expect(getMemberCancellationAvailability(booking, 120, Date.parse("2026-07-20T08:00:00.001Z"))).toMatchObject({ available: false, reason: "cutoff_passed" })
    expect(getMemberCancellationAvailability({ ...booking, status: "checked_in" }, 120, Date.parse("2026-07-20T07:00:00.000Z"))).toMatchObject({ available: false, reason: "not_reserved" })
  })
})
