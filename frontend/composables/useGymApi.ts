import type { AccountBinding, AccountBindingInput, CancelClassBookingInput, CardProduct, CardProductInput, CardProductList, ChangePasswordInput, ClassBooking, ClassBookingList, ClassSession, ClassSessionInput, ClassSessionList, CoachProfile, CoachProfileInput, CoachProfileList, CopyWeekInput, CopyWeekResult, Course, CourseInput, CourseList, CourseSession, CreateClassBookingInput, Member, MemberCardList, MemberInput, MemberList, MemberStatus, PasswordResetInput, PrivateBooking, PrivateBookingDecisionInput, PrivateBookingInput, PrivateBookingList, PrivateLessonRecordInput, PrivateSlot, PrivateSlotInput, PrivateSlotList, PrivateWeekInput, PrivateWeekResult, ReportDetail, ReportDetailCategory, ReportQuery, ReportSummary, ReportTrend, ReportTrendCategory, Room, RoomInput, RoomList, TimelineList, TimelineQuery, TransactionInput, TransactionOperation, WechatBindingStatus, WriteOffEvent, WriteOffEventType } from "~/types/domain"

type CatalogQuery = { keyword?: string; enabled?: boolean; skip?: number; limit?: number }

function queryString(params: object): string {
  return new URLSearchParams(
    Object.entries(params)
      .filter(([, value]) => value !== undefined && value !== "")
      .map(([key, value]) => [key, String(value)]),
  ).toString()
}

