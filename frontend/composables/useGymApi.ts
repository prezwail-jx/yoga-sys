import type { BookingRecord, CardProduct, CardProductInput, CardProductList, CoachSlot, CourseSession, Member, MemberCardList, MemberInput, MemberList, MemberStatus, ReportSummary, TransactionInput, TransactionOperation } from "~/types/domain"

export function useGymApi() {
  const { request } = useApiClient()
  const getMeta = () => request<{ appName: string; roles: string[]; today: string }>("/meta")
  const getMembers = (params: { keyword?: string; status?: MemberStatus; skip?: number; limit?: number } = {}) => request<MemberList>(`/members?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== "").map(([key, value]) => [key, String(value)]))}`)
  const getMember = (id: string) => request<Member>(`/members/${id}`)
  const createMember = (payload: MemberInput) => request<Member>("/members", { method: "POST", body: payload })
  const updateMember = (id: string, payload: Partial<MemberInput> & { status?: MemberStatus }) => request<Member>(`/members/${id}`, { method: "PATCH", body: payload })
  const deleteMember = async (id: string) => { await request<unknown>(`/members/${id}`, { method: "DELETE" }) }
  const getCards = (params: { enabled?: boolean; skip?: number; limit?: number } = {}) => request<CardProductList>(`/card-products?${new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined).map(([key, value]) => [key, String(value)]))}`)
  const createCard = (payload: CardProductInput) => request<CardProduct>("/card-products", { method: "POST", body: payload })
  const updateCard = (id: string, payload: Partial<CardProductInput> & { enabled?: boolean }) => request<CardProduct>(`/card-products/${id}`, { method: "PATCH", body: payload })
  const getMemberCards = (memberId: string) => request<MemberCardList>(`/members/${memberId}/cards`)
  const createTransaction = (payload: TransactionInput, key: string) => request<TransactionOperation>("/transactions", { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const freezeMemberCard = (id: string, payload: { frozenUntil: string; reason: string }, key: string) => request<TransactionOperation>(`/member-cards/${id}/freeze`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const unfreezeMemberCard = (id: string, payload: { reason?: string }, key: string) => request<TransactionOperation>(`/member-cards/${id}/unfreeze`, { method: "POST", body: payload, headers: { "Idempotency-Key": key } })
  const getSchedule = () => request<CourseSession[]>("/schedule")
  const getPrivateSlots = () => request<CoachSlot[]>("/private-slots")
  const getBookings = () => request<BookingRecord[]>("/bookings")
  const getReportSummary = () => request<ReportSummary>("/reports/summary")
  return { getMeta, getMembers, getMember, createMember, updateMember, deleteMember, getCards, createCard, updateCard, getMemberCards, createTransaction, freezeMemberCard, unfreezeMemberCard, getSchedule, getPrivateSlots, getBookings, getReportSummary }
}
