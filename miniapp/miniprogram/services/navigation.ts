import type { MiniProgramRuntime } from "../platform/runtime"
import type { BusinessRole, CurrentUser } from "../types/contracts"

export interface NavigationItem {
  id: string
  label: string
  description: string
  path: string
}

const MEMBER_NAVIGATION: NavigationItem[] = [
  { id: "group-schedule", label: "团课日程", description: "按天查看可预约课程", path: "/pages/member/schedule/index" },
  { id: "private-training", label: "私教预约", description: "查看教练开放时间", path: "/pages/member/private-training/index" },
  { id: "my-bookings", label: "我的预约", description: "团课与私教历史", path: "/pages/member/bookings/index" },
  { id: "my-cards", label: "我的卡项", description: "余额、有效期与冻结状态", path: "/pages/member/cards/index" },
]

const COACH_NAVIGATION: NavigationItem[] = [
  { id: "assigned-classes", label: "我的团课", description: "今日排课与签到入口", path: "/pages/coach/schedule/index" },
  { id: "attendance", label: "签到名册", description: "从我的团课进入会员名册", path: "/pages/coach/schedule/index" },
  { id: "availability", label: "私教时间", description: "发布与调整开放时段", path: "/pages/coach/availability/index" },
  { id: "private-requests", label: "私教申请", description: "确认待处理请求", path: "/pages/coach/workload/index" },
]

export function navigationForRole(role: BusinessRole): NavigationItem[] {
  return role === "member" ? MEMBER_NAVIGATION : COACH_NAVIGATION
}

export class NavigationService {
  constructor(private readonly runtime: MiniProgramRuntime) {}

  routeAuthenticated(user: CurrentUser): void {
    if (user.role !== "member" && user.role !== "coach") {
      this.routeForbidden()
      return
    }
    this.runtime.reLaunch({ url: "/pages/workspace/index" })
  }

  routeBinding(): void {
    this.runtime.reLaunch({ url: "/pages/bind/index" })
  }

  routeStartup(): void {
    this.runtime.reLaunch({ url: "/pages/startup/index" })
  }

  routeForbidden(): void {
    this.runtime.reLaunch({ url: "/pages/forbidden/index" })
  }

  open(path: string): void {
    this.runtime.navigateTo({ url: path })
  }
}
