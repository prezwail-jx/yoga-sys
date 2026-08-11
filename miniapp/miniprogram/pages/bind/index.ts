import { ApiError, BindingTicketExpiredError, sessionService } from "../../services/index"

Page({
  data: {
    username: "",
    password: "",
    passwordKey: 0,
    pending: false,
    error: "",
  },
  updateUsername(event: WechatMiniprogram.Input) {
    this.setData({ username: event.detail.value.trim(), error: "" })
  },
  updatePassword(event: WechatMiniprogram.Input) {
    this.setData({ password: event.detail.value, error: "" })
  },
  async submit() {
    if (this.data.pending || !this.data.username || !this.data.password) return
    this.setData({ pending: true, error: "" })
    try {
      await sessionService.bindAndRoute(this.data.username, this.data.password)
      this.setData({ password: "", passwordKey: this.data.passwordKey + 1 })
    } catch (error) {
      const message = error instanceof BindingTicketExpiredError
        ? "绑定凭证已过期，请重新登录"
        : error instanceof ApiError
          ? error.message
          : "绑定失败，请稍后重试"
      this.setData({ password: "", passwordKey: this.data.passwordKey + 1, error: message })
    } finally {
      this.setData({ pending: false })
    }
  },
  restart() {
    sessionService.logout()
  },
})
