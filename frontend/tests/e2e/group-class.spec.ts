import { expect, test } from "@playwright/test"

const now = Date.now()
const startAt = new Date(now + 3 * 60 * 60 * 1000).toISOString()
const endAt = new Date(now + 4 * 60 * 60 * 1000).toISOString()

const session = {
  id: "session-1",
  courseId: "course-1",
  coachProfileId: "coach-1",
  roomId: "room-1",
  courseName: "流瑜伽",
  coachName: "林教练",
  roomName: "一号教室",
  startAt,
  endAt,
  capacity: 10,
  bookingOpenHoursBefore: 168,
  bookingCloseMinutesBefore: 60,
  cancelCutoffMinutesBefore: 120,
  status: "published",
  sourceSessionId: null,
  createdBy: "admin",
  bookedCount: 0,
  remainingCapacity: 10,
  isFull: false,
  createdAt: new Date(now).toISOString(),
  updatedAt: new Date(now).toISOString(),
}

test("会员可以从真实周课表预约并在我的预约中取消", async ({ page }) => {
  let booking: Record<string, unknown> | null = null
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "member", role: "member" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "member", role: "member", memberId: "member-1" } }))
  await page.route(/\/api\/class-sessions\?.*/, route => route.fulfill({ json: { items: [session], weekStart: "2026-07-20", weekEnd: "2026-07-26" } }))
  await page.route(/\/api\/class-sessions\/session-1$/, route => route.fulfill({ json: session }))
  await page.route("**/api/class-sessions/session-1/bookings", async route => {
    booking = {
      id: "booking-1",
      classSessionId: session.id,
      memberId: "member-1",
      memberName: "测试会员",
      courseName: session.courseName,
      coachName: session.coachName,
      roomName: session.roomName,
      startAt,
      endAt,
      sessionStatus: "published",
      status: "reserved",
      bookedById: "account-1",
      bookedByRole: "member",
      bookedAt: new Date(now).toISOString(),
      terminalById: null,
      terminalByRole: null,
      terminalAt: null,
      cancellationReason: null,
      traceId: "trace-1",
      createdAt: new Date(now).toISOString(),
      updatedAt: new Date(now).toISOString(),
    }
    await route.fulfill({ status: 201, json: booking })
  })
  await page.route(/\/api\/members\/me\/bookings\?.*/, route => route.fulfill({ json: { items: booking ? [booking] : [], total: booking ? 1 : 0, skip: 0, limit: 100 } }))
  await page.route("**/api/class-bookings/booking-1/cancel", async route => {
    booking = { ...booking, status: "cancelled", cancellationReason: "行程变化", terminalAt: new Date().toISOString() }
    await route.fulfill({ json: booking })
  })

  await page.goto("/login")
  await page.getByLabel("用户名").fill("member")
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page.getByRole("heading", { name: "团课周课表" })).toBeVisible()
  await expect(page.getByRole("link", { name: "我的预约" })).toBeVisible()
  await page.getByRole("button", { name: "立即预约" }).click()
  await expect(page.getByText("已预约 流瑜伽")).toBeVisible()
  await page.getByRole("link", { name: "我的预约" }).click()
  await expect(page.getByRole("heading", { name: "我的预约", exact: true })).toBeVisible()
  await page.getByRole("button", { name: "取消预约" }).click()
  await page.getByLabel("取消原因（选填）").fill("行程变化")
  await page.getByRole("button", { name: "确认取消预约" }).click()
  await expect(page.getByText("已取消 流瑜伽 的预约")).toBeVisible()
})

test("管理员可以为会员开通资源绑定账号", async ({ page }) => {
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route(/\/api\/members\?.*/, route => route.fulfill({ json: { items: [{ id: "member-1", name: "测试会员", phone: "13800000000", status: "normal", joinDate: "2026-07-20" }], total: 1, skip: 0, limit: 20 } }))
  await page.route("**/api/members/member-1/account", route => route.fulfill({ status: 201, json: { id: "account-1", username: "member001", role: "member", memberId: "member-1", coachProfileId: null, createdAt: new Date().toISOString() } }))

  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("button", { name: "开通账号" }).click()
  await page.getByLabel("用户名").fill("member001")
  await page.getByLabel("初始密码").fill("member123")
  await page.getByRole("button", { name: "确认开通" }).click()
  await expect(page.getByText("已为 测试会员 开通账号 member001")).toBeVisible()
})
