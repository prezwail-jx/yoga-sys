import { expect, test } from "@playwright/test"

const now = Date.now()
const startAt = new Date(now + 3 * 60 * 60 * 1000).toISOString()
const endAt = new Date(now + 4 * 60 * 60 * 1000).toISOString()

const slot = {
  id: "slot-1",
  coachProfileId: "coach-1",
  coachName: "林教练",
  startAt,
  endAt,
  durationMinutes: 60,
  status: "available",
  createdById: "coach-account",
  createdByRole: "coach",
  createdAt: new Date(now).toISOString(),
  updatedAt: new Date(now).toISOString(),
}

function booking(status: "pending" | "confirmed" | "completed") {
  return {
    id: "booking-1",
    availabilityId: slot.id,
    memberId: "member-1",
    memberName: "测试会员",
    coachProfileId: "coach-1",
    coachName: "林教练",
    memberCardId: status === "pending" ? null : "card-1",
    startAt,
    endAt,
    durationMinutes: 60,
    status,
    memberMessage: "想练肩颈",
    rejectionReason: null,
    cancellationReason: null,
    bookedById: "member-account",
    bookedByRole: "member",
    confirmedAt: status === "pending" ? null : new Date(now).toISOString(),
    terminalById: status === "completed" ? "coach-account" : null,
    terminalByRole: status === "completed" ? "coach" : null,
    terminalAt: status === "completed" ? new Date(now).toISOString() : null,
    traceId: "trace-1",
    createdAt: new Date(now).toISOString(),
    updatedAt: new Date(now).toISOString(),
  }
}

