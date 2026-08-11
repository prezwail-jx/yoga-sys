import { ApiError, coachService, navigationService, storageService } from "../../../services"
import type { CoachScheduleGroups } from "../../../types/coach"
import { dateKey, mondayOf, shiftWeek } from "../../../utils/member-presenter"

Page({
  data: {
    weekStart: "",
    groups: [] as CoachScheduleGroups,
    mode: "loading",
    message: "正在加载我的团课",
  },
  onLoad() {
    if (storageService.user()?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    this.setData({ weekStart: dateKey(mondayOf(new Date())) })
    void this.load()
  },
  async load() {
    this.setData({ mode: "loading", message: "正在加载我的团课" })
    try {
      const groups = await coachService.schedule(this.data.weekStart)
      this.setData({ groups, mode: groups.length ? "ready" : "empty", message: groups.length ? "" : "本周没有分配给你的团课" })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "团课加载失败" })
    }
  },
  previousWeek() {
    this.setData({ weekStart: shiftWeek(this.data.weekStart, -1) })
    void this.load()
  },
  nextWeek() {
    this.setData({ weekStart: shiftWeek(this.data.weekStart, 1) })
    void this.load()
  },
  roster(event: WechatMiniprogram.CustomEvent) {
    navigationService.open(`/pages/coach/roster/index?sessionId=${encodeURIComponent(event.currentTarget.dataset.id as string)}`)
  },
})
