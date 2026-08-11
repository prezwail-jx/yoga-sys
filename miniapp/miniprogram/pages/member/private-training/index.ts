import { ActionGuard, ApiError, memberService, navigationService, storageService } from "../../../services"
import type { DayGroup, PrivateBookingView, PrivateSlotView } from "../../../types/member"
import { promptAction } from "../../../utils/modal"

const actions = new ActionGuard()

function range(days: number): { from: string; to: string } {
  const from = new Date()
  const to = new Date(from.getTime() + days * 24 * 60 * 60 * 1000)
  return { from: from.toISOString(), to: to.toISOString() }
}

Page({
  data: {
    groups: [] as DayGroup<PrivateSlotView>[],
    pendingBookings: [] as PrivateBookingView[],
    mode: "loading",
    message: "正在读取教练开放时间",
    pendingId: "",
    feedback: "",
  },
  onLoad() {
    if (storageService.user()?.role !== "member") {
      navigationService.routeForbidden()
      return
    }
    void this.load()
  },
  async load() {
    this.setData({ mode: "loading", message: "正在读取教练开放时间", feedback: "" })
    try {
      const dates = range(30)
      const [groups, bookings] = await Promise.all([
        memberService.privateSlots(dates.from, dates.to),
        memberService.privateBookings(0, 20),
      ])
      const pendingBookings = bookings.items.filter((booking) => booking.status === "pending")
      this.setData({
        groups,
        pendingBookings,
        mode: groups.length || pendingBookings.length ? "ready" : "empty",
        message: groups.length || pendingBookings.length ? "" : "未来 30 天暂无开放私教时间",
      })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "私教时间加载失败" })
    }
  },
  async requestSlot(event: WechatMiniprogram.CustomEvent) {
    const slotId = event.currentTarget.dataset.id as string
    if (actions.isPending(slotId)) return
    const message = await promptAction("申请私教", "给教练的留言（可选）")
    if (message === null) return
    this.setData({ pendingId: slotId, feedback: "" })
    try {
      await actions.run(slotId, () => memberService.requestPrivateSlot(slotId, message))
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "申请失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
  openBookings() {
    navigationService.open("/pages/member/bookings/index?tab=private")
  },
})
