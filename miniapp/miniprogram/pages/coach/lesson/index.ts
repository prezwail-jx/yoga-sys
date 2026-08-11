import { ActionGuard, ApiError, coachService, navigationService, storageService } from "../../../services"
import type { PrivateBooking } from "../../../types/member"
import { validateLessonInput } from "../../../utils/coach-presenter"

const actions = new ActionGuard()

Page({
  data: {
    bookingId: "",
    booking: null as PrivateBooking | null,
    content: "",
    consumedHours: "1",
    memberStatusNotes: "",
    mode: "loading",
    message: "正在加载私教预约",
    pending: false,
    feedback: "",
  },
  onLoad(query: Record<string, string | undefined>) {
    if (storageService.user()?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    if (!query.bookingId) {
      this.setData({ mode: "error", message: "缺少私教预约信息" })
      return
    }
    this.setData({ bookingId: query.bookingId })
    void this.load()
  },
  async load() {
    try {
      const booking = await coachService.booking(this.data.bookingId)
      this.setData({ booking, mode: "ready", message: "" })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "私教预约加载失败" })
    }
  },
  updateContent(event: WechatMiniprogram.Input) {
    this.setData({ content: event.detail.value, feedback: "" })
  },
  updateHours(event: WechatMiniprogram.Input) {
    this.setData({ consumedHours: event.detail.value, feedback: "" })
  },
  updateNotes(event: WechatMiniprogram.Input) {
    this.setData({ memberStatusNotes: event.detail.value, feedback: "" })
  },
  async submit() {
    const consumedHours = Number(this.data.consumedHours)
    const validationMessage = validateLessonInput(this.data.content, consumedHours)
    if (validationMessage) {
      this.setData({ feedback: validationMessage })
      return
    }
    if (actions.isPending(this.data.bookingId)) return
    this.setData({ pending: true, feedback: "" })
    try {
      await actions.run(this.data.bookingId, () => coachService.signInPrivate(this.data.bookingId, {
        content: this.data.content.trim(),
        consumedHours,
        memberStatusNotes: this.data.memberStatusNotes.trim() || undefined,
      }))
      wx.showToast({ title: "签到完成", icon: "success" })
      navigationService.routeAuthenticated(storageService.user()!)
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "签到失败，请稍后重试" })
    } finally {
      this.setData({ pending: false })
    }
  },
})
