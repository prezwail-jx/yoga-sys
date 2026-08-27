import { ApiError, sessionService } from "../../services/index"

Page({
  data: {
    mode: "loading",
    message: "正在恢复你的工作台",
    accountLoginEnabled: false,
    release: false,
    username: "",
    password: "",
    pending: false,
    error: "",
  },
  onLoad() {
    const accountLoginEnabled = sessionService.isPasswordLoginEnabled()
    const release = sessionService.isReleaseEnvironment()
    this.setData({ accountLoginEnabled, release })
    if (sessionService.shouldShowLoginChoice()) {
      this.setData({ mode: "login_choice", message: "" })
      return
    }
    if (sessionService.isSignedOut()) {
      this.setData({ mode: "signed_out", message: "你已退出登录" })
      return
    }
    void this.start()
  },
  async start() {
    this.setData({ mode: "loading", message: "正在恢复你的工作台" })
    try {
      await sessionService.loginAndRoute()
    } catch {
      if (this.data.accountLoginEnabled) {
        this.setData({ mode: "login_choice", error: "微信登录失败，可重试或使用测试账号登录" })
      } else {
        this.setData({ mode: "error", message: "暂时无法连接，请检查网络后重试" })
      }
    }
  },
  updateUsername(event: WechatMiniprogram.Input) {
    this.setData({ username: event.detail.value.trim(), error: "" })
  },
  updatePassword(event: WechatMiniprogram.Input) {
    this.setData({ password: event.detail.value, error: "" })
  },
  async passwordLogin() {
    if (this.data.pending || !this.data.username || !this.data.password) return
    this.setData({ pending: true, error: "" })
    try {
      await sessionService.passwordLoginAndRoute(this.data.username, this.data.password)
    } catch (error) {
      const message = error instanceof ApiError && error.kind === "authentication"
        ? "用户名或密码错误"
        : error instanceof ApiError
          ? error.message
          : "账号登录失败，请稍后重试"
      this.setData({ error: message })
    } finally {
      this.setData({ password: "", pending: false })
    }
  },
})
