import { adminService, navigationService, storageService } from "../../../services/index"
import { reportMetrics } from "../../../utils/admin-presenter"

Page({
  data: { mode: "loading", message: "正在加载运营数据", metrics: [] as ReturnType<typeof reportMetrics> },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  async load() {
    this.setData({ mode: "loading", message: "正在加载运营数据" })
    try { const metrics = reportMetrics(await adminService.reportSummary()); this.setData({ metrics, mode: "ready", message: "" }) }
    catch { this.setData({ mode: "error", message: "运营数据加载失败，请稍后重试" }) }
  },
})
