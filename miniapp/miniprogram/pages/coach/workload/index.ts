import { ActionGuard, ApiError, coachService, navigationService, storageService } from "../../../services"
import type { PrivateBookingStatus, PrivateBookingView } from "../../../types/member"
import { confirmAction, promptAction } from "../../../utils/modal"

const PAGE_SIZE = 20
const actions = new ActionGuard()

Page({
  data: {
    status: "pending" as PrivateBookingStatus,
    statuses: ["pending", "confirmed", "completed", "rejected", "cancelled"] as PrivateBookingStatus[],
    items: [] as PrivateBookingView[],
    total: 0,
    mode: "loading",
    message: "正在加载私教工作",
    feedback: "",
    pendingId: "",
  },
  onLoad() {
    if (storageService.user()?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    void this.load(true)
  },
  switchStatus(event: WechatMiniprogram.CustomEvent) {
    this.setData({ status: event.currentTarget.dataset.status as PrivateBookingStatus, feedback: "" })
    void this.load(true)
  },
  async load(reset = false) {
    const skip = reset ? 0 : this.data.items.length
    if (reset) this.setData({ mode: "loading", message: "正在加载私教工作" })
    try {
      const page = await coachService.workload(this.data.status, skip, PAGE_SIZE)
      const items = reset ? page.items : [...this.data.items, ...page.items]
      this.setData({ items, total: page.total, mode: items.length ? "ready" : "empty", message: items.length ? "" : `暂无 ${this.data.status} 私教记录` })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "私教工作加载失败" })
    }
  },
  loadMore() {
    void this.load(false)
  },
  async confirm(event: WechatMiniprogram.CustomEvent) {
    const bookingId = event.currentTarget.dataset.id as string
    const memberName = event.currentTarget.dataset.name as string
    if (actions.isPending(bookingId) || !await confirmAction("确认私教", `接受 ${memberName} 的私教申请？`)) return
    await this.runAction(bookingId, () => coachService.confirmPrivate(bookingId))
  },
  async reject(event: WechatMiniprogram.CustomEvent) {
    const bookingId = event.currentTarget.dataset.id as string
    if (actions.isPending(bookingId)) return
    const reason = await promptAction("拒绝申请", "拒绝原因（可选）")
    if (reason === null) return
    await this.runAction(bookingId, () => coachService.rejectPrivate(bookingId, reason))
  },
  lesson(event: WechatMiniprogram.CustomEvent) {
    navigationService.open(`/pages/coach/lesson/index?bookingId=${encodeURIComponent(event.currentTarget.dataset.id as string)}`)
  },
  async runAction(bookingId: string, action: () => Promise<unknown>) {
    this.setData({ pendingId: bookingId, feedback: "" })
    try {
      await actions.run(bookingId, action)
      await this.load(true)
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "操作失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
})
