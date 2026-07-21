export type UserRole = "admin" | "coach" | "member"
export type MemberStatus = "normal" | "paused" | "expired" | "disabled"
export type CardType = "duration" | "times" | "private" | "trial"
export type ActivationMode = "immediate" | "first_booking"
export type CourseScope = "group" | "private" | "specific"

export interface CurrentUser {
  username: string
  role: UserRole
  memberId?: string | null
  coachProfileId?: string | null
}

export type CourseDifficulty = "all_levels" | "beginner" | "intermediate" | "advanced"
export type ClassSessionStatus = "draft" | "published" | "paused" | "cancelled" | "completed"
export type ClassBookingStatus = "reserved" | "checked_in" | "cancelled" | "absent"

export interface Course {
  id: string
  name: string
  durationMinutes: number
  difficulty: CourseDifficulty
  description: string | null
  coverUrl: string | null
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface CourseInput {
  name: string
  durationMinutes: number
  difficulty?: CourseDifficulty
  description?: string | null
  coverUrl?: string | null
  enabled?: boolean
}

export interface CourseList {
  items: Course[]
  total: number
  skip: number
  limit: number
}

export interface Room {
  id: string
  name: string
  capacity: number
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface RoomInput {
  name: string
  capacity: number
  enabled?: boolean
}

export interface RoomList {
  items: Room[]
  total: number
  skip: number
  limit: number
}

export interface CoachProfile {
  id: string
  name: string
  avatarUrl: string | null
  bio: string | null
  specialtyCourseIds: string[] | null
  enabled: boolean
  createdAt: string
  updatedAt: string
}

export interface CoachProfileInput {
  name: string
  avatarUrl?: string | null
  bio?: string | null
  specialtyCourseIds?: string[] | null
  enabled?: boolean
}

export interface CoachProfileList {
  items: CoachProfile[]
  total: number
  skip: number
  limit: number
}

export interface ClassSession {
  id: string
  courseId: string
  coachProfileId: string
  roomId: string
  courseName: string
  coachName: string
  roomName: string
  startAt: string
  endAt: string
  capacity: number
  bookingOpenHoursBefore: number
  bookingCloseMinutesBefore: number
  cancelCutoffMinutesBefore: number
  status: ClassSessionStatus
  sourceSessionId: string | null
  createdBy: string
  bookedCount: number
  remainingCapacity: number
  isFull: boolean
  createdAt: string
  updatedAt: string
}

export interface ClassSessionInput {
  courseId: string
  coachProfileId: string
  roomId: string
  startAt: string
  endAt: string
  capacity: number
  bookingOpenHoursBefore?: number
  bookingCloseMinutesBefore?: number
  cancelCutoffMinutesBefore?: number
}

export interface ClassSessionList {
  items: ClassSession[]
  weekStart: string
  weekEnd: string
}

export interface CopyWeekInput {
  sourceWeekStart: string
  targetWeekStart: string
}

export interface CopyWeekConflict {
  sourceSessionId: string
  targetStartAt: string
  reason: string
}

export interface CopyWeekResult {
  created: ClassSession[]
  conflicts: CopyWeekConflict[]
}

export interface ClassBooking {
  id: string
  classSessionId: string
  memberId: string
  memberName: string
  courseName: string
  coachName: string
  roomName: string
  startAt: string
  endAt: string
  sessionStatus: ClassSessionStatus
  status: ClassBookingStatus
  bookedById: string | null
  bookedByRole: string | null
  bookedAt: string
  terminalById: string | null
  terminalByRole: string | null
  terminalAt: string | null
  cancellationReason: string | null
  traceId: string
  createdAt: string
  updatedAt: string
}

export interface ClassBookingList {
  items: ClassBooking[]
  total: number
  skip: number
  limit: number
}

export interface CreateClassBookingInput {
  memberId?: string | null
}

export interface CancelClassBookingInput {
  reason?: string | null
}

export interface AccountBindingInput {
  username: string
  initialPassword: string
}

export interface AccountBinding {
  id: string
  username: string
  role: "member" | "coach"
  memberId: string | null
  coachProfileId: string | null
  createdAt: string
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

export type TimelineCategory = "all" | "transaction" | "writeoff" | "audit"
export type WriteOffEventType = "reserve_hold" | "checkin_commit" | "cancel_refund" | "absence_commit"

export interface TimelineEvent {
  id: string
  source: "transaction" | "writeoff" | "audit"
  action: string
  result: "success" | "rejected" | "failed"
  occurredAt: string
  traceId: string
  memberCardId: string | null
  businessRef: string | null
  sequenceNo: number | null
  timesDelta: number | null
  amount: string | null
  productName: string | null
  cardType: CardType | null
  validDaysDelta: number | null
  reason: string | null
  operatorId: string | null
  operatorRole: UserRole | "system" | null
  objectType: string | null
  objectId: string | null
  summary: string
}

export interface TimelineList { items: TimelineEvent[]; total: number; skip: number; limit: number }
export interface TimelineQuery {
  category?: TimelineCategory
  action?: string
  dateFrom?: string
  dateTo?: string
  businessRef?: string
  skip?: number
  limit?: number
}

export interface WriteOffEvent {
  id: string
  memberId: string
  memberCardId: string
  previousEventId: string | null
  eventType: WriteOffEventType
  businessRef: string
  sequenceNo: number
  timesDelta: number
  selectionBasis: string
  idempotencyKey: string
  traceId: string
  operatorId: string
  operatorRole: UserRole | "system"
  occurredAt: string
}
