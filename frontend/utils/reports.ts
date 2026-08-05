import type { ReportSummary } from "~/types/domain"

export function formatReportSummaryRows(summary: ReportSummary | null | undefined) {
  return summary ? [
    { label: "总会员数", value: summary.totalMembers },
    { label: "活跃会员", value: summary.activeMembers },
    { label: "即将到期会员", value: summary.expiringSoonMembers },
    { label: "售卡收入", value: `¥${summary.cardSales}` },
    { label: "续费收入", value: `¥${summary.renewalSales}` },
    { label: "退款金额", value: `¥${summary.refundAmount}` },
    { label: "团课出勤率", value: `${Math.round(summary.attendanceRate * 100)}%` },
    { label: "满课率", value: `${Math.round(summary.fullClassRate * 100)}%` },
    { label: "私教完成数", value: summary.privateLessonCount },
    { label: "私教课时", value: summary.privateConsumedHours },
  ] : []
}
