import { describe, expect, it } from "vitest"

import type { ClassBooking, ClassSession, PrivateBooking } from "../miniprogram/types/member"
import {
  assignedSchedule,
  rosterBooking,
  validateLessonInput,
  workloadBooking,
} from "../miniprogram/utils/coach-presenter"

function session(changes: Partial<ClassSession> = {}): ClassSession {
  return {
    id: "session-1",
    courseId: "course-1",
    coachProfileId: "coach-1",
    roomId: "room-1",
    courseName: "流瑜伽",
    coachName: "周教练",
    roomName: "一号教室",
    startAt: "2030-01-07T01:00:00Z",
    endAt: "2030-01-07T02:00:00Z",
    capacity: 10,
    bookingOpenHoursBefore: 168,
    bookingCloseMinutesBefore: 0,
    cancelCutoffMinutesBefore: 120,
    status: "published",
    bookedCount: 3,
    remainingCapacity: 7,
    isFull: false,
    ...changes,
  }
}

function booking(changes: Partial<ClassBooking> = {}): ClassBooking {
  return {
    id: "booking-1",
    classSessionId: "session-1",
    memberId: "member-1",
    memberName: "林会员",
    courseName: "流瑜伽",
    coachName: "周教练",
    roomName: "一号教室",
    startAt: "2030-01-07T01:00:00Z",
    endAt: "2030-01-07T02:00:00Z",
    sessionStatus: "published",
    status: "reserved",
    bookedAt: "2030-01-01T00:00:00Z",
    ...changes,
  }
}

describe("coach presenters", () => {
  it("groups assigned sessions by Shanghai day and start time", () => {
    const groups = assignedSchedule([
      session({ id: "later", startAt: "2030-01-08T03:00:00Z", endAt: "2030-01-08T04:00:00Z" }),
      session(),
    ])

    expect(groups.map((group) => group.dateKey)).toEqual(["2030-01-07", "2030-01-08"])
    expect(groups[0].items[0]).toMatchObject({
      timeLabel: "09:00 - 10:00",
      capacityLabel: "3/10",
      roomName: "一号教室",
    })
  })

  it("opens class check-in thirty minutes before class and respects terminal states", () => {
    expect(rosterBooking(booking(), session(), new Date("2030-01-07T00:29:59Z"))).toMatchObject({
      canCheckIn: false,
      checkInMessage: "开课前 30 分钟开放签到",
    })
    expect(rosterBooking(booking(), session(), new Date("2030-01-07T00:30:00Z"))).toMatchObject({
      canCheckIn: true,
      checkInMessage: "可签到",
    })
    expect(rosterBooking(booking({ status: "checked_in" }), session())).toMatchObject({
      canCheckIn: false,
      checkInMessage: "已签到",
    })
  })

  it("preserves the five-state private workload presentation", () => {
    const item: PrivateBooking = {
      id: "private-1",
      availabilityId: "slot-1",
      coachProfileId: "coach-1",
      memberId: "member-1",
      memberName: "林会员",
      coachName: "周教练",
      startAt: "2030-01-08T01:00:00Z",
      endAt: "2030-01-08T02:00:00Z",
      durationMinutes: 60,
      status: "pending",
      memberMessage: "改善肩颈",
    }

    expect(workloadBooking(item)).toMatchObject({ status: "pending", canCancel: true })
    expect(workloadBooking({ ...item, status: "confirmed" })).toMatchObject({
      status: "confirmed",
      canCancel: false,
    })
  })

  it("validates private lesson content and consumed hours", () => {
    expect(validateLessonInput("  ", 1)).toBe("请填写本次训练内容")
    expect(validateLessonInput("肩颈拉伸", 0)).toBe("消耗课时必须大于 0 且不超过 24")
    expect(validateLessonInput("肩颈拉伸", 25)).toBe("消耗课时必须大于 0 且不超过 24")
    expect(validateLessonInput("肩颈拉伸", 1.5)).toBeNull()
  })
})
