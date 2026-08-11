import { describe, expect, it } from "vitest"

import type { ClassBooking, ClassSession, MemberCard } from "../miniprogram/types/member"
import {
  classBookingView,
  groupClassSchedule,
  memberCardView,
  mondayOf,
  shiftWeek,
} from "../miniprogram/utils/member-presenter"

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

describe("member presenters", () => {
  it("groups schedules chronologically in Shanghai time and joins booking state", () => {
    const groups = groupClassSchedule([
      session({ id: "session-2", startAt: "2030-01-08T03:00:00Z", endAt: "2030-01-08T04:00:00Z" }),
      session(),
      session({ id: "draft", status: "draft" }),
    ], [booking()])

    expect(groups.map((group) => group.dateKey)).toEqual(["2030-01-07", "2030-01-08"])
    expect(groups[0].items[0]).toMatchObject({
      timeLabel: "09:00 - 10:00",
      myBookingId: "booking-1",
      actionLabel: "已预约",
      canBook: false,
    })
    expect(groups[1].items[0].canBook).toBe(true)
  })

  it("calculates natural weeks and cancellation cutoff messaging", () => {
    expect(mondayOf(new Date("2030-01-09T12:00:00+08:00")).toISOString()).toBe("2030-01-06T16:00:00.000Z")
    expect(shiftWeek("2030-01-07", 1)).toBe("2030-01-14")
    const cancellable = classBookingView(
      booking(),
      session(),
      new Date("2030-01-07T06:00:00+08:00"),
    )
    expect(cancellable.canCancel).toBe(true)
    expect(cancellable.cutoffMessage).toContain("01-07 07:00")
    const late = classBookingView(booking(), session(), new Date("2030-01-07T08:00:00+08:00"))
    expect(late.canCancel).toBe(false)
    expect(late.cutoffMessage).toBe("已超过可取消时间")
  })

  it("presents card balance, validity and freeze data without mutation fields", () => {
    const card: MemberCard = {
      id: "card-1",
      productName: "十次卡",
      cardType: "times",
      status: "frozen",
      remainingTimes: 6,
      openedOn: "2030-01-01",
      expiresOn: "2030-06-01",
      frozenFrom: "2030-02-01",
      frozenUntil: "2030-02-10",
    }
    expect(memberCardView(card)).toMatchObject({
      typeLabel: "次数卡",
      balanceLabel: "剩余 6 次",
      validityLabel: "2030-01-01 至 2030-06-01",
      freezeLabel: "2030-02-01 至 2030-02-10",
    })
    expect(Object.keys(memberCardView(card))).not.toContain("refundableTransactionId")
  })
})
