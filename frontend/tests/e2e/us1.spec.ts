import { expect, test } from "@playwright/test"

test("管理员登录后可以进入会员管理并打开新增表单", async ({ page }) => {
  await page.route("**/api/auth/login", route =>
    route.fulfill({ json: { username: "admin", role: "admin" } }),
  )
  await page.route("**/api/auth/me", route =>
    route.fulfill({ json: { username: "admin", role: "admin" } }),
  )
  await page.route("**/api/members**", async route => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: { items: [], total: 0, skip: 0, limit: 20 } })
    } else {
      await route.fulfill({
        status: 201,
        json: {
          id: "00000000-0000-0000-0000-000000000001",
          name: "测试会员",
          phone: "13800001234",
          gender: null,
          status: "normal",
          joinDate: "2026-07-16",
          birthday: null,
          note: null,
          emergencyContact: null,
          deletedAt: null,
          createdAt: "2026-07-16T00:00:00Z",
          updatedAt: "2026-07-16T00:00:00Z",
        },
      })
    }
  })

  await page.goto("/login")
  await page.getByLabel("用户名").fill("admin")
  await page.getByLabel("密码").fill("admin123")
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page.getByRole("heading", { name: "会员管理", exact: true, level: 1 })).toBeVisible()
  await page.getByRole("button", { name: "新增会员", exact: true }).click()
  await expect(page.getByRole("heading", { name: "新增会员", exact: true })).toBeVisible()
})

test("管理员可以从导航进入基础资料管理", async ({ page }) => {
  await page.route("**/api/auth/login", route =>
    route.fulfill({ json: { username: "admin", role: "admin" } }),
  )
  await page.route("**/api/auth/me", route =>
    route.fulfill({ json: { username: "admin", role: "admin" } }),
  )
  await page.route(/\/api\/(courses|rooms|coaches)\?.*/, route =>
    route.fulfill({ json: { items: [], total: 0, skip: 0, limit: 100 } }),
  )

  await page.goto("/login")
  await page.getByLabel("用户名").fill("admin")
  await page.getByLabel("密码").fill("admin123")
  await page.getByRole("button", { name: "登录" }).click()
  const navigation = page.getByRole("navigation", { name: "主导航" })
  await expect(navigation.getByText("客户经营", { exact: true })).toBeVisible()
  await expect(navigation.getByText("课程与预约", { exact: true })).toBeVisible()
  await expect(navigation.getByText("产品与配置", { exact: true })).toBeVisible()
  await page.getByRole("link", { name: "基础资料", exact: true }).click()
  await expect(page.getByRole("heading", { name: "基础资料", exact: true, level: 1 })).toBeVisible()
  await expect(page.getByRole("heading", { name: "教练与账号管理", exact: true })).toBeVisible()
  await expect(page).toHaveURL(/tab=coaches/)
  await page.getByRole("button", { name: /课程/ }).click()
  await expect(page).toHaveURL(/tab=courses/)
  await expect(page.getByRole("heading", { name: "课程", exact: true })).toBeVisible()
})

test("教练登录后进入本人课表", async ({ page }) => {
  await page.route("**/api/auth/login", route =>
    route.fulfill({ json: { username: "coach", role: "coach" } }),
  )
  await page.route("**/api/auth/me", route =>
    route.fulfill({ json: { username: "coach", role: "coach", coachProfileId: "coach-1" } }),
  )
  await page.route("**/api/class-sessions?**", route =>
    route.fulfill({ json: { items: [], weekStart: "2026-07-20", weekEnd: "2026-07-26" } }),
  )
  await page.goto("/login")
  await page.getByLabel("用户名").fill("coach")
  await page.getByLabel("密码").fill("coach123")
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page.getByRole("heading", { name: "团课周课表" })).toBeVisible()
  await expect(page.getByRole("link", { name: "我的课表" })).toBeVisible()
  await expect(page.getByRole("link", { name: "基础资料", exact: true })).toHaveCount(0)
})

test("会员列表突出账号状态、业务入口和重新启用操作", async ({ page }) => {
  const baseMember = {
    phone: "13800001234", gender: null, joinDate: "2026-07-16", birthday: null,
    note: null, emergencyContact: null, deletedAt: null,
    createdAt: "2026-07-16T00:00:00Z", updatedAt: "2026-07-16T00:00:00Z",
  }
  const members = [
    { ...baseMember, id: "member-open", name: "已开户会员", status: "normal", hasAccount: true, username: "member" },
    { ...baseMember, id: "member-disabled", name: "禁用会员", status: "disabled", hasAccount: false, username: null },
  ]
  let reenabled = false
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route(/\/api\/members\?.*/, route => route.fulfill({ json: { items: members, total: 2, skip: 0, limit: 20 } }))
  await page.route("**/api/members/member-disabled", async route => {
    reenabled = route.request().method() === "PATCH"
    await route.fulfill({ json: { ...members[1], status: "normal" } })
  })

  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  const openRow = page.getByRole("row").filter({ hasText: "已开户会员" })
  await expect(openRow.getByText("已开通", { exact: true })).toBeVisible()
  await expect(openRow.getByText("member", { exact: true })).toBeVisible()
  await expect(openRow.getByRole("button", { name: "业务管理" })).toBeVisible()
  await expect(openRow.getByRole("link", { name: "业务记录" })).toBeVisible()

  const disabledRow = page.getByRole("row").filter({ hasText: "禁用会员" })
  await disabledRow.getByRole("button", { name: "业务管理" }).click()
  await page.getByRole("button", { name: "重新启用" }).click()
  expect(reenabled).toBe(true)
})
