export function parseSpecificCourseIds(value: string): string[] {
  return [...new Set(value.split(",").map(item => item.trim()).filter(Boolean))]
}
