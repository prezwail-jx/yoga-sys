import { ActionGuard, ApiError, memberService, navigationService, storageService } from "../../../services"
import type { ClassBookingView, PrivateBookingView } from "../../../types/member"
import { promptAction } from "../../../utils/modal"

const PAGE_SIZE = 20
const actions = new ActionGuard()

Page({
  data: {
    tab: "class" as "class" | "private",
    classItems: [] as ClassBookingView[],
    privateItems: [] as PrivateBookingView[],
    total: 0,
    mode: "loading",
    message: "正在加载预约记录",
    pendingId: "",
    feedback: "",
  },
  onLoad(query: Record<string, string | undefined>) {
    if (storageService.user()?.role !== "member") {
      navigationService.routeForbidden()
      return
    }
    this.setData({ tab: query.tab === "private" ? "private" : "class" })
    void this.load(true)
  },
  switchTab(event: WechatMiniprogram.CustomEvent) {
    const tab = event.currentTarget.dataset.tab as "class" | "private"
    if (tab === this.data.tab) return
    this.setData({ tab, feedback: "" })
    void this.load(true)
  },
  async load(reset = false) {
    const current = this.data.tab === "class" ? this.data.classItems : this.data.privateItems
    const skip = reset ? 0 : current.length
    if (reset) this.setData({ mode: "loading", message: "正在加载预约记录" })
    try {
      if (this.data.tab === "class") {
        const page = await memberService.classBookings(skip, PAGE_SIZE)
        const classItems = reset ? page.items : [...this.data.classItems, ...page.items]
        this.setData({ classItems, total: page.total, mode: classItems.length ? "ready" : "empty", message: classItems.length ? "" : "还没有团课预约" })
      } else {
        const page = await memberService.privateBookings(skip, PAGE_SIZE)
        const privateItems = reset ? page.items : [...this.data.privateItems, ...page.items]
        this.setData({ privateItems, total: page.total, mode: privateItems.length ? "ready" : "empty", message: privateItems.length ? "" : "还没有私教申请" })
      }
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "预约记录加载失败" })
    }
  },
  loadMore() {
    void this.load(false)
  },
  async cancelClass(event: WechatMiniprogram.CustomEvent) {
    await this.cancel(event.currentTarget.dataset.id as string, "class")
  },
  async cancelPrivate(event: WechatMiniprogram.CustomEvent) {
    await this.cancel(event.currentTarget.dataset.id as string, "private")
  },
  async cancel(bookingId: string, type: "class" | "private") {
    if (actions.isPending(bookingId)) return
    const reason = await promptAction("取消预约", "取消原因（可选）")
    if (reason === null) return
    this.setData({ pendingId: bookingId, feedback: "" })
    try {
      await actions.run(bookingId, async () => {
        if (type === "class") {
          await memberService.cancelClass(bookingId, reason)
        } else {
          await memberService.cancelPrivateBooking(bookingId, reason)
        }
      })
      await this.load(true)
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "取消失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
  browse() {
    navigationService.open(this.data.tab === "class" ? "/pages/member/schedule/index" : "/pages/member/private-training/index")
  },
})
