type ApiError = {
  statusCode?: number
  status?: number
  statusMessage?: string
  response?: { status?: number }
  data?: {
    detail?: string
    traceId?: string
    statusMessage?: string
    data?: { detail?: string; traceId?: string }
  }
}

const detailMessages: Record<string, string> = {
  invalid_time_range: "结束时间必须晚于开始时间。",
  private_slot_time_conflict: "该教练已有重叠的私教时段，请调整时间。",
  coach_class_time_conflict: "该教练同期已有团课，请调整时间。",
  "Private slot is not available": "该私教时段已不可预约，请刷新后选择其他时间。",
  "Private slot is in the past": "不能预约已开始或已结束的私教时段。",
  "Member has overlapping private booking": "您在该时间已有私教预约。",
  "Member has overlapping class booking": "您在该时间已有团课预约。",
  "Booking is not pending": "该预约已被处理，请刷新后查看最新状态。",
  "Booking is not confirmed": "只有已确认的预约才能签到。",
  "No eligible member card": "该会员没有可用的私教卡，请检查卡状态、有效期和适用范围。",
  "Member card has no remaining times": "该会员的私教卡次数已用完。",
  "Member status does not allow write-off": "该会员当前状态不允许私教卡核销。",
}

export function privateTrainingErrorMessage(error: unknown, fallback: string): string {
  const value = error as ApiError | null
  const status = value?.statusCode || value?.status || value?.response?.status
  const detail = value?.data?.detail || value?.data?.data?.detail || value?.data?.statusMessage || value?.statusMessage
  const traceId = value?.data?.traceId || value?.data?.data?.traceId
  if (detail && detailMessages[detail]) return detailMessages[detail]
  if (status === 401) return "登录状态已失效，请重新登录后继续。"
  if (status === 403) return "当前账号没有权限执行此操作。"
  if (status === 409) return detail || "当前状态发生冲突，请刷新后重试。"
  if (status === 422) return detail || "提交内容不完整或格式不正确，请检查后重试。"
  if (status && status >= 500) {
    return traceId
      ? `${fallback}，请联系管理员并提供追踪编号：${traceId}`
      : `${fallback}，请稍后重试。`
  }
  return detail || fallback
}
