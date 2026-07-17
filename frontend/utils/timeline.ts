import type { TimelineEvent } from "~/types/domain"

export const timelineActionLabels: Record<string, string> = {
  purchase: "购卡", renew: "续费", reissue: "补卡", refund: "退款",
  freeze: "冻结", unfreeze: "解冻", extend: "延期",
  reserve_hold: "预约预扣", checkin_commit: "签到实扣",
  cancel_refund: "取消预约", absence_commit: "缺勤处理",
}

export function orderWriteoffChain(items: TimelineEvent[]): TimelineEvent[] {
  return [...items].sort((left, right) => (left.sequenceNo || 0) - (right.sequenceNo || 0))
}

export function writeoffChainStatus(items: TimelineEvent[]): string {
  const actions = new Set(items.map(item => item.action))
  if (actions.has("checkin_commit")) return "已签到"
  if (actions.has("cancel_refund")) return "已取消"
  if (actions.has("absence_commit")) {
    const absence = items.find(item => item.action === "absence_commit")
    return absence?.timesDelta === 1 ? "缺勤返还" : "缺勤扣次"
  }
  return "链路未完成"
}
