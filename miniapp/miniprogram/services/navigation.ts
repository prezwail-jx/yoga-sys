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

const ADMIN_NAVIGATION: NavigationItem[] = [
  { id: "admin-dashboard", label: "运营概览", description: "经营指标与今日工作入口", path: "/packageAdmin/pages/dashboard/index" },
  { id: "admin-members", label: "会员与卡项", description: "会员资料、持卡摘要和卡项办理", path: "/packageAdmin/pages/members/index" },
  { id: "admin-products", label: "卡产品", description: "卡产品新建、编辑与启停", path: "/packageAdmin/pages/products/index" },
  { id: "admin-classes", label: "团课管理", description: "排课、课次状态和预约名单", path: "/packageAdmin/pages/classes/index" },
  { id: "admin-private", label: "私教管理", description: "私教时段与预约处理", path: "/packageAdmin/pages/private/index" },
  { id: "admin-catalog", label: "基础资料", description: "课程、教室、教练及账号", path: "/packageAdmin/pages/catalog/index" },
  { id: "admin-reports", label: "统计报表", description: "筛选查看趋势和业务明细", path: "/packageAdmin/pages/reports/index" },
]

export function navigationForRole(role: BusinessRole): NavigationItem[] {
  if (role === "member") return MEMBER_NAVIGATION
  if (role === "coach") return COACH_NAVIGATION
  return ADMIN_NAVIGATION
}

export class NavigationService {
  constructor(private readonly runtime: MiniProgramRuntime) {}

  routeAuthenticated(user: CurrentUser): void {
    if (user.role !== "member" && user.role !== "coach" && user.role !== "admin") {
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
