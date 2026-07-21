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
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page.getByRole("heading", { name: "会员管理", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "新增会员", exact: true }).click()
  await expect(page.getByRole("heading", { name: "新增会员", exact: true })).toBeVisible()
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
})
