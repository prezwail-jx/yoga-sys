import { describe, expect, it } from "vitest"
import type { TimelineEvent } from "../../types/domain"
import { orderWriteoffChain, writeoffChainStatus } from "../../utils/timeline"

const event = (action: string, sequenceNo: number, timesDelta = 0): TimelineEvent => ({
  id: `${action}-id`, source: "writeoff", action, result: "success",
  occurredAt: "2026-07-17T01:00:00Z", traceId: "trace", memberCardId: "card",
  businessRef: "booking-1", sequenceNo, timesDelta, amount: null,
  productName: null, cardType: null, validDaysDelta: null, reason: null,
  operatorId: "admin", operatorRole: "admin", objectType: "writeoff_event",
  objectId: `${action}-id`, summary: action,
})

describe("write-off chain helpers", () => {
  it("orders reserve before terminal event", () => {
    expect(orderWriteoffChain([event("checkin_commit", 2), event("reserve_hold", 1)]).map(item => item.sequenceNo)).toEqual([1, 2])
  })
  it("labels absence refund and incomplete chains", () => {
    expect(writeoffChainStatus([event("reserve_hold", 1), event("absence_commit", 2, 1)])).toBe("缺勤返还")
    expect(writeoffChainStatus([event("reserve_hold", 1)])).toBe("链路未完成")
  })
})
