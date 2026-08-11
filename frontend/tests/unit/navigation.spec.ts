import { describe, expect, it } from "vitest"

import { getNavigationGroups, getPageContext, isNavigationItemActive } from "../../utils/navigation"

describe("navigation information architecture", () => {
  it("groups administrator navigation by business flow", () => {
    const groups = getNavigationGroups("admin")
    expect(groups.map(group => group.label)).toEqual(["概览", "客户经营", "课程与预约", "产品与配置", "经营分析"])
    expect(groups.flatMap(group => group.items).map(item => item.label)).toContain("卡项产品")
  })

  it("keeps administrator configuration out of member and coach menus", () => {
    expect(getNavigationGroups("member").flatMap(group => group.items).some(item => item.to === "/class-catalog")).toBe(false)
    expect(getNavigationGroups("coach").flatMap(group => group.items).some(item => item.to === "/class-catalog")).toBe(false)
  })

  it("matches nested business routes to their parent navigation", () => {
    const memberItem = getNavigationGroups("admin").flatMap(group => group.items).find(item => item.to === "/members")!
    const scheduleItem = getNavigationGroups("admin").flatMap(group => group.items).find(item => item.to === "/schedule")!
    expect(isNavigationItemActive(memberItem, "/members/member-1/timeline")).toBe(true)
    expect(isNavigationItemActive(scheduleItem, "/sessions/session-1")).toBe(true)
    expect(getPageContext("/members/member-1/timeline", "admin")).toMatchObject({ group: "客户经营", title: "会员业务记录" })
  })
})
