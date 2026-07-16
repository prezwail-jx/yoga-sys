import { beforeEach, describe, expect, it, vi } from "vitest"
import { useIdempotentSubmit } from "../../composables/useIdempotentSubmit"

describe("useIdempotentSubmit", () => {
  beforeEach(() => {
    let sequence = 0
    vi.stubGlobal("crypto", { randomUUID: () => `key-${++sequence}` })
  })

  it("reuses the same key when the same payload is retried", async () => {
    const submitter = useIdempotentSubmit()
    const keys: string[] = []
    await expect(submitter.submit("same", async key => { keys.push(key); throw new Error("network") })).rejects.toThrow()
    await submitter.submit("same", async key => { keys.push(key); return true })
    expect(keys).toEqual(["key-1", "key-1"])
  })

  it("uses a new key when the payload changes or reset is called", async () => {
    const submitter = useIdempotentSubmit()
    const keys: string[] = []
    await submitter.submit("one", async key => keys.push(key))
    await submitter.submit("two", async key => keys.push(key))
    submitter.reset()
    await submitter.submit("two", async key => keys.push(key))
    expect(keys).toEqual(["key-1", "key-2", "key-3"])
  })
})
