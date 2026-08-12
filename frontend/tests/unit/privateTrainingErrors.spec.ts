import { describe, expect, it } from "vitest"

import { privateTrainingErrorMessage } from "../../utils/privateTrainingErrors"

describe("privateTrainingErrorMessage", () => {
  it("maps known scheduling conflicts", () => {
    expect(privateTrainingErrorMessage({ statusCode: 409, data: { detail: "private_slot_time_conflict" } }, "失败"))
      .toBe("该教练已有重叠的私教时段，请调整时间。")
  })

  it("reads backend details from the Nitro production error envelope", () => {
    const error = {
      statusCode: 409,
      data: {
        statusMessage: "No eligible member card",
        data: { detail: "No eligible member card" },
      },
    }

    expect(privateTrainingErrorMessage(error, "操作失败"))
      .toBe("该会员没有可用的私教卡，请检查卡状态、有效期和适用范围。")
  })

  it("maps private-card eligibility failures", () => {
    expect(privateTrainingErrorMessage({ statusCode: 409, data: { detail: "Member card has no remaining times" } }, "失败"))
      .toBe("该会员的私教卡次数已用完。")
    expect(privateTrainingErrorMessage({ statusCode: 409, data: { detail: "Member status does not allow write-off" } }, "失败"))
      .toBe("该会员当前状态不允许私教卡核销。")
  })

  it("maps authorization and validation failures", () => {
    expect(privateTrainingErrorMessage({ statusCode: 403 }, "失败")).toBe("当前账号没有权限执行此操作。")
    expect(privateTrainingErrorMessage({ statusCode: 422 }, "失败")).toContain("提交内容")
  })

  it("preserves trace context for unexpected failures", () => {
    expect(privateTrainingErrorMessage({ statusCode: 500, data: { traceId: "trace-123" } }, "创建时段失败"))
      .toContain("trace-123")
    expect(privateTrainingErrorMessage({ statusCode: 500, data: { data: { traceId: "trace-nested" } } }, "创建时段失败"))
      .toContain("trace-nested")
  })
})
