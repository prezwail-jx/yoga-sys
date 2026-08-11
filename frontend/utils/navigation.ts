export type NavigationItem = {
  to: string
  label: string
  icon: string
  description: string
  mock?: boolean
  aliases?: string[]
}

export type NavigationGroup = {
  label: string
  items: NavigationItem[]
}

const adminGroups: NavigationGroup[] = [
  { label: "概览", items: [{ to: "/", label: "运营看板", icon: "i-lucide-layout-dashboard", description: "查看场馆经营概况", mock: true }] },
  { label: "客户经营", items: [
    { to: "/members", label: "会员管理", icon: "i-lucide-users", description: "管理会员资料、账号和业务记录" },
    { to: "/transactions", label: "卡项办理", icon: "i-lucide-credit-card", description: "办理购卡、续费及卡项业务" },
  ] },
  { label: "课程与预约", items: [
    { to: "/schedule", label: "团课课表", icon: "i-lucide-calendar-days", description: "排课、预约和团课运营", aliases: ["/sessions"] },
    { to: "/private-training", label: "私教预约", icon: "i-lucide-user-check", description: "管理私教时段和预约" },
  ] },
  { label: "产品与配置", items: [
    { to: "/cards", label: "卡项产品", icon: "i-lucide-badge", description: "配置卡项产品和售卖规则" },
    { to: "/class-catalog", label: "基础资料", icon: "i-lucide-settings-2", description: "维护教练账号、课程和教室" },
  ] },
  { label: "经营分析", items: [
    { to: "/reports", label: "统计报表", icon: "i-lucide-chart-no-axes-combined", description: "查看经营数据和趋势" },
  ] },
]

const memberGroups: NavigationGroup[] = [
  { label: "预约服务", items: [
    { to: "/schedule", label: "团课课表", icon: "i-lucide-calendar-days", description: "查看并预约团课" },
    { to: "/private-training", label: "私教预约", icon: "i-lucide-user-check", description: "查看并预约私教" },
    { to: "/my-bookings", label: "我的预约", icon: "i-lucide-clipboard-list", description: "管理我的预约记录" },
  ] },
  { label: "个人设置", items: [
    { to: "/account-security", label: "账号安全", icon: "i-lucide-shield-check", description: "修改登录密码" },
  ] },
]

const coachGroups: NavigationGroup[] = [
  { label: "教学工作", items: [
    { to: "/schedule", label: "我的课表", icon: "i-lucide-calendar-days", description: "查看本人团课安排", aliases: ["/sessions"] },
    { to: "/private-training", label: "私教工作台", icon: "i-lucide-user-check", description: "管理私教时段和预约" },
  ] },
]

export function getNavigationGroups(role?: string): NavigationGroup[] {
  if (role === "member") return memberGroups
  if (role === "coach") return coachGroups
  return adminGroups
}

export function isNavigationItemActive(item: NavigationItem, path: string): boolean {
  const paths = [item.to, ...(item.aliases || [])]
  return paths.some(value => value === "/" ? path === "/" : path === value || path.startsWith(`${value}/`))
}

export function getPageContext(path: string, role?: string): { group: string; title: string; description: string } {
  const groups = getNavigationGroups(role)
  for (const group of groups) {
    const item = group.items.find(candidate => isNavigationItemActive(candidate, path))
    if (item) {
      const title = path.includes("/timeline") ? "会员业务记录" : path.startsWith("/sessions/") ? "课次运营" : item.label
      return { group: group.label, title, description: item.description }
    }
  }
  return { group: "工作台", title: "Yoga SYS", description: "瑜伽馆日常经营与预约管理" }
}
