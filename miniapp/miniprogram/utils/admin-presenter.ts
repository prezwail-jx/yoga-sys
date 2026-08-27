import type { CardProduct, CardSummary, Member, MemberStatus, ReportSummary } from "../types/admin"
import type { ClassBookingStatus, ClassSessionStatus, MemberCardStatus, PrivateBookingStatus } from "../types/member"

export const memberStatusLabels: Record<MemberStatus, string> = { normal: "正常", paused: "暂停", expired: "已过期", disabled: "已停用" }
export const memberCardStatusLabels: Record<MemberCardStatus, string> = { pending_activation: "待激活", active: "使用中", frozen: "已冻结", expired: "已过期", closed: "已关闭" }
export const classSessionStatusLabels: Record<ClassSessionStatus, string> = { draft: "草稿", published: "已发布", paused: "已暂停", cancelled: "已取消", completed: "已完成" }
export const classBookingStatusLabels: Record<ClassBookingStatus, string> = { reserved: "已预约", checked_in: "已签到", cancelled: "已取消", absent: "缺席" }
export const privateBookingStatusLabels: Record<PrivateBookingStatus, string> = { pending: "待确认", confirmed: "已确认", rejected: "已拒绝", cancelled: "已取消", completed: "已完成" }
export const privateSlotStatusLabels = { available: "可预约", locked: "已占用", cancelled: "已取消" } as const
export const cardTypeLabels = { duration: "期限卡", times: "次数卡", private: "私教卡", trial: "体验卡" } as const
const RAW_VALUE_LABELS: Record<string, string> = {
  ...memberStatusLabels, ...memberCardStatusLabels, ...classSessionStatusLabels,
  ...classBookingStatusLabels, ...privateBookingStatusLabels, ...privateSlotStatusLabels,
  purchase: "购卡", renew: "续费", reissue: "补卡", refund: "退款", freeze: "冻结",
  unfreeze: "解冻", extend: "延期", adjust: "调整次数", success: "成功",
  rejected: "已拒绝", failed: "失败", transaction: "卡交易", writeoff: "权益核销", audit: "审计记录",
}

export function localizedValue(value: unknown): string {
  const text = String(value)
  return RAW_VALUE_LABELS[text] ?? text
}

const SCHEDULING_CONFLICT_LABELS: Record<string, string> = {
  course_disabled: "课程已停用", coach_disabled: "教练已停用", room_disabled: "教室已停用",
  room_capacity_exceeded: "课次容量超过教室容量", coach_time_conflict: "教练同期已有团课",
  room_time_conflict: "教室同期已被占用", coach_private_time_conflict: "教练同期已有私教",
  private_slot_in_past: "时段已经过去", invalid_time_range: "结束时间必须晚于开始时间",
  private_slot_time_conflict: "教练已有重叠私教时段", coach_class_time_conflict: "教练同期已有团课",
}

export function schedulingConflictLabel(reason: string): string {
  return SCHEDULING_CONFLICT_LABELS[reason] ?? reason
}

export function cardSummaryLabel(card: CardSummary): string {
  const balance = card.remainingTimes === null ? "不限次数" : `剩余 ${card.remainingTimes} 次`
  return `${card.productName} · ${memberCardStatusLabels[card.status]} · ${balance}${card.expiresOn ? ` · ${card.expiresOn} 到期` : ""}`
}

export function memberView(member: Member) {
  return { ...member, statusLabel: memberStatusLabels[member.status], cardLabels: member.cardSummaries.map(cardSummaryLabel) }
}

export function productView(product: CardProduct) {
  return { ...product, typeLabel: cardTypeLabels[product.cardType], enabledLabel: product.enabled ? "已启用" : "已停用", ruleLabel: product.totalTimes === null ? `${product.validDays ?? "长期"} 天` : `${product.totalTimes} 次 / ${product.validDays ?? "未设置"} 天` }
}

export function reportMetrics(summary: ReportSummary) {
  return [
    { label: "会员总数", value: String(summary.totalMembers) },
    { label: "正常会员", value: String(summary.activeMembers) },
    { label: "即将到期", value: String(summary.expiringSoonMembers) },
    { label: "购卡收入", value: `¥${summary.cardSales}` },
    { label: "续费收入", value: `¥${summary.renewalSales}` },
    { label: "退款金额", value: `¥${summary.refundAmount}` },
    { label: "团课出勤率", value: `${Math.round(summary.attendanceRate * 100)}%` },
    { label: "私教完成数", value: String(summary.privateLessonCount) },
  ]
}
