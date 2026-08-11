import { apiBaseUrl } from "../config/environment"
import { runtime } from "../platform/runtime"
import { ApiClient } from "./api"
import { IdempotencyService } from "./idempotency"
import { MemberService } from "./member"
import { CoachService } from "./coach"
import { NavigationService } from "./navigation"
import { SessionService } from "./session"
import { StorageService } from "./storage"

export const storageService = new StorageService(runtime)
export const navigationService = new NavigationService(runtime)
export const apiClient = new ApiClient(
  runtime,
  apiBaseUrl(runtime),
  () => storageService.token(),
  () => storageService.clearSession(),
)
export const idempotencyService = new IdempotencyService(storageService)
export const memberService = new MemberService(apiClient, idempotencyService, storageService)
export const coachService = new CoachService(apiClient, idempotencyService, storageService)
export const sessionService = new SessionService(
  runtime,
  apiClient,
  storageService,
  navigationService,
)

export { ApiError, type ApiErrorKind } from "./api"
export { idempotentMutation } from "./idempotency"
export { navigationForRole } from "./navigation"
export { BindingTicketExpiredError } from "./session"
export { ActionGuard } from "./action-guard"
