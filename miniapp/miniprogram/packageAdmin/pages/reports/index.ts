import { ActionGuard, ApiError, adminService, navigationService, storageService } from "../../../services/index"
import type { ReportDetailCategory, ReportTrendCategory } from "../../../types/admin"
import { localizedValue, reportMetrics } from "../../../utils/admin-presenter"

const trendValues: ReportTrendCategory[] = ["revenue", "bookings", "attendance", "private"]
const detailValues: ReportDetailCategory[] = ["transactions", "refunds", "expiring_members", "attendance", "private"]
const guard = new ActionGuard()
Page({
  data: { dateFrom: "", dateTo: "", trendIndex: 0, detailIndex: 0, trendNames: ["收入", "预约", "出勤", "私教"], detailNames: ["交易", "退款", "即将到期会员", "团课出勤", "私教"], metrics: [] as Array<{ label: string; value: string }>, points: [] as Array<{ bucket: string; value: string | number }>, rows: [] as string[], mode: "loading", message: "正在加载报表", error: "", exporting: false, exportFeedback: "" },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  dateFrom(e: WechatMiniprogram.PickerChange) { this.setData({ dateFrom: String(e.detail.value) }); void this.load() },
  dateTo(e: WechatMiniprogram.PickerChange) { this.setData({ dateTo: String(e.detail.value) }); void this.load() },
  trend(e: WechatMiniprogram.PickerChange) { this.setData({ trendIndex: Number(e.detail.value) }); void this.load() },
  detail(e: WechatMiniprogram.PickerChange) { this.setData({ detailIndex: Number(e.detail.value) }); void this.load() },
  async load() { this.setData({ mode: "loading", error: "" }); try { const [summary, trend, detail] = await Promise.all([adminService.reportSummary(this.data.dateFrom, this.data.dateTo), adminService.reportTrend(trendValues[this.data.trendIndex], this.data.dateFrom, this.data.dateTo), adminService.reportDetail(detailValues[this.data.detailIndex], this.data.dateFrom, this.data.dateTo)]); const rows = detail.items.map(item => Object.values(item).filter(value => value !== null && value !== undefined && typeof value !== "object").map(localizedValue).join(" · ")); this.setData({ metrics: reportMetrics(summary), points: trend.points, rows, mode: "ready", message: "" }) } catch { this.setData({ mode: "error", message: "报表加载失败" }) } },
  async exportReport() {
    if (this.data.exporting) return
    this.setData({ exporting: true, exportFeedback: "正在下载并打开 Excel 报表", error: "" })
    try {
      await guard.run("report-export", () => adminService.exportReport(detailValues[this.data.detailIndex], this.data.dateFrom, this.data.dateTo))
      this.setData({ exportFeedback: "报表已使用临时文件打开，关闭预览后文件由微信自动清理。" })
    } catch (error) {
      this.setData({ exportFeedback: "", error: error instanceof ApiError ? error.message : "报表导出失败，请稍后重试" })
    } finally {
      this.setData({ exporting: false })
    }
  },
})
