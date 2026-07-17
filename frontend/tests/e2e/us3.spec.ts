import { expect, test } from "@playwright/test"

test("管理员从会员列表进入时间线并查看核销链路", async ({ page }) => {
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/members?**", route => route.fulfill({ json: { items: [{ id: "member-1", name: "测试会员", phone: "13800000000", status: "normal", joinDate: "2026-07-17" }], total: 1, skip: 0, limit: 20 } }))
  await page.route("**/api/members/member-1/timeline**", route => route.fulfill({ json: {
    items: [
      { id: "event-2", source: "writeoff", action: "checkin_commit", result: "success", occurredAt: "2026-07-17T02:00:00Z", traceId: "trace-2", memberCardId: "card-1", businessRef: "booking-1", sequenceNo: 2, timesDelta: 0, summary: "签到实扣", productName: null, cardType: null, validDaysDelta: null, reason: null, amount: null },
      { id: "event-1", source: "writeoff", action: "reserve_hold", result: "success", occurredAt: "2026-07-17T01:00:00Z", traceId: "trace-1", memberCardId: "card-1", businessRef: "booking-1", sequenceNo: 1, timesDelta: -1, summary: "预约预扣", productName: null, cardType: null, validDaysDelta: null, reason: null, amount: null },
      { id: "txn-1", source: "transaction", action: "purchase", result: "success", occurredAt: "2026-07-16T01:00:00Z", traceId: "trace-0", memberCardId: "card-1", businessRef: null, sequenceNo: null, timesDelta: 10, amount: "500.00", productName: "10次团课卡", cardType: "times", validDaysDelta: 90, reason: null, summary: "购卡" },
    ], total: 3, skip: 0, limit: 50,
  } }))
  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await page.getByRole("link", { name: "会员管理" }).click()
  await page.getByRole("link", { name: "业务记录" }).click()
  await expect(page.getByRole("heading", { name: "会员业务时间线" })).toBeVisible()
  await expect(page.locator(".timeline-card strong", { hasText: "签到实扣" })).toBeVisible()
  await expect(page.getByText("10次团课卡")).toBeVisible()
  await expect(page.getByText("金额：¥500.00")).toBeVisible()
  await page.getByRole("button", { name: "查看核销链路" }).first().click()
  await expect(page.getByRole("complementary", { name: "核销链路详情" })).toBeVisible()
  await expect(page.getByText("已签到")).toBeVisible()
})
