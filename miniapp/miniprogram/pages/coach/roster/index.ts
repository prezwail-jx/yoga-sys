import { ActionGuard, ApiError, coachService, navigationService, storageService } from "../../../services/index"
import type { RosterBooking } from "../../../types/coach"
import type { ClassSession } from "../../../types/member"
import { confirmAction } from "../../../utils/modal"

const actions = new ActionGuard()

Page({
  data: {
    sessionId: "",
    session: null as ClassSession | null,
    items: [] as RosterBooking[],
    mode: "loading",
    message: "正在加载签到名册",
    pendingId: "",
    feedback: "",
  },
  onLoad(query: Record<string, string | undefined>) {
    if (storageService.user()?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    if (!query.sessionId) {
      this.setData({ mode: "error", message: "缺少课次信息" })
      return
    }
    this.setData({ sessionId: query.sessionId })
    void this.load()
  },
  async load() {
    this.setData({ mode: "loading", message: "正在加载签到名册", feedback: "" })
    try {
      const result = await coachService.roster(this.data.sessionId)
      this.setData({ session: result.session, items: result.items, mode: result.items.length ? "ready" : "empty", message: result.items.length ? "" : "本课次还没有预约会员" })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "名册加载失败" })
    }
  },
  async checkIn(event: WechatMiniprogram.CustomEvent) {
    const bookingId = event.currentTarget.dataset.id as string
    const memberName = event.currentTarget.dataset.name as string
    if (actions.isPending(bookingId)) return
    if (!await confirmAction("确认签到", `确认 ${memberName} 已到课？`)) return
    this.setData({ pendingId: bookingId, feedback: "" })
    try {
      await actions.run(bookingId, () => coachService.checkIn(bookingId))
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "签到失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
})
