import { ApiError, sessionService } from "../../../services/index"

Page({
  data: {
    oldPassword: "",
    newPassword: "",
    confirmation: "",
    pending: false,
    error: "",
    success: "",
  },
  updateOldPassword(event: WechatMiniprogram.Input) {
    this.setData({ oldPassword: event.detail.value, error: "" })
  },
  updateNewPassword(event: WechatMiniprogram.Input) {
    this.setData({ newPassword: event.detail.value, error: "" })
  },
  updateConfirmation(event: WechatMiniprogram.Input) {
    this.setData({ confirmation: event.detail.value, error: "" })
  },
  async submit() {
    const { oldPassword, newPassword, confirmation, pending } = this.data
    if (pending) return
    if (!oldPassword || !newPassword || !confirmation) {
      this.setData({ error: "请填写所有密码字段" })
      return
    }
    if (newPassword.length < 8) {
      this.setData({ error: "新密码至少需要 8 位" })
      return
    }
    if (newPassword !== confirmation) {
      this.setData({ error: "两次输入的新密码不一致" })
      return
    }
    this.setData({ pending: true, error: "", success: "" })
    try {
      await sessionService.changePassword(oldPassword, newPassword)
      this.setData({
        success: "密码修改成功。下次登录请使用新密码。",
        oldPassword: "",
        newPassword: "",
        confirmation: "",
      })
    } catch (error) {
      const message = error instanceof ApiError
        ? error.message
        : "密码修改失败，请稍后重试"
      this.setData({ error: message })
    } finally {
      this.setData({ pending: false })
    }
  },
})
