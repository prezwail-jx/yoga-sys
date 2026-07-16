import { describe, expect, it } from "vitest"

import { parseSpecificCourseIds } from "../../utils/cardProduct"

describe("parseSpecificCourseIds", () => {
  it("trims, removes empty values and de-duplicates course ids", () => {
    expect(parseSpecificCourseIds("course-1, course-2, ,course-1")).toEqual(["course-1", "course-2"])
  })

  it("returns an empty list for blank input", () => {
    expect(parseSpecificCourseIds("   ")).toEqual([])
  })
})
