import { describe, expect, it, vi } from "vitest"

import { ApiClient, ApiError } from "../miniprogram/services/api"
import { FakeRuntime } from "./helpers/fake-runtime"

describe("ApiClient", () => {
  it("adds bearer, trace and idempotency headers without logging sensitive values", async () => {
    const runtime = new FakeRuntime()
    runtime.requestHandler = (options) => options.success({
      data: { ok: true }, statusCode: 201, header: { "x-trace-id": "server-trace" },
    })
    const api = new ApiClient(runtime, "https://api.example.test", () => "secret-token", vi.fn())

    await expect(api.request("/private-slots", {
      method: "POST",
      body: { password: "do-not-log" },
      idempotencyKey: "operation-key",
    })).resolves.toEqual({ ok: true })

    expect(runtime.requests[0].header.Authorization).toBe("Bearer secret-token")
    expect(runtime.requests[0].header["Idempotency-Key"]).toBe("operation-key")
    expect(runtime.requests[0].header["X-Trace-Id"]).toMatch(/^mp-/)
    expect(runtime.requests[0].timeout).toBe(10_000)
    const serializedLogs = JSON.stringify(runtime.logs)
    expect(serializedLogs).not.toContain("secret-token")
    expect(serializedLogs).not.toContain("do-not-log")
    expect(serializedLogs).toContain("server-trace")
  })

  it("normalizes HTTP errors and clears terminal unauthorized sessions", async () => {
    const runtime = new FakeRuntime()
    const unauthorized = vi.fn()
    runtime.requestHandler = (options) => options.success({
      data: { detail: "Token expired" }, statusCode: 401, header: {},
    })
    const api = new ApiClient(runtime, "https://api.example.test", () => "old-token", unauthorized)

    await expect(api.request("/auth/me")).rejects.toMatchObject({
      name: "ApiError", kind: "authentication", statusCode: 401, message: "Token expired",
    })
    expect(unauthorized).toHaveBeenCalledOnce()
  })

  it("distinguishes timeout and conflict errors", async () => {
    const runtime = new FakeRuntime()
    const api = new ApiClient(runtime, "https://api.example.test", () => null, vi.fn())
    runtime.requestHandler = (options) => options.fail({ errMsg: "request:fail timeout" })
    const timeout = await api.request("/slow").catch((error: ApiError) => error)
    expect(timeout).toMatchObject({ kind: "timeout", uncertain: true })

    runtime.requestHandler = (options) => options.success({
      data: { errorDescription: "Already bound" }, statusCode: 409, header: {},
    })
    await expect(api.request("/auth/wechat/bind", { method: "POST" })).rejects.toMatchObject({
      kind: "conflict", statusCode: 409, message: "Already bound",
    })
  })

  it("downloads an authenticated report to a temporary file and opens it", async () => {
    const runtime = new FakeRuntime()
    const api = new ApiClient(runtime, "https://api.example.test", () => "admin-token", vi.fn())

    await expect(api.downloadAndOpen("/reports/export?category=transactions")).resolves.toBeUndefined()

    expect(runtime.downloads).toHaveLength(1)
    expect(runtime.downloads[0].url).toBe("https://api.example.test/reports/export?category=transactions")
    expect(runtime.downloads[0].header.Authorization).toBe("Bearer admin-token")
    expect(runtime.downloads[0].timeout).toBe(30_000)
    expect(runtime.openedDocuments[0]).toMatchObject({ filePath: "/tmp/report.xlsx", fileType: "xlsx", showMenu: true })
    expect(JSON.stringify(runtime.logs)).not.toContain("admin-token")
  })

  it("reports download and temporary-file preview failures in Chinese", async () => {
    const runtime = new FakeRuntime()
    const api = new ApiClient(runtime, "https://api.example.test", () => "admin-token", vi.fn())
    runtime.downloadHandler = options => options.fail({ errMsg: "downloadFile:fail timeout" })
    await expect(api.downloadAndOpen("/reports/export?category=refunds")).rejects.toMatchObject({ kind: "timeout", message: "报表下载超时，请稍后重试" })

    runtime.downloadHandler = options => options.success({ tempFilePath: "/tmp/report.xlsx", statusCode: 200 })
    runtime.openDocumentHandler = options => options.fail({ errMsg: "openDocument:fail file format" })
    await expect(api.downloadAndOpen("/reports/export?category=refunds")).rejects.toMatchObject({ message: expect.stringContaining("无法打开临时文件") })
  })
})