test("会员提交私教预约后教练确认并签到", async ({ page }) => {
  let currentBooking: Record<string, unknown> | null = null
  let currentUser: Record<string, unknown> | null = null
  await page.route("**/api/auth/login", route => route.fulfill({ json: currentUser }))
  await page.route("**/api/auth/me", route => currentUser ? route.fulfill({ json: currentUser }) : route.fulfill({ status: 401, json: { detail: "Unauthorized" } }))
  await page.route("**/api/auth/logout", route => {
    currentUser = null
    return route.fulfill({ json: { ok: true } })
  })
  await page.route(/\/api\/coaches\?.*/, route => route.fulfill({ json: { items: [{ id: "coach-1", name: "林教练", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route(/\/api\/private-slots\?.*/, route => route.fulfill({ json: { items: currentBooking ? [] : [slot], total: currentBooking ? 0 : 1 } }))
  await page.route(/\/api\/private-bookings\?.*/, route => route.fulfill({ json: { items: currentBooking ? [currentBooking] : [], total: currentBooking ? 1 : 0, skip: 0, limit: 100 } }))
  await page.route("**/api/private-bookings", route => {
    currentBooking = booking("pending")
    return route.fulfill({ status: 201, json: currentBooking })
  })

  await page.goto("/login")
  currentUser = { username: "member", role: "member", memberId: "member-1" }
  await page.getByLabel("用户名").fill("member")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("link", { name: "私教预约" }).click()
  await page.getByPlaceholder("给教练留言（选填）").fill("想练肩颈")
  await page.getByRole("button", { name: "预约" }).click()
  await expect(page.getByText("已提交私教预约，等待教练确认")).toBeVisible()
  await expect(page.getByText("测试会员")).toBeVisible()

  await page.route("**/api/private-bookings/booking-1/confirm", route => {
    currentBooking = booking("confirmed")
    return route.fulfill({ json: currentBooking })
  })
  await page.route("**/api/private-bookings/booking-1/sign-in", route => {
    currentBooking = booking("completed")
    return route.fulfill({ json: currentBooking })
  })
  await page.getByRole("button", { name: "退出" }).click()
  currentUser = { username: "coach", role: "coach", coachProfileId: "coach-1" }
  await page.getByLabel("用户名").fill("coach")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("link", { name: "私教工作台" }).click()
  await page.getByRole("button", { name: "处理" }).click()
  await page.getByRole("button", { name: "确认" }).click()
  await expect(page.getByText("预约状态已更新")).toBeVisible()
  await page.getByRole("button", { name: "处理" }).click()
  await page.getByLabel("上课内容").fill("肩颈放松与核心训练")
  await page.getByRole("button", { name: "签到并记录" }).click()
  await expect(page.getByText("私教课已签到并记录")).toBeVisible()
})

test("管理员查看真实报表下钻并触发 Excel 导出", async ({ page }) => {
  let currentUser: Record<string, unknown> | null = null
  await page.route("**/api/auth/login", route => {
    currentUser = { username: "admin", role: "admin" }
    return route.fulfill({ json: currentUser })
  })
  await page.route("**/api/auth/me", route => currentUser ? route.fulfill({ json: currentUser }) : route.fulfill({ status: 401, json: { detail: "Unauthorized" } }))
  await page.route(/\/api\/coaches\?.*/, route => route.fulfill({ json: { items: [{ id: "coach-1", name: "林教练", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route(/\/api\/courses\?.*/, route => route.fulfill({ json: { items: [{ id: "course-1", name: "流瑜伽", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route(/\/api\/cards\?.*/, route => route.fulfill({ json: { items: [{ id: "card-product-1", name: "私教卡", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route(/\/api\/reports\/summary.*/, route => route.fulfill({ json: { totalMembers: 12, activeMembers: 10, expiringSoonMembers: 2, cardSales: "1000.00", renewalSales: "200.00", refundAmount: "50.00", attendanceRate: 0.8, fullClassRate: 0.5, privateLessonCount: 3, privateConsumedHours: "4.5", privateCompletionRate: 0.75 } }))
  await page.route(/\/api\/reports\/trends.*/, route => route.fulfill({ json: { category: "revenue", points: [{ bucket: "2030-01-01", value: "1000.00" }] } }))
  await page.route(/\/api\/reports\/details\/transactions.*/, route => route.fulfill({ json: { category: "transactions", items: [{ transactionId: "txn-1", memberName: "测试会员", amount: "1000.00" }], total: 1, skip: 0, limit: 20 } }))
  await page.route(/\/api\/reports\/export.*/, route => route.fulfill({ body: "xlsx", headers: { "content-type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "content-disposition": "attachment; filename=report-transactions.xlsx" } }))

  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("link", { name: "统计报表" }).click()
  await expect(page.getByRole("heading", { name: "统计报表" })).toBeVisible()
  await expect(page.getByText("活跃会员")).toBeVisible()
  await expect(page.getByText("测试会员")).toBeVisible()
  const download = page.waitForEvent("download")
  await page.getByRole("button", { name: "导出 Excel" }).click()
  await expect((await download).suggestedFilename()).toBe("report-transactions.xlsx")
})

test("管理员创建私教时段并看到可执行冲突提示", async ({ page }) => {
  const currentUser = { username: "admin", role: "admin" }
  let createCount = 0
  await page.route("**/api/auth/login", route => route.fulfill({ json: currentUser }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: currentUser }))
  await page.route(/\/api\/coaches\?.*/, route => route.fulfill({ json: { items: [{ id: "coach-1", name: "林教练", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route(/\/api\/private-slots\?.*/, route => route.fulfill({ json: { items: [], total: 0 } }))
  await page.route(/\/api\/private-bookings\?.*/, route => route.fulfill({ json: { items: [], total: 0, skip: 0, limit: 100 } }))
  await page.route("**/api/private-slots", route => {
    createCount += 1
    if (createCount === 1) return route.fulfill({ status: 201, json: slot })
    return route.fulfill({ status: 409, json: { detail: "private_slot_time_conflict" } })
  })

  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("link", { name: "私教预约" }).click()
  await page.getByLabel("教练").selectOption("coach-1")
  await page.getByLabel("开始时间").fill("2030-01-08T10:00")
  await page.getByLabel("结束时间").fill("2030-01-08T11:00")
  await page.getByRole("button", { name: "创建时段" }).click()
  await expect(page.getByText("私教空闲时段已创建")).toBeVisible()

  await page.getByLabel("开始时间").fill("2030-01-08T10:30")
  await page.getByLabel("结束时间").fill("2030-01-08T11:30")
  await page.getByRole("button", { name: "创建时段" }).click()
  await expect(page.getByText("该教练已有重叠的私教时段，请调整时间。")).toBeVisible()
})
