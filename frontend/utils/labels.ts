import type { TimelineCategory } from "~/types/domain"

export function label(map: Record<string, string>, value: string | null | undefined): string {
  if (!value) return ""
  return map[value] || value
}

export const memberStatusLabels: Record<string, string> = {
  normal: "正常",
  paused: "暂停",
  expired: "到期",
  disabled: "禁用",
}

export const cardTypeLabels: Record<string, string> = {
  duration: "期限卡",
  times: "次数卡",
  private: "私教卡",
  trial: "体验卡",
}

export const memberCardStatusLabels: Record<string, string> = {
  pending_activation: "待激活",
  active: "使用中",
  frozen: "冻结中",
  expired: "已过期",
  closed: "已关闭",
}

export const userRoleLabels: Record<string, string> = {
  admin: "管理员",
  coach: "教练",
  member: "会员",
  system: "系统",
}

export const privateSlotStatusLabels: Record<string, string> = {
  available: "可预约",
  locked: "已锁定",
  cancelled: "已取消",
}

export const privateBookingStatusLabels: Record<string, string> = {
  pending: "待确认",
  confirmed: "已确认",
  rejected: "已拒绝",
  cancelled: "已取消",
  completed: "已完成",
}

export const timelineResultLabels: Record<string, string> = {
  success: "成功",
  rejected: "已拒绝",
  failed: "失败",
}

export const timelineSourceLabels: Record<string, string> = {
  transaction: "卡项交易",
  writeoff: "核销事件",
  audit: "操作审计",
}

export const reportDetailHeaderLabels: Record<string, string> = {
  bookingId: "预约ID",
  cardName: "卡项名称",
  coachName: "教练",
  completedAt: "完成时间",
  consumedHours: "消耗课时",
  content: "上课内容",
  courseName: "课程",
  expiresOn: "到期日期",
  lessonId: "课次ID",
  memberCardId: "会员卡ID",
  memberId: "会员ID",
  memberName: "会员",
  occurredAt: "发生时间",
  reason: "原因",
  remainingTimes: "剩余次数",
  sessionId: "课次ID",
  startAt: "开始时间",
  status: "状态",
  transactionId: "交易ID",
  type: "类型",
  amount: "金额",
}

export const reportTransactionTypeLabels: Record<string, string> = {
  purchase: "购卡",
  renew: "续费",
  refund: "退款",
}

export const reportClassBookingStatusLabels: Record<string, string> = {
  reserved: "已预约",
  checked_in: "已签到",
  cancelled: "已取消",
  absent: "缺勤",
}

export function reportHeaderLabel(key: string): string {
  return reportDetailHeaderLabels[key] || key
}

export function timelineCategoryLabel(category: TimelineCategory): string {
  const labels: Record<TimelineCategory, string> = {
    all: "全部类别",
    transaction: "卡项交易",
    writeoff: "核销事件",
    audit: "操作审计",
  }
  return labels[category]
}
