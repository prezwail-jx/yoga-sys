import type { ApiClient } from "./api"
import { idempotentMutation, type IdempotencyService } from "./idempotency"
import type { StorageService } from "./storage"
import type { CardProduct, CardProductInput, ClassBooking, ClassSession, Coach, CopyWeekResult, Course, ManagedMemberCard, Member, MemberInput, MemberUpdateInput, PageResult, PrivateBooking, PrivateSlot, PrivateWeekInput, PrivateWeekResult, ReportDetail, ReportDetailCategory, ReportSummary, ReportTrend, ReportTrendCategory, Room, TimelineEvent, TransactionInput, TransactionOperation } from "../types/admin"

function query(params: Record<string, string | number | boolean | undefined>): string {
  return Object.entries(params).filter(([, value]) => value !== undefined && value !== "").map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`).join("&")
}

export class AdminService {
  constructor(private readonly api: ApiClient, private readonly idempotency: IdempotencyService, private readonly storage: StorageService) {}
  members(params: { keyword?: string; status?: string; skip?: number; limit?: number } = {}) { return this.api.request<PageResult<Member>>(`/members?${query({ ...params })}`) }
  member(id: string) { return this.api.request<Member>(`/members/${encodeURIComponent(id)}`) }
  createMember(input: MemberInput) { return this.api.request<Member>("/members", { method: "POST", body: input }) }
  updateMember(id: string, input: MemberUpdateInput) { return this.api.request<Member>(`/members/${encodeURIComponent(id)}`, { method: "PATCH", body: input }) }
  memberCards(id: string) { return this.api.request<{ items: ManagedMemberCard[]; total: number }>(`/members/${encodeURIComponent(id)}/cards`) }
  memberTimeline(id: string) { return this.api.request<PageResult<TimelineEvent>>(`/members/${encodeURIComponent(id)}/timeline?limit=20`) }
  products(enabled?: boolean) { return this.api.request<PageResult<CardProduct>>(`/card-products?${query({ enabled, limit: 100 })}`) }
  createProduct(input: CardProductInput) { return this.api.request<CardProduct>("/card-products", { method: "POST", body: input }) }
  updateProduct(id: string, input: Partial<CardProductInput>) { return this.api.request<CardProduct>(`/card-products/${encodeURIComponent(id)}`, { method: "PATCH", body: input }) }
  transaction(input: TransactionInput) { return this.mutate<TransactionOperation>(`transaction:${input.memberId}:${input.txnType}`, "/transactions", input) }
  freeze(cardId: string, frozenUntil: string, reason: string) { return this.mutate<TransactionOperation>(`freeze:${cardId}`, `/member-cards/${encodeURIComponent(cardId)}/freeze`, { frozenUntil, reason }) }
  unfreeze(cardId: string, reason?: string) { return this.mutate<TransactionOperation>(`unfreeze:${cardId}`, `/member-cards/${encodeURIComponent(cardId)}/unfreeze`, { reason: reason || null }) }
  adjustTimes(cardId: string, timesDelta: number, reason: string) { return this.mutate<TransactionOperation>(`adjust:${cardId}`, `/member-cards/${encodeURIComponent(cardId)}/adjust-times`, { timesDelta, reason }) }
  sessions(weekStart: string) { return this.api.request<{ items: ClassSession[]; weekStart: string; weekEnd: string }>(`/class-sessions?weekStart=${encodeURIComponent(weekStart)}`) }
  createSession(input: { courseId: string; coachProfileId: string; roomId: string; startAt: string; endAt: string; capacity: number }) { return this.api.request<ClassSession>("/class-sessions", { method: "POST", body: input }) }
  copySessionWeek(sourceWeekStart: string, targetWeekStart: string) { return this.mutate<CopyWeekResult>(`session:copy-week:${sourceWeekStart}:${targetWeekStart}`, "/class-sessions/copy-week", { sourceWeekStart, targetWeekStart }) }
  transitionSession(id: string, action: "publish" | "pause" | "resume" | "cancel" | "complete") { return action === "cancel" || action === "complete" ? this.mutate<ClassSession>(`session:${action}:${id}`, `/class-sessions/${id}/${action}`, undefined) : this.api.request<ClassSession>(`/class-sessions/${id}/${action}`, { method: "POST" }) }
  roster(id: string) { return this.api.request<PageResult<ClassBooking>>(`/class-sessions/${id}/bookings`) }
  adminBook(id: string, memberId: string) { return this.mutate<ClassBooking>(`admin-book:${id}:${memberId}`, `/class-sessions/${id}/bookings`, { memberId }) }
  cancelBooking(id: string, reason?: string) { return this.mutate<ClassBooking>(`booking-cancel:${id}`, `/class-bookings/${id}/cancel`, { reason: reason || null }) }
  checkIn(id: string) { return this.mutate<ClassBooking>(`check-in:${id}`, `/class-bookings/${id}/check-in`, undefined) }
  privateSlots(dateFrom?: string, dateTo?: string) { return this.api.request<{ items: PrivateSlot[]; total: number }>(`/private-slots?${query({ dateFrom, dateTo })}`) }
  createPrivateSlot(coachProfileId: string, startAt: string, endAt: string) { return this.mutate<PrivateSlot>(`private-slot:create:${coachProfileId}:${startAt}`, "/private-slots", { coachProfileId, startAt, endAt }) }
  generatePrivateWeek(input: PrivateWeekInput) { return this.mutate<PrivateWeekResult>(`private-slot:week:${input.coachProfileId}:${input.weekStart}:${input.startTime}`, "/private-slots/generate-week", input) }
  updatePrivateSlot(id: string, coachProfileId: string, startAt: string, endAt: string) { return this.mutate<PrivateSlot>(`private-slot:update:${id}`, `/private-slots/${encodeURIComponent(id)}`, { coachProfileId, startAt, endAt }, "PATCH") }
  deletePrivateSlot(id: string) { return this.mutate<PrivateSlot>(`private-slot:delete:${id}`, `/private-slots/${encodeURIComponent(id)}`, undefined, "DELETE") }
  privateBookings(status?: string) { return this.api.request<PageResult<PrivateBooking>>(`/private-bookings?${query({ status, limit: 100 })}`) }
  decidePrivate(id: string, action: "confirm" | "reject" | "cancel", reason?: string) { return this.mutate<PrivateBooking>(`private:${action}:${id}`, `/private-bookings/${id}/${action}`, reason ? { reason } : undefined) }
  signInPrivate(id: string, content: string, consumedHours: string, memberStatusNotes?: string) { return this.mutate<PrivateBooking>(`private:sign-in:${id}`, `/private-bookings/${id}/sign-in`, { content, consumedHours, memberStatusNotes: memberStatusNotes || null }) }
  courses() { return this.api.request<PageResult<Course>>("/courses?limit=100") }
  rooms() { return this.api.request<PageResult<Room>>("/rooms?limit=100") }
  coaches() { return this.api.request<PageResult<Coach>>("/coaches?limit=100") }
  createCatalog(kind: "courses" | "rooms" | "coaches", input: Record<string, unknown>) { return this.api.request<unknown>(`/${kind}`, { method: "POST", body: input }) }
  updateCatalog(kind: "courses" | "rooms" | "coaches", id: string, input: Record<string, unknown>) { return this.api.request<unknown>(`/${kind}/${id}`, { method: "PATCH", body: input }) }
  createAccount(kind: "members" | "coaches", id: string, username: string, initialPassword: string) { return this.mutate<unknown>(`account:${kind}:${id}`, `/${kind}/${id}/account`, { username, initialPassword }) }
  resetPassword(kind: "members" | "coaches", id: string, newPassword: string) { return this.api.request<unknown>(`/${kind}/${id}/account/reset-password`, { method: "POST", body: { newPassword } }) }
  reportSummary(dateFrom?: string, dateTo?: string) { return this.api.request<ReportSummary>(`/reports/summary?${query({ dateFrom, dateTo })}`) }
  reportTrend(category: ReportTrendCategory, dateFrom?: string, dateTo?: string) { return this.api.request<ReportTrend>(`/reports/trends?${query({ category, dateFrom, dateTo })}`) }
  reportDetail(category: ReportDetailCategory, dateFrom?: string, dateTo?: string) { return this.api.request<ReportDetail>(`/reports/details/${category}?${query({ dateFrom, dateTo, limit: 50 })}`) }
  exportReport(category: ReportDetailCategory, dateFrom?: string, dateTo?: string) { return this.api.downloadAndOpen(`/reports/export?${query({ category, dateFrom, dateTo })}`) }
  private mutate<T>(operation: string, path: string, body: unknown, method: "POST" | "PATCH" | "DELETE" = "POST") { return idempotentMutation<T>(this.api, this.idempotency, `${this.storage.user()?.username ?? "admin"}:${operation}`, path, { method, body }) }
}
