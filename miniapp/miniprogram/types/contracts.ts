export type BusinessRole = "member" | "coach"

export interface CurrentUser {
  username: string
  role: BusinessRole
  memberId?: string
  coachProfileId?: string
}

export interface BoundWechatSession {
  state: "bound"
  accessToken: string
  tokenType: string
  role: BusinessRole
}

export interface BindingRequiredWechatSession {
  state: "binding_required"
  bindingTicket: string
  expiresIn: number
}

export type WechatSession = BoundWechatSession | BindingRequiredWechatSession

export interface WechatBindResult {
  accessToken: string
  tokenType: string
  role: BusinessRole
}

export interface PasswordLoginResult {
  access_token: string
  token_type: string
  role: string
}

export interface ChangePasswordInput {
  oldPassword: string
  newPassword: string
}
