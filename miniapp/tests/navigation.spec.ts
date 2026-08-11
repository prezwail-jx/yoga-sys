import { describe, expect, it } from "vitest"

import { NavigationService, navigationForRole } from "../miniprogram/services/navigation"
import { apiBaseUrl } from "../miniprogram/config/environment"
import { FakeRuntime } from "./helpers/fake-runtime"

describe("role routing", () => {
  it("provides disjoint member and coach destinations", () => {
    const memberIds = navigationForRole("member").map((item) => item.id)
    const coachIds = navigationForRole("coach").map((item) => item.id)
    expect(memberIds).toEqual(["group-schedule", "private-training", "my-bookings", "my-cards"])
    expect(coachIds).toEqual(["assigned-classes", "attendance", "availability", "private-requests"])
    expect(memberIds).not.toContain("attendance")
    expect(coachIds).not.toContain("my-cards")
  })

  it("routes authenticated roles to workspace and rejects unsupported roles", () => {
    const runtime = new FakeRuntime()
    const navigation = new NavigationService(runtime)
    navigation.routeAuthenticated({ username: "member", role: "member", memberId: "member-1" })
    expect(runtime.relaunches.at(-1)).toBe("/pages/workspace/index")

    navigation.routeAuthenticated({ username: "admin", role: "admin" as "member" })
    expect(runtime.relaunches.at(-1)).toBe("/pages/forbidden/index")
  })

  it("selects local and production API hosts by environment version", () => {
    const runtime = new FakeRuntime()
    expect(apiBaseUrl(runtime)).toBe("http://127.0.0.1:8000")
    runtime.envVersion = "release"
    expect(apiBaseUrl(runtime)).toBe("https://yoga.tuitukj.com/backend")
  })
})
