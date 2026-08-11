import { describe, expect, it } from "vitest"
import { accountOpeningError, isUsernameConflict, memberAccountPresentation, passwordValidationError, wechatBindingPresentation } from "../../utils/accountManagement"

describe("account management rules", () => {
  it("recognizes proxied and direct username conflicts", () => {
    expect(isUsernameConflict({ statusCode: 409 })).toBe(true)
    expect(isUsernameConflict({ response: { status: 409 } })).toBe(true)
    expect(accountOpeningError({ statusCode: 409 }, "会员")).toContain("全局唯一")
  })

  it("validates password length and confirmation", () => {
    expect(passwordValidationError("short", "short")).toBe("新密码至少需要 8 位")
    expect(passwordValidationError("password-a", "password-b")).toBe("两次输入的新密码不一致")
    expect(passwordValidationError("password-a", "password-a")).toBe("")
  })

  it("selects the account status and management action from backend state", () => {
    expect(memberAccountPresentation(false)).toEqual({ label: "未开通", action: "open" })
    expect(memberAccountPresentation(true)).toEqual({ label: "已开通", action: "reset" })
  })

  it("presents WeChat binding status", () => {
    expect(wechatBindingPresentation(true)).toEqual({ label: "已绑定微信", description: expect.stringContaining("解绑"), action: "unbind" })
    expect(wechatBindingPresentation(false)).toEqual({ label: "未绑定微信", description: expect.stringContaining("尚未"), action: "none" })
  })
})
