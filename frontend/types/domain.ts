export type UserRole = "admin" | "coach" | "member"
export type MemberStatus = "normal" | "paused" | "expired" | "disabled"
export type CardType = "duration" | "times" | "private" | "trial"
export type ActivationMode = "immediate" | "first_booking"
export type CourseScope = "group" | "private" | "specific"

export interface CurrentUser {
  username: string
  role: UserRole
}

export interface Member {
  id: string
  name: string
  gender: string | null
  phone: string
  birthday: string | null
  joinDate: string
  emergencyContact: string | null
  status: MemberStatus
  note: string | null
  deletedAt: string | null
  createdAt: string
  updatedAt: string
}

export interface MemberInput {
  name: string
  phone: string
  joinDate: string
  gender?: string | null
  birthday?: string | null
  note?: string | null
  emergencyContact?: string | null
}

export interface MemberList {
  items: Member[]
  total: number
  skip: number
  limit: number
}

export interface CardProduct {
  id: string
  name: string
  cardType: CardType
  price: string
  costPrice: string | null
  totalTimes: number | null
  validDays: number | null
  activationMode: ActivationMode
  applicableCourseScope: CourseScope
  specificCourseIds: string[] | null
  absenceDeductEnabled: boolean
  cancelRefundEnabled: boolean
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface CardProductInput {
  name: string
  cardType: CardType
  price: number
  costPrice?: number | null
  totalTimes?: number | null
  validDays?: number | null
  activationMode: ActivationMode
  applicableCourseScope: CourseScope
  specificCourseIds?: string[] | null
  absenceDeductEnabled: boolean
  cancelRefundEnabled: boolean
}

export interface CardProductList {
  items: CardProduct[]
  total: number
  skip: number
  limit: number
}

export interface CourseSession {
  id: string
  weekday: number
  startAt: string
  endAt: string
  courseName: string
  coachName: string
  roomName: string
  capacity: number
  booked: number
  status: "normal" | "full" | "cancelled" | "paused"
}

export interface CoachSlot {
  id: string
  coachId: string
  coachName: string
  startAt: string
  endAt: string
  durationMinutes: number
  booked: boolean
}

export interface BookingRecord {
  id: string
  memberName: string
  courseName: string
  bookingType: "group" | "private"
  bookedAt: string
  signedIn: boolean
  deductionDone: boolean
}

export interface ReportSummary {
  totalMembers: number
  activeMembers: number
  expiringSoonMembers: number
  cardSales: number
  renewalSales: number
  refundAmount: number
  attendanceRate: number
  fullClassRate: number
}

export type MemberCardStatus = "pending_activation" | "active" | "frozen" | "expired" | "closed"
export type TransactionType = "purchase" | "renew" | "reissue" | "refund" | "freeze" | "unfreeze" | "extend"

export interface MemberCard {
  id: string
  memberId: string
  cardProductId: string
  sourceMemberCardId: string | null
  productName: string
  cardType: CardType
  status: MemberCardStatus
  remainingTimes: number | null
  usedTimes: number
  validDays: number | null
  openedOn: string | null
  expiresOn: string | null
  remindOn: string | null
  frozenFrom: string | null
  frozenUntil: string | null
  freezeReason: string | null
  totalFrozenDays: number
  expiringSoon: boolean
  refundableTransactionId: string | null
  termsSnapshot: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export interface MemberCardList { items: MemberCard[]; total: number }

export interface CardTransaction {
  id: string
  memberId: string
  memberCardId: string
  originTransactionId: string | null
  sourceMemberCardId: string | null
  txnType: TransactionType
  amount: string | null
  timesDelta: number | null
  validDaysDelta: number | null
  reason: string | null
  idempotencyKey: string
  traceId: string
  operatorId: string
  operatorRole: UserRole | "system"
  occurredAt: string
}

export interface TransactionOperation { transaction: CardTransaction; memberCard: MemberCard }
export interface TransactionInput {
  txnType: "purchase" | "renew" | "reissue" | "refund" | "extend"
  memberId: string
  cardProductId?: string
  memberCardId?: string
  originTransactionId?: string
  validDaysDelta?: number
  reason?: string
}
