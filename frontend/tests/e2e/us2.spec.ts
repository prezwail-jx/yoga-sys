import { expect, test } from "@playwright/test"

test("管理员可从卡项办理页购卡且请求携带幂等键", async ({ page }) => {
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/members**", route => route.fulfill({ json: { items: [{ id: "member-1", name: "测试会员", phone: "13800000000", status: "normal" }], total: 1, skip: 0, limit: 100 } }))
  await page.route("**/api/card-products**", route => route.fulfill({ json: { items: [{ id: "product-1", name: "10次卡", price: "500.00", enabled: true }], total: 1, skip: 0, limit: 100 } }))
  await page.route("**/api/members/member-1/cards", route => route.fulfill({ json: { items: [], total: 0 } }))
  let idempotencyKey = ""
  await page.route("**/api/transactions", async route => {
    idempotencyKey = route.request().headers()["idempotency-key"] || ""
    await route.fulfill({ json: { transaction: { id: "transaction-1" }, memberCard: { id: "card-1" } } })
  })
  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page).toHaveURL(/\/members$/)
  await page.getByRole("link", { name: "卡项办理" }).click()
  await expect(page.getByRole("heading", { name: "卡项办理" })).toBeVisible()
  await page.locator("select").nth(0).selectOption("member-1")
  await page.locator("select").nth(1).selectOption("product-1")
  await page.getByRole("button", { name: "办理购卡" }).click()
  await expect(page.getByText(/交易号：transaction-1/)).toBeVisible()
  expect(idempotencyKey.length).toBeGreaterThanOrEqual(8)
})

test("管理员可填写原因并二次确认调整会员卡次数", async ({ page }) => {
  await page.route("**/api/auth/login", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route("**/api/auth/me", route => route.fulfill({ json: { username: "admin", role: "admin" } }))
  await page.route(/\/api\/members(?:\?.*)?$/, route => route.fulfill({ json: { items: [{ id: "member-1", name: "测试会员", phone: "13800000000", status: "normal", cardSummaries: [] }], total: 1, skip: 0, limit: 100 } }))
  await page.route("**/api/card-products**", route => route.fulfill({ json: { items: [], total: 0, skip: 0, limit: 100 } }))
  await page.route(/\/api\/members\/member-1\/cards(?:\?.*)?$/, route => route.fulfill({ json: { items: [{
    id: "card-1", memberId: "member-1", cardProductId: "product-1", sourceMemberCardId: null,
    productName: "10 次团课卡", cardType: "times", status: "active", remainingTimes: 6, usedTimes: 4,
    validDays: 90, openedOn: "2026-08-01", expiresOn: "2026-10-29", remindOn: null,
    frozenFrom: null, frozenUntil: null, freezeReason: null, totalFrozenDays: 0, expiringSoon: false,
    refundableTransactionId: null, termsSnapshot: {}, createdAt: "2026-08-01T00:00:00Z", updatedAt: "2026-08-01T00:00:00Z",
  }], total: 1 } }))
  let requestBody: Record<string, unknown> = {}
  let idempotencyKey = ""
  await page.route("**/api/member-cards/card-1/adjust-times", async route => {
    requestBody = route.request().postDataJSON()
    idempotencyKey = route.request().headers()["idempotency-key"] || ""
    await route.fulfill({ json: { transaction: { id: "adjust-1" }, memberCard: { id: "card-1", remainingTimes: 8 } } })
  })
  page.on("dialog", dialog => dialog.accept())

  await page.goto("/login")
  await page.getByRole("button", { name: "登录" }).click()
  await expect(page).toHaveURL(/\/members$/)
  await page.getByRole("link", { name: "卡项办理" }).click()
  await page.locator("select").nth(0).selectOption("member-1")
  await page.getByPlaceholder("增减次数，如 2 或 -1").fill("2")
  await page.getByPlaceholder("调整原因（必填）").fill("活动赠送")
  await page.getByRole("button", { name: "调整次数" }).click()

  await expect(page.getByText("次数调整成功，当前剩余 8 次")).toBeVisible()
  expect(requestBody).toEqual({ timesDelta: 2, reason: "活动赠送" })
  expect(idempotencyKey.length).toBeGreaterThanOrEqual(8)
})
