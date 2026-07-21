import { describe, expect, it } from "vitest"
import { getApiErrorMessage } from "../../utils/errors"

describe("getApiErrorMessage", () => {
  it("uses the fallback for an empty async-data error", () => {
    expect(getApiErrorMessage(null, "加载失败")).toBe("加载失败")
  })

  it("prefers backend detail when present", () => {
    expect(getApiErrorMessage({ data: { detail: "预约已截止" } }, "预约失败")).toBe("预约已截止")
  })
})