export function useGymApi() {
  const { request } = useApiClient()
  const getMeta = () => request<{ appName: string; roles: string[]; today: string }>("/meta")
  const getMembers = (params: { keyword?: string; status?: MemberStatus; skip?: number; limit?: number } = {}) => request<MemberList>(`/members?${queryString(params)}`)
  const getMember = (id: string) => request<Member>(`/members/${id}`)
  const createMember = (payload: MemberInput) => request<Member>("/members", { method: "POST", body: payload })
  const updateMember = (id: string, payload: Partial<MemberInput> & { status?: MemberStatus }) => request<Member>(`/members/${id}`, { method: "PATCH", body: payload })
  const deleteMember = async (id: string) => { await request<unknown>(`/members/${id}`, { method: "DELETE" }) }
  const getCards = (params: { enabled?: boolean; skip?: number; limit?: number } = {}) => request<CardProductList>(`/card-products?${queryString(params)}`)
  const createCard = (payload: CardProductInput) => request<CardProduct>("/card-products", { method: "POST", body: payload })
  const updateCard = (id: string, payload: Partial<CardProductInput> & { enabled?: boolean }) => request<CardProduct>(`/card-products/${id}`, { method: "PATCH", body: payload })
  const getMemberCards = (memberId: string) => request<MemberCardList>(`/members/${memberId}/cards`)
  const createTransaction = (payload: TransactionInput, key: string) => request<TransactionOperation>("/transactions", { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const freezeMemberCard = (id: string, payload: { frozenUntil: string; reason: string }, key: string) => request<TransactionOperation>(`/member-cards/${id}/freeze`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const unfreezeMemberCard = (id: string, payload: { reason?: string }, key: string) => request<TransactionOperation>(`/member-cards/${id}/unfreeze`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const adjustMemberCardTimes = (id: string, payload: { timesDelta: number; reason: string }, key: string) => request<TransactionOperation>(`/member-cards/${id}/adjust-times`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const getMemberTimeline = (memberId: string, params: TimelineQuery = {}) => request<TimelineList>(`/members/${memberId}/timeline?${queryString(params)}`)
  const createWriteOffEvent = (payload: { memberId: string; businessRef: string; eventType: WriteOffEventType }, key: string) => request<WriteOffEvent>("/writeoff/events", { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const getCourses = (params: CatalogQuery = {}) => request<CourseList>(`/courses?${queryString(params)}`)
  const getCourse = (id: string) => request<Course>(`/courses/${id}`)
  const createCourse = (payload: CourseInput) => request<Course>("/courses", { method: "POST", body: payload })
  const updateCourse = (id: string, payload: Partial<CourseInput>) => request<Course>(`/courses/${id}`, { method: "PATCH", body: payload })
  const getRooms = (params: CatalogQuery = {}) => request<RoomList>(`/rooms?${queryString(params)}`)
  const getRoom = (id: string) => request<Room>(`/rooms/${id}`)
  const createRoom = (payload: RoomInput) => request<Room>("/rooms", { method: "POST", body: payload })
  const updateRoom = (id: string, payload: Partial<RoomInput>) => request<Room>(`/rooms/${id}`, { method: "PATCH", body: payload })
  const getCoaches = (params: CatalogQuery = {}) => request<CoachProfileList>(`/coaches?${queryString(params)}`)
  const getCoach = (id: string) => request<CoachProfile>(`/coaches/${id}`)
  const createCoach = (payload: CoachProfileInput) => request<CoachProfile>("/coaches", { method: "POST", body: payload })
  const updateCoach = (id: string, payload: Partial<CoachProfileInput>) => request<CoachProfile>(`/coaches/${id}`, { method: "PATCH", body: payload })
  const getClassSessions = (weekStart: string) => request<ClassSessionList>(`/class-sessions?${queryString({ weekStart })}`)
  const getClassSession = (id: string) => request<ClassSession>(`/class-sessions/${id}`)
  const createClassSession = (payload: ClassSessionInput) => request<ClassSession>("/class-sessions", { method: "POST", body: payload })
  const updateClassSession = (id: string, payload: Partial<ClassSessionInput>) => request<ClassSession>(`/class-sessions/${id}`, { method: "PATCH", body: payload })
  const publishClassSession = (id: string) => request<ClassSession>(`/class-sessions/${id}/publish`, { method: "POST" })
  const pauseClassSession = (id: string) => request<ClassSession>(`/class-sessions/${id}/pause`, { method: "POST" })
  const resumeClassSession = (id: string) => request<ClassSession>(`/class-sessions/${id}/resume`, { method: "POST" })
  const cancelClassSession = (id: string, idempotencyKey: string) => request<ClassSession>(`/class-sessions/${id}/cancel`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey } })
  const completeClassSession = (id: string, idempotencyKey: string) => request<ClassSession>(`/class-sessions/${id}/complete`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey } })
  const copyClassSessionWeek = (payload: CopyWeekInput, idempotencyKey: string) => request<CopyWeekResult>("/class-sessions/copy-week", { method: "POST", body: payload, headers: { "Idempotency-Key": idempotencyKey } })
  const getClassSessionBookings = (sessionId: string) => request<ClassBookingList>(`/class-sessions/${sessionId}/bookings`)
  const createClassBooking = (sessionId: string, payload: CreateClassBookingInput, idempotencyKey: string) => request<ClassBooking>(`/class-sessions/${sessionId}/bookings`, { method: "POST", body: payload, headers: { "Idempotency-Key": idempotencyKey } })
  const createMemberClassBooking = (sessionId: string, idempotencyKey: string) => createClassBooking(sessionId, {}, idempotencyKey)
  const createAdminClassBooking = (sessionId: string, memberId: string, idempotencyKey: string) => createClassBooking(sessionId, { memberId }, idempotencyKey)
  const cancelClassBooking = (bookingId: string, payload: CancelClassBookingInput, idempotencyKey: string) => request<ClassBooking>(`/class-bookings/${bookingId}/cancel`, { method: "POST", body: payload, headers: { "Idempotency-Key": idempotencyKey } })
  const checkInClassBooking = (bookingId: string, idempotencyKey: string) => request<ClassBooking>(`/class-bookings/${bookingId}/check-in`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey } })
  const getMyClassBookings = (params: { skip?: number; limit?: number } = {}) => request<ClassBookingList>(`/members/me/bookings?${queryString(params)}`)
  const createMemberAccount = (memberId: string, payload: AccountBindingInput, idempotencyKey: string) => request<AccountBinding>(`/members/${memberId}/account`, { method: "POST", body: payload, headers: { "Idempotency-Key": idempotencyKey } })
  const createCoachAccount = (coachId: string, payload: AccountBindingInput, idempotencyKey: string) => request<AccountBinding>(`/coaches/${coachId}/account`, { method: "POST", body: payload, headers: { "Idempotency-Key": idempotencyKey } })
  const resetMemberPassword = (memberId: string, payload: PasswordResetInput) => request<unknown>(`/members/${memberId}/account/reset-password`, { method: "POST", body: payload })
  const resetCoachPassword = (coachId: string, payload: PasswordResetInput) => request<unknown>(`/coaches/${coachId}/account/reset-password`, { method: "POST", body: payload })
  const changePassword = (payload: ChangePasswordInput) => request<unknown>("/auth/change-password", { method: "POST", body: payload })
  const getWechatBindingStatus = (accountId: string) => request<WechatBindingStatus>(`/accounts/${encodeURIComponent(accountId)}/wechat-binding`)
  const unbindWechat = (accountId: string) => request<unknown>(`/accounts/${encodeURIComponent(accountId)}/wechat-binding`, { method: "DELETE", body: { confirm: true } })
  const getSchedule = () => request<CourseSession[]>("/schedule")
  const getPrivateSlots = (params: ReportQuery = {}) => request<PrivateSlotList>(`/private-slots?${queryString(params)}`)
  const createPrivateSlot = (payload: PrivateSlotInput) => request<PrivateSlot>("/private-slots", { method: "POST", body: payload })
  const updatePrivateSlot = (id: string, payload: PrivateSlotInput) => request<PrivateSlot>(`/private-slots/${id}`, { method: "PATCH", body: payload })
  const deletePrivateSlot = (id: string) => request<PrivateSlot>(`/private-slots/${id}`, { method: "DELETE" })
  const generatePrivateWeek = (payload: PrivateWeekInput, key: string) => request<PrivateWeekResult>("/private-slots/generate-week", { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const getPrivateBookings = (params: { status?: string; skip?: number; limit?: number } = {}) => request<PrivateBookingList>(`/private-bookings?${queryString(params)}`)
  const createPrivateBooking = (payload: PrivateBookingInput, key: string) => request<PrivateBooking>("/private-bookings", { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const confirmPrivateBooking = (id: string, key: string) => request<PrivateBooking>(`/private-bookings/${id}/confirm`, { method: "POST", headers: { "Idempotency-Key": key } })
  const rejectPrivateBooking = (id: string, payload: PrivateBookingDecisionInput, key: string) => request<PrivateBooking>(`/private-bookings/${id}/reject`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const cancelPrivateBooking = (id: string, payload: PrivateBookingDecisionInput, key: string) => request<PrivateBooking>(`/private-bookings/${id}/cancel`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const signInPrivateBooking = (id: string, payload: PrivateLessonRecordInput, key: string) => request<PrivateBooking>(`/private-bookings/${id}/sign-in`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const getReportSummary = (params: ReportQuery = {}) => request<ReportSummary>(`/reports/summary?${queryString(params)}`)
  const getReportTrend = (category: ReportTrendCategory, params: ReportQuery = {}) => request<ReportTrend>(`/reports/trends?${queryString({ category, ...params })}`)
  const getReportDetail = (category: ReportDetailCategory, params: ReportQuery & { skip?: number; limit?: number } = {}) => request<ReportDetail>(`/reports/details/${category}?${queryString(params)}`)
  const exportReport = async (category: ReportDetailCategory, params: ReportQuery = {}) => {
    const response = await $fetch.raw(`/api/reports/export?${queryString({ category, ...params })}`, { responseType: "blob" })
    const blob = response._data as unknown as Blob
    const disposition = response.headers.get("content-disposition") || ""
    const filename = disposition.match(/filename="?([^";]+)"?/)?.[1] || `report-${category}.xlsx`
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = filename
    link.click()
    URL.revokeObjectURL(url)
  }
  return { getMeta, getMembers, getMember, createMember, updateMember, deleteMember, getCards, createCard, updateCard, getMemberCards, createTransaction, freezeMemberCard, unfreezeMemberCard, adjustMemberCardTimes, getMemberTimeline, createWriteOffEvent, getCourses, getCourse, createCourse, updateCourse, getRooms, getRoom, createRoom, updateRoom, getCoaches, getCoach, createCoach, updateCoach, getClassSessions, getClassSession, createClassSession, updateClassSession, publishClassSession, pauseClassSession, resumeClassSession, cancelClassSession, completeClassSession, copyClassSessionWeek, getClassSessionBookings, createClassBooking, createMemberClassBooking, createAdminClassBooking, cancelClassBooking, checkInClassBooking, getMyClassBookings, createMemberAccount, createCoachAccount, resetMemberPassword, resetCoachPassword, changePassword, getWechatBindingStatus, unbindWechat, getSchedule, getPrivateSlots, createPrivateSlot, updatePrivateSlot, deletePrivateSlot, generatePrivateWeek, getPrivateBookings, createPrivateBooking, confirmPrivateBooking, rejectPrivateBooking, cancelPrivateBooking, signInPrivateBooking, getReportSummary, getReportTrend, getReportDetail, exportReport }
}
