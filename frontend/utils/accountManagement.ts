type HttpError = { statusCode?: number; status?: number; response?: { status?: number } }

export function isUsernameConflict(error: unknown): boolean {
  const value = error as HttpError | null
  return value?.statusCode === 409 || value?.status === 409 || value?.response?.status === 409
}

export function accountOpeningError(error: unknown, resource: "会员" | "教练"): string {
  if (isUsernameConflict(error)) return "该用户名已存在。用户名在会员、教练和管理员账号中全局唯一，请更换后重试。"
  return `${resource}账号开通失败`
}

export function passwordValidationError(newPassword: string, confirmation?: string): string {
  if (newPassword.length < 8) return "新密码至少需要 8 位"
  if (confirmation !== undefined && newPassword !== confirmation) return "两次输入的新密码不一致"
  return ""
}

export function memberAccountPresentation(hasAccount: boolean): { label: string; action: "open" | "reset" } {
  return hasAccount ? { label: "已开通", action: "reset" } : { label: "未开通", action: "open" }
}

export function wechatBindingPresentation(bound: boolean): { label: string; description: string; action: "none" | "unbind" } {
  return bound
    ? { label: "已绑定微信", description: "该账号已绑定微信身份，解绑后用户需重新通过首次绑定流程关联微信。", action: "unbind" }
    : { label: "未绑定微信", description: "该账号尚未绑定微信身份。", action: "none" }
}
