import { ActionGuard, adminService, navigationService, storageService } from "../../../services/index"
import type { ClassBooking, ClassSession, Coach, Course, Room } from "../../../types/admin"
import { classBookingStatusLabels, classSessionStatusLabels, schedulingConflictLabel } from "../../../utils/admin-presenter"
import { dateKey, mondayOf, shiftWeek, timeLabel } from "../../../utils/member-presenter"
import { confirmAction, promptAction } from "../../../utils/modal"

type SessionView = ClassSession & { statusLabel: string; timeLabel: string }
type BookingView = ClassBooking & { statusLabel: string }
const guard = new ActionGuard()
const currentWeek = dateKey(mondayOf(new Date()))
Page({
  data: { weekStart: currentWeek, copySourceWeek: currentWeek, copyTargetWeek: shiftWeek(currentWeek, 1), copyFeedback: "", copyConflicts: [] as string[], sessions: [] as SessionView[], roster: [] as BookingView[], courses: [] as Course[], coaches: [] as Coach[], rooms: [] as Room[], courseNames: [] as string[], coachNames: [] as string[], roomNames: [] as string[], courseIndex: 0, coachIndex: 0, roomIndex: 0, selectedId: "", mode: "loading", message: "正在加载团课", pendingId: "", error: "" },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  week(e: WechatMiniprogram.PickerChange) { this.setData({ weekStart: dateKey(mondayOf(new Date(`${String(e.detail.value)}T00:00:00+08:00`))) }); void this.load() },
  copyWeekDate(e: WechatMiniprogram.PickerChange) { const value = dateKey(mondayOf(new Date(`${String(e.detail.value)}T00:00:00+08:00`))); this.setData({ [String(e.currentTarget.dataset.field)]: value, copyFeedback: "", copyConflicts: [] }) },
  async load() { try { const [result, courses, coaches, rooms] = await Promise.all([adminService.sessions(this.data.weekStart), adminService.courses(), adminService.coaches(), adminService.rooms()]); this.setData({ sessions: result.items.map(item => ({ ...item, statusLabel: classSessionStatusLabels[item.status], timeLabel: timeLabel(item.startAt, item.endAt) })), courses: courses.items.filter(item => item.enabled), coaches: coaches.items.filter(item => item.enabled), rooms: rooms.items.filter(item => item.enabled), courseNames: courses.items.filter(item => item.enabled).map(item => item.name), coachNames: coaches.items.filter(item => item.enabled).map(item => item.name), roomNames: rooms.items.filter(item => item.enabled).map(item => item.name), mode: result.items.length ? "ready" : "empty", message: result.items.length ? "" : "本周暂无团课", roster: [], selectedId: "" }) } catch { this.setData({ mode: "error", message: "团课加载失败" }) } },
  chooseCatalog(e: WechatMiniprogram.PickerChange) { this.setData({ [String(e.currentTarget.dataset.field)]: Number(e.detail.value) }) },
  async createSession() { const course = this.data.courses[this.data.courseIndex]; const coach = this.data.coaches[this.data.coachIndex]; const room = this.data.rooms[this.data.roomIndex]; if (!course || !coach || !room) return this.setData({ error: "请先启用课程、教练和教室资料" }); const startAt = await promptAction("开课时间", "如 2026-08-28T09:00:00+08:00"); if (!startAt) return; const endAt = await promptAction("结束时间", "必须晚于开课时间"); if (!endAt) return; const capacity = Number(await promptAction("课次容量", `教室容量 ${room.capacity} 人`)); if (!Number.isInteger(capacity) || capacity <= 0 || capacity > room.capacity) return this.setData({ error: `课次容量应为 1 至 ${room.capacity} 的整数` }); if (!await confirmAction("确认新建排课", `${course.name} · ${coach.name} · ${room.name}\n${startAt}`)) return; await this.run("create-session", () => adminService.createSession({ courseId: course.id, coachProfileId: coach.id, roomId: room.id, startAt, endAt, capacity })); await this.load() },
  async copyWeek() {
    if (this.data.pendingId) return
    const { copySourceWeek, copyTargetWeek } = this.data
    if (copySourceWeek === copyTargetWeek) return this.setData({ error: "来源周和目标周不能相同" })
    if (!await confirmAction("确认复制整周课表", `从 ${copySourceWeek} 复制到 ${copyTargetWeek}？已有冲突课次不会重复创建。`)) return
    this.setData({ pendingId: "copy-week", error: "", copyFeedback: "", copyConflicts: [] })
    try {
      const result = await guard.run("copy-week", () => adminService.copySessionWeek(copySourceWeek, copyTargetWeek))
      if (!result) return
      this.setData({ copyFeedback: `成功创建 ${result.created.length} 个课次${result.conflicts.length ? `，跳过 ${result.conflicts.length} 个冲突` : "，无冲突"}`, copyConflicts: result.conflicts.map(item => `${item.targetStartAt}：${schedulingConflictLabel(item.reason)}`), weekStart: copyTargetWeek })
      await this.load()
    } catch { this.setData({ error: "整周课表复制失败，请检查来源周和目标周" }) }
    finally { this.setData({ pendingId: "" }) }
  },
  async roster(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); try { const result = await adminService.roster(id); this.setData({ selectedId: id, roster: result.items.map(item => ({ ...item, statusLabel: classBookingStatusLabels[item.status] })) }) } catch { this.setData({ error: "预约名单加载失败" }) } },
  async transition(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const action = String(e.currentTarget.dataset.action) as "publish" | "pause" | "resume" | "cancel" | "complete"; if ((action === "cancel" || action === "complete") && !await confirmAction(action === "cancel" ? "确认取消课次" : "确认完成课次", "该操作会影响预约和卡项权益，请再次确认。")) return; await this.run(`session:${action}:${id}`, () => adminService.transitionSession(id, action)); await this.load() },
  async adminBook() { if (!this.data.selectedId) return; const memberId = await promptAction("会员代约", "请输入会员 ID"); if (!memberId) return; if (!await confirmAction("确认代约", `为会员 ${memberId} 预约当前课次？`)) return; await this.run(`book:${memberId}`, () => adminService.adminBook(this.data.selectedId, memberId)); await this.refreshRoster() },
  async bookingAction(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const action = String(e.currentTarget.dataset.action); if (!await confirmAction(action === "check" ? "确认签到" : "确认取消预约", "请确认会员和课次信息无误。")) return; if (action === "check") await this.run(`check:${id}`, () => adminService.checkIn(id)); else { const reason = await promptAction("取消原因", "可选"); if (reason === null) return; await this.run(`cancel:${id}`, () => adminService.cancelBooking(id, reason)) } await this.refreshRoster() },
  async refreshRoster() { if (!this.data.selectedId) return; const result = await adminService.roster(this.data.selectedId); this.setData({ roster: result.items.map(item => ({ ...item, statusLabel: classBookingStatusLabels[item.status] })) }) },
  async run(id: string, task: () => Promise<unknown>) { this.setData({ pendingId: id, error: "" }); try { await guard.run(id, task); wx.showToast({ title: "操作成功", icon: "success" }) } catch { this.setData({ error: "操作失败，请检查课次当前状态" }) } finally { this.setData({ pendingId: "" }) } },
})
