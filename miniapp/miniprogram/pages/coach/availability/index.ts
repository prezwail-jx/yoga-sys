import { ActionGuard, ApiError, coachService, navigationService, storageService } from "../../../services"
import type { DayGroup, PrivateSlotView } from "../../../types/member"
import { dateKey, mondayOf } from "../../../utils/member-presenter"
import { confirmAction } from "../../../utils/modal"

const DURATION_OPTIONS = [30, 45, 60, 75, 90, 120]
const actions = new ActionGuard()

function localDate(days = 1): string {
  return dateKey(new Date(Date.now() + days * 24 * 60 * 60 * 1000))
}

function interval(date: string, startTime: string, duration: number): { startAt: string; endAt: string } {
  const start = new Date(`${date}T${startTime}:00+08:00`)
  return { startAt: start.toISOString(), endAt: new Date(start.getTime() + duration * 60_000).toISOString() }
}

function slotTime(value: string): string {
  const local = new Date(new Date(value).getTime() + 8 * 60 * 60 * 1000)
  return `${String(local.getUTCHours()).padStart(2, "0")}:${String(local.getUTCMinutes()).padStart(2, "0")}`
}

Page({
  data: {
    groups: [] as DayGroup<PrivateSlotView>[],
    mode: "loading",
    message: "正在加载私教开放时间",
    feedback: "",
    pendingId: "",
    editingId: "",
    slotDate: localDate(),
    startTime: "09:00",
    durationIndex: 2,
    durationOptions: DURATION_OPTIONS,
    weekStart: dateKey(mondayOf(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000))),
    weekdays: [0, 2, 4] as number[],
    conflicts: [] as string[],
  },
  onLoad() {
    if (storageService.user()?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    void this.load()
  },
  async load() {
    const from = new Date().toISOString()
    const to = new Date(Date.now() + 45 * 24 * 60 * 60 * 1000).toISOString()
    this.setData({ mode: "loading", message: "正在加载私教开放时间" })
    try {
      const groups = await coachService.availability(from, to)
      this.setData({ groups, mode: groups.length ? "ready" : "empty", message: groups.length ? "" : "未来 45 天还没有开放时间" })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "开放时间加载失败" })
    }
  },
  changeDate(event: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ slotDate: event.detail.value })
  },
  changeTime(event: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ startTime: event.detail.value })
  },
  changeDuration(event: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ durationIndex: Number(event.detail.value) })
  },
  changeWeekStart(event: WechatMiniprogram.CustomEvent<{ value: string }>) {
    this.setData({ weekStart: event.detail.value })
  },
  changeWeekdays(event: WechatMiniprogram.CustomEvent<{ value: string[] }>) {
    this.setData({ weekdays: event.detail.value.map(Number) })
  },
  edit(event: WechatMiniprogram.CustomEvent) {
    const slotId = event.currentTarget.dataset.id as string
    const startAt = event.currentTarget.dataset.start as string
    const durationMinutes = Number(event.currentTarget.dataset.duration)
    const durationIndex = Math.max(0, DURATION_OPTIONS.indexOf(durationMinutes))
    this.setData({ editingId: slotId, slotDate: dateKey(startAt), startTime: slotTime(startAt), durationIndex })
  },
  resetForm() {
    this.setData({ editingId: "", slotDate: localDate(), startTime: "09:00", durationIndex: 2 })
  },
  async saveSlot() {
    const actionId = this.data.editingId || "create-slot"
    if (actions.isPending(actionId)) return
    const input = interval(this.data.slotDate, this.data.startTime, this.data.durationOptions[this.data.durationIndex])
    this.setData({ pendingId: actionId, feedback: "" })
    try {
      await actions.run(actionId, () => this.data.editingId
        ? coachService.updateSlot(this.data.editingId, input)
        : coachService.createSlot(input))
      this.resetForm()
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "保存失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
  async cancelSlot(event: WechatMiniprogram.CustomEvent) {
    const slotId = event.currentTarget.dataset.id as string
    if (actions.isPending(slotId) || !await confirmAction("取消时段", "取消后会员将无法申请该时段。")) return
    this.setData({ pendingId: slotId, feedback: "" })
    try {
      await actions.run(slotId, () => coachService.cancelSlot(slotId))
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "取消失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
  async generateWeek() {
    const actionId = `week:${this.data.weekStart}`
    if (actions.isPending(actionId) || this.data.weekdays.length === 0) return
    this.setData({ pendingId: actionId, feedback: "", conflicts: [] })
    try {
      const result = await actions.run(actionId, () => coachService.generateWeek({
        weekStart: `${this.data.weekStart}T00:00:00+08:00`,
        weekdays: this.data.weekdays,
        startTime: this.data.startTime,
        durationMinutes: this.data.durationOptions[this.data.durationIndex],
      }))
      this.setData({ conflicts: result?.conflicts.map((item) => `${dateKey(item.startAt)} ${slotTime(item.startAt)} · ${item.reason}`) ?? [] })
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "周生成失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
})
