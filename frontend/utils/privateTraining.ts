import type { UserRole } from "~/types/domain"

export function canConfirmPrivateBooking(role: UserRole | undefined, status: string) {
  return (role === "admin" || role === "coach") && status === "pending"
}

export function canRejectPrivateBooking(role: UserRole | undefined, status: string) {
  return canConfirmPrivateBooking(role, status)
}

export function canCancelPendingPrivateBooking(role: UserRole | undefined, status: string) {
  return (role === "admin" || role === "member") && status === "pending"
}

export function canSignInPrivateBooking(role: UserRole | undefined, status: string) {
  return (role === "admin" || role === "coach") && status === "confirmed"
}
