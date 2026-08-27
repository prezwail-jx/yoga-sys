import type { ClassBooking, ClassSession, MemberCard, PrivateBooking, PrivateSlot } from "./member"

export type MemberStatus = "normal" | "paused" | "expired" | "disabled"
export type CardType = "duration" | "times" | "private" | "trial"

export interface PageResult<T> { items: T[]; total: number; skip: number; limit: number }
export interface CardSummary { id: string; productName: string; cardType: CardType; status: MemberCard["status"]; remainingTimes: number | null; expiresOn: string | null }
export interface Member { id: string; name: string; phone: string; gender: string | null; status: MemberStatus; joinDate: string; birthday: string | null; note: string | null; emergencyContact: string | null; hasAccount: boolean; username: string | null; accountId: string | null; cardSummaries: CardSummary[] }
export interface MemberInput { name: string; phone: string; joinDate: string; gender?: string | null; birthday?: string | null; note?: string | null; emergencyContact?: string | null; status?: MemberStatus }
export interface MemberUpdateInput { name?: string; gender?: string | null; birthday?: string | null; note?: string | null; emergencyContact?: string | null; status?: MemberStatus }
export interface ManagedMemberCard extends MemberCard { memberId: string; cardProductId: string; sourceMemberCardId: string | null; usedTimes: number; validDays: number | null; freezeReason: string | null; refundableTransactionId: string | null }

export interface CardProduct { id: string; name: string; cardType: CardType; price: string; costPrice: string | null; totalTimes: number | null; validDays: number | null; activationMode: "immediate" | "first_booking"; applicableCourseScope: "group" | "private" | "specific"; specificCourseIds: string[] | null; absenceDeductEnabled: boolean; cancelRefundEnabled: boolean; enabled: boolean }
export interface CardProductInput { name: string; cardType: CardType; price: number; costPrice?: number | null; totalTimes?: number | null; validDays?: number | null; activationMode: "immediate" | "first_booking"; applicableCourseScope: "group" | "private" | "specific"; specificCourseIds?: string[] | null; absenceDeductEnabled: boolean; cancelRefundEnabled: boolean; enabled?: boolean }
export type TransactionType = "purchase" | "renew" | "reissue" | "refund" | "extend"
export interface TransactionInput { txnType: TransactionType; memberId: string; cardProductId?: string; memberCardId?: string; originTransactionId?: string; validDaysDelta?: number; reason?: string }
export interface TransactionOperation { memberCard: ManagedMemberCard; transaction: { id: string; txnType: TransactionType | "freeze" | "unfreeze" | "adjust" } }
export interface TimelineEvent { id: string; source: "transaction" | "writeoff" | "audit"; occurredAt: string; summary: string; reason: string | null; timesDelta: number | null; amount: string | null }

export interface Course { id: string; name: string; durationMinutes: number; difficulty: "all_levels" | "beginner" | "intermediate" | "advanced"; description: string | null; enabled: boolean }
export interface Room { id: string; name: string; capacity: number; enabled: boolean }
export interface Coach { id: string; name: string; bio: string | null; enabled: boolean; hasAccount: boolean; username: string | null; accountId: string | null }
export interface ReportSummary { totalMembers: number; activeMembers: number; expiringSoonMembers: number; cardSales: string; renewalSales: string; refundAmount: string; attendanceRate: number; fullClassRate: number; privateLessonCount: number; privateConsumedHours: string; privateCompletionRate: number }
export type ReportTrendCategory = "revenue" | "bookings" | "attendance" | "private"
export type ReportDetailCategory = "expiring_members" | "transactions" | "refunds" | "attendance" | "private"
export interface ReportTrend { category: ReportTrendCategory; points: Array<{ bucket: string; value: string | number }> }
export interface ReportDetail { category: ReportDetailCategory; items: Record<string, unknown>[]; total: number; skip: number; limit: number }
export interface CopyWeekResult { created: ClassSession[]; conflicts: Array<{ sourceSessionId: string; targetStartAt: string; reason: string }> }
export interface PrivateWeekInput { coachProfileId: string; weekStart: string; weekdays: number[]; startTime: string; durationMinutes: number }
export interface PrivateWeekResult { created: PrivateSlot[]; conflicts: Array<{ startAt: string; endAt: string; reason: string }> }

export type { ClassBooking, ClassSession, PrivateBooking, PrivateSlot }
