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
  await page.getByRole("link", { name: "卡项办理" }).click()
  await expect(page.getByRole("heading", { name: "卡项办理" })).toBeVisible()
  await page.locator("select").nth(0).selectOption("member-1")
  await page.locator("select").nth(1).selectOption("product-1")
  await page.getByRole("button", { name: "办理购卡" }).click()
  await expect(page.getByText(/交易号：transaction-1/)).toBeVisible()
  expect(idempotencyKey.length).toBeGreaterThanOrEqual(8)
})
