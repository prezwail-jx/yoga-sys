import { describe, expect, it, vi } from "vitest"

import { ApiClient } from "../miniprogram/services/api"
import { IdempotencyService, idempotentMutation } from "../miniprogram/services/idempotency"
import { StorageService } from "../miniprogram/services/storage"
import { FakeRuntime } from "./helpers/fake-runtime"

describe("IdempotencyService", () => {
  it("reuses a key for the same payload and replaces it when input changes", () => {
    const runtime = new FakeRuntime()
    const service = new IdempotencyService(new StorageService(runtime))
    const first = service.keyFor("create-slot", { start: "09:00", days: [1, 2] })
    const replay = service.keyFor("create-slot", { days: [1, 2], start: "09:00" })
    const changed = service.keyFor("create-slot", { start: "10:00", days: [1, 2] })

    expect(replay).toBe(first)
    expect(changed).not.toBe(first)
  })

  it("retains the same key after an uncertain failure and clears it after an authoritative response", async () => {
    const runtime = new FakeRuntime()
    const storage = new StorageService(runtime)
    const idempotency = new IdempotencyService(storage)
    const api = new ApiClient(runtime, "https://api.example.test", () => "token", vi.fn())
    runtime.requestHandler = (options) => options.fail({ errMsg: "request:fail network" })

    await expect(idempotentMutation(api, idempotency, "slot-1", "/private-slots", {
      method: "POST", body: { startAt: "2030-01-01T09:00:00+08:00" },
    })).rejects.toMatchObject({ kind: "network" })
    const retainedKey = runtime.requests[0].header["Idempotency-Key"]

    runtime.requestHandler = (options) => options.success({ data: { id: "slot" }, statusCode: 201, header: {} })
    await idempotentMutation(api, idempotency, "slot-1", "/private-slots", {
      method: "POST", body: { startAt: "2030-01-01T09:00:00+08:00" },
    })
    expect(runtime.requests[1].header["Idempotency-Key"]).toBe(retainedKey)
    expect(storage.pendingIdempotency("slot-1")).toBeNull()
  })
})
