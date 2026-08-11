import { ActionGuard, ApiError, memberService, navigationService, storageService } from "../../../services/index"
import type { DayGroup, ClassScheduleItem } from "../../../types/member"
import { dateKey, mondayOf, shiftWeek } from "../../../utils/member-presenter"
import { confirmAction } from "../../../utils/modal"

const actions = new ActionGuard()

Page({
  data: {
    weekStart: "",
    groups: [] as DayGroup<ClassScheduleItem>[],
    mode: "loading",
    message: "正在加载本周课程",
    pendingId: "",
    feedback: "",
  },
  onLoad() {
    if (storageService.user()?.role !== "member") {
      navigationService.routeForbidden()
      return
    }
    this.setData({ weekStart: dateKey(mondayOf(new Date())) })
    void this.load()
  },
  async load() {
    this.setData({ mode: "loading", message: "正在加载本周课程", feedback: "" })
    try {
      const groups = await memberService.schedule(this.data.weekStart)
      this.setData({
        groups,
        mode: groups.length ? "ready" : "empty",
        message: groups.length ? "" : "本周还没有可查看的课程",
      })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "课程加载失败" })
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
  async book(event: WechatMiniprogram.CustomEvent) {
    const sessionId = event.currentTarget.dataset.id as string
    const courseName = event.currentTarget.dataset.name as string
    if (actions.isPending(sessionId)) return
    if (!await confirmAction("确认预约", `预约 ${courseName}？资格、容量和时间冲突以服务端结果为准。`)) return
    this.setData({ pendingId: sessionId, feedback: "" })
    try {
      await actions.run(sessionId, () => memberService.bookClass(sessionId))
      await this.load()
    } catch (error) {
      this.setData({ feedback: error instanceof ApiError ? error.message : "预约失败，请稍后重试" })
    } finally {
      this.setData({ pendingId: "" })
    }
  },
})
