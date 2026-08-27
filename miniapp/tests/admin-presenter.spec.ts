import { describe, expect, it } from "vitest"
import { cardSummaryLabel, classBookingStatusLabels, classSessionStatusLabels, localizedValue, memberCardStatusLabels, privateBookingStatusLabels, reportMetrics, schedulingConflictLabel } from "../miniprogram/utils/admin-presenter"

describe("admin presenter", () => {
  it("maps all business statuses to Chinese labels", () => {
    expect(Object.values(memberCardStatusLabels)).toEqual(["待激活", "使用中", "已冻结", "已过期", "已关闭"])
    expect(classSessionStatusLabels.cancelled).toBe("已取消")
    expect(classBookingStatusLabels.checked_in).toBe("已签到")
    expect(privateBookingStatusLabels.pending).toBe("待确认")
  })

  it("formats card summaries without exposing raw enums", () => {
    const label = cardSummaryLabel({ id: "card-1", productName: "十次卡", cardType: "times", status: "active", remainingTimes: 8, expiresOn: "2026-12-31" })
    expect(label).toBe("十次卡 · 使用中 · 剩余 8 次 · 2026-12-31 到期")
    expect(label).not.toContain("active")
  })

  it("formats real report summary metrics", () => {
    const metrics = reportMetrics({ totalMembers: 10, activeMembers: 8, expiringSoonMembers: 2, cardSales: "1000.00", renewalSales: "200.00", refundAmount: "50.00", attendanceRate: 0.75, fullClassRate: 0.5, privateLessonCount: 3, privateConsumedHours: "4", privateCompletionRate: 0.6 })
    expect(metrics).toContainEqual({ label: "团课出勤率", value: "75%" })
  })

  it("localizes enum values found in generic report details", () => {
    expect(localizedValue("pending_activation")).toBe("待激活")
    expect(localizedValue("refund")).toBe("退款")
  })

  it("localizes scheduling conflict codes", () => {
    expect(schedulingConflictLabel("coach_private_time_conflict")).toBe("教练同期已有私教")
    expect(schedulingConflictLabel("private_slot_in_past")).toBe("时段已经过去")
  })
})
