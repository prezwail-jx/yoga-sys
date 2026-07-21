import type { ClassSession } from "~/types/domain"

const dateKeyFormatter = new Intl.DateTimeFormat("en-CA", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
})

export function localDateKey(date: Date): string {
  return dateKeyFormatter.format(date)
}

export function getNaturalWeekStart(date = new Date()): string {
  const monday = new Date(date)
  monday.setHours(12, 0, 0, 0)
  const day = monday.getDay() || 7
  monday.setDate(monday.getDate() - day + 1)
  return localDateKey(monday)
}

export function addLocalDays(date: string, days: number): string {
  const result = new Date(`${date}T12:00:00`)
  result.setDate(result.getDate() + days)
  return localDateKey(result)
}

export function isoToLocalDateTime(value: string): string {
  const date = new Date(value)
  const pad = (part: number) => String(part).padStart(2, "0")
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function localDateTimeToIso(value: string): string {
  return new Date(value).toISOString()
}

export interface ScheduleDay {
  date: string
  sessions: ClassSession[]
}

export function groupSessionsByWeek(sessions: ClassSession[], weekStart: string): ScheduleDay[] {
  const days = Array.from({ length: 7 }, (_, index) => ({
    date: addLocalDays(weekStart, index),
    sessions: [] as ClassSession[],
  }))
  const dayByDate = new Map(days.map(day => [day.date, day]))
  for (const session of sessions) {
    dayByDate.get(localDateKey(new Date(session.startAt)))?.sessions.push(session)
  }
  for (const day of days) day.sessions.sort((left, right) => left.startAt.localeCompare(right.startAt))
  return days
}
