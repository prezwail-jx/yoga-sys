import { ActionGuard, adminService, navigationService, storageService } from "../../../services/index"
import type { Coach, PrivateBooking, PrivateSlot } from "../../../types/admin"
import { privateBookingStatusLabels, privateSlotStatusLabels, schedulingConflictLabel } from "../../../utils/admin-presenter"
import { dateKey, mondayOf, timeLabel } from "../../../utils/member-presenter"
import { confirmAction, promptAction } from "../../../utils/modal"

type SlotView = PrivateSlot & { statusLabel: string; timeLabel: string }
type BookingView = PrivateBooking & { statusLabel: string; timeLabel: string }
const guard = new ActionGuard()
const currentWeek = dateKey(mondayOf(new Date()))

Page({
  data: {
    tab: "bookings", slots: [] as SlotView[], bookings: [] as BookingView[], coaches: [] as Coach[], coachNames: [] as string[],
    coachIndex: 0, editingId: "", slotDate: dateKey(new Date()), slotStartTime: "09:00", slotEndTime: "10:00",
    weekStart: currentWeek, weekStartTime: "09:00", durationMinutes: "60", selectedWeekdays: [0, 1, 2, 3, 4] as number[],
    weekdayOptions: [{ label: "周一", value: 0, checked: true }, { label: "周二", value: 1, checked: true }, { label: "周三", value: 2, checked: true }, { label: "周四", value: 3, checked: true }, { label: "周五", value: 4, checked: true }, { label: "周六", value: 5, checked: false }, { label: "周日", value: 6, checked: false }],
    batchFeedback: "", batchConflicts: [] as string[], mode: "loading", message: "正在加载私教业务", error: "", pendingId: "",
  },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  tab(e: WechatMiniprogram.TouchEvent) { this.setData({ tab: String(e.currentTarget.dataset.tab) }) },
  async load() {
    try {
      const [slots, bookings, coaches] = await Promise.all([adminService.privateSlots(), adminService.privateBookings(), adminService.coaches()])
      const enabledCoaches = coaches.items.filter(item => item.enabled)
      this.setData({
        slots: slots.items.map(item => ({ ...item, statusLabel: privateSlotStatusLabels[item.status], timeLabel: timeLabel(item.startAt, item.endAt) })),
        bookings: bookings.items.map(item => ({ ...item, statusLabel: privateBookingStatusLabels[item.status], timeLabel: timeLabel(item.startAt, item.endAt) })),
        coaches: enabledCoaches, coachNames: enabledCoaches.map(item => item.name), mode: "ready", message: "",
      })
    } catch { this.setData({ mode: "error", message: "私教业务加载失败" }) }
  },
  chooseCoach(e: WechatMiniprogram.PickerChange) { this.setData({ coachIndex: Number(e.detail.value) }) },
  slotDate(e: WechatMiniprogram.PickerChange) { this.setData({ slotDate: String(e.detail.value) }) },
  slotTime(e: WechatMiniprogram.PickerChange) { this.setData({ [String(e.currentTarget.dataset.field)]: String(e.detail.value) }) },
  weekDate(e: WechatMiniprogram.PickerChange) { const value = dateKey(mondayOf(new Date(`${String(e.detail.value)}T00:00:00+08:00`))); this.setData({ weekStart: value, batchFeedback: "", batchConflicts: [] }) },
  duration(e: WechatMiniprogram.Input) { this.setData({ durationMinutes: e.detail.value }) },
  weekdays(e: WechatMiniprogram.CheckboxGroupChange) { const selectedWeekdays = e.detail.value.map(Number); this.setData({ selectedWeekdays, weekdayOptions: this.data.weekdayOptions.map(item => ({ ...item, checked: selectedWeekdays.includes(item.value) })), batchFeedback: "", batchConflicts: [] }) },
  editSlot(e: WechatMiniprogram.TouchEvent) {
    const slot = this.data.slots.find(item => item.id === String(e.currentTarget.dataset.id)); if (!slot) return
    const times = timeLabel(slot.startAt, slot.endAt).split(" - ")
    const coachIndex = Math.max(0, this.data.coaches.findIndex(item => item.id === slot.coachProfileId))
    this.setData({ tab: "slots", editingId: slot.id, coachIndex, slotDate: dateKey(slot.startAt), slotStartTime: times[0], slotEndTime: times[1], error: "" })
  },
  cancelEdit() { this.setData({ editingId: "", error: "" }) },
  async saveSlot() {
    const coach = this.data.coaches[this.data.coachIndex]
    if (!coach) return this.setData({ error: "请选择已启用的教练" })
    if (this.data.slotEndTime <= this.data.slotStartTime) return this.setData({ error: "结束时间必须晚于开始时间" })
    const startAt = `${this.data.slotDate}T${this.data.slotStartTime}:00+08:00`; const endAt = `${this.data.slotDate}T${this.data.slotEndTime}:00+08:00`
    const title = this.data.editingId ? "确认修改时段" : "确认新增时段"
    if (!await confirmAction(title, `${coach.name} · ${this.data.slotDate} ${this.data.slotStartTime}-${this.data.slotEndTime}`)) return
    const id = this.data.editingId
    await this.run(id ? `update-slot:${id}` : "create-slot", () => id ? adminService.updatePrivateSlot(id, coach.id, startAt, endAt) : adminService.createPrivateSlot(coach.id, startAt, endAt))
    this.setData({ editingId: "" })
  },
  async deleteSlot(e: WechatMiniprogram.TouchEvent) {
    const id = String(e.currentTarget.dataset.id)
    if (!await confirmAction("确认删除私教时段", "删除后该时段将标记为已取消，不能继续预约。")) return
    await this.run(`delete-slot:${id}`, () => adminService.deletePrivateSlot(id))
  },
  async generateWeek() {
    if (this.data.pendingId) return
    const coach = this.data.coaches[this.data.coachIndex]; const durationMinutes = Number(this.data.durationMinutes)
    if (!coach) return this.setData({ error: "请选择已启用的教练" })
    if (!this.data.selectedWeekdays.length) return this.setData({ error: "请至少选择一个星期" })
    if (!Number.isInteger(durationMinutes) || durationMinutes <= 0 || durationMinutes > 480) return this.setData({ error: "时长必须为 1 至 480 分钟的整数" })
    if (!await confirmAction("确认批量生成", `${coach.name} · ${this.data.weekStart} 所在周 · ${this.data.weekStartTime} · ${durationMinutes} 分钟`)) return
    this.setData({ pendingId: "generate-week", error: "", batchFeedback: "", batchConflicts: [] })
    try {
      const result = await guard.run("generate-week", () => adminService.generatePrivateWeek({ coachProfileId: coach.id, weekStart: `${this.data.weekStart}T00:00:00+08:00`, weekdays: this.data.selectedWeekdays, startTime: this.data.weekStartTime, durationMinutes }))
      if (!result) return
      this.setData({ batchFeedback: `成功生成 ${result.created.length} 个时段${result.conflicts.length ? `，跳过 ${result.conflicts.length} 个冲突` : "，无冲突"}`, batchConflicts: result.conflicts.map(item => `${item.startAt}：${schedulingConflictLabel(item.reason)}`) })
      await this.load()
    } catch { this.setData({ error: "批量生成失败，请检查时间范围和已有时段" }) }
    finally { this.setData({ pendingId: "" }) }
  },
  async decide(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const action = String(e.currentTarget.dataset.action) as "confirm" | "reject" | "cancel"; let reason: string | undefined; if (action !== "confirm") { const value = await promptAction(action === "reject" ? "拒绝原因" : "取消原因", "请填写说明"); if (value === null) return; reason = value } if (!await confirmAction("确认私教预约操作", action === "confirm" ? "确认接受该预约？" : "该操作将终止当前预约。")) return; await this.run(`${action}:${id}`, () => adminService.decidePrivate(id, action, reason)) },
  async signIn(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const content = await promptAction("课时记录", "请填写本次训练内容"); if (!content) return; const hours = await promptAction("核销课时", "例如 1 或 1.5"); if (!hours || Number(hours) <= 0) return this.setData({ error: "核销课时必须大于 0" }); if (!await confirmAction("确认签到并核销", `本次核销 ${hours} 小时，提交后将完成预约。`)) return; await this.run(`sign:${id}`, () => adminService.signInPrivate(id, content, hours)) },
  async run(id: string, task: () => Promise<unknown>) { if (this.data.pendingId) return; this.setData({ pendingId: id, error: "" }); try { await guard.run(id, task); wx.showToast({ title: "操作成功", icon: "success" }); await this.load() } catch { this.setData({ error: "操作失败，请检查时段、预约或会员卡状态" }) } finally { this.setData({ pendingId: "" }) } },
})
