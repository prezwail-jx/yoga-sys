import { describe, expect, it } from "vitest"
import { canCancelPendingPrivateBooking, canConfirmPrivateBooking, canRejectPrivateBooking, canSignInPrivateBooking } from "../../utils/privateTraining"
import { formatReportSummaryRows } from "../../utils/reports"

describe("private training role actions", () => {
  it("exposes pending decisions only to allowed roles", () => {
    expect(canConfirmPrivateBooking("coach", "pending")).toBe(true)
    expect(canRejectPrivateBooking("admin", "pending")).toBe(true)
    expect(canCancelPendingPrivateBooking("member", "pending")).toBe(true)
    expect(canCancelPendingPrivateBooking("coach", "pending")).toBe(false)
    expect(canConfirmPrivateBooking("member", "pending")).toBe(false)
  })

  it("allows sign-in only for admin or coach after confirmation", () => {
    expect(canSignInPrivateBooking("coach", "confirmed")).toBe(true)
    expect(canSignInPrivateBooking("admin", "confirmed")).toBe(true)
    expect(canSignInPrivateBooking("member", "confirmed")).toBe(false)
    expect(canSignInPrivateBooking("coach", "pending")).toBe(false)
  })
})

describe("report summary formatting", () => {
  it("formats money and percentage rows for the report grid", () => {
    const rows = formatReportSummaryRows({
      totalMembers: 12,
      activeMembers: 10,
      expiringSoonMembers: 2,
      cardSales: "1000.00",
      renewalSales: "200.00",
      refundAmount: "50.00",
      attendanceRate: 0.8,
      fullClassRate: 0.5,
      privateLessonCount: 3,
      privateConsumedHours: "4.5",
      privateCompletionRate: 0.75,
    })

    expect(rows).toContainEqual({ label: "售卡收入", value: "¥1000.00" })
    expect(rows).toContainEqual({ label: "团课出勤率", value: "80%" })
    expect(rows).toContainEqual({ label: "私教课时", value: "4.5" })
  })
})
