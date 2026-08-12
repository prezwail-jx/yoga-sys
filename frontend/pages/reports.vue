<script setup lang="ts">
import type { ReportDetailCategory, ReportTrendCategory } from "~/types/domain"
import { formatReportSummaryRows } from "~/utils/reports"
import { reportClassBookingStatusLabels, reportHeaderLabel, reportTransactionTypeLabels } from "~/utils/labels"

definePageMeta({ middleware: "require-admin" })

const api = useGymApi()
const filters = reactive({ dateFrom: "", dateTo: "", coachId: "", courseId: "", cardProductId: "" })
const activeDetail = ref<ReportDetailCategory>("transactions")
const activeTrend = ref<ReportTrendCategory>("revenue")
const pendingExport = ref(false)
const errorMessage = ref("")

const query = computed(() => ({
  dateFrom: filters.dateFrom || undefined,
  dateTo: filters.dateTo || undefined,
  coachId: filters.coachId || undefined,
  courseId: filters.courseId || undefined,
  cardProductId: filters.cardProductId || undefined,
}))

const { data: summary, status, error, refresh } = await useAsyncData("reports-real-summary", () => api.getReportSummary(query.value), { watch: [query] })
const { data: trend, refresh: refreshTrend } = await useAsyncData("reports-real-trend", () => api.getReportTrend(activeTrend.value, query.value), { watch: [query, activeTrend] })
const { data: detail, refresh: refreshDetail } = await useAsyncData("reports-real-detail", () => api.getReportDetail(activeDetail.value, { ...query.value, limit: 20 }), { watch: [query, activeDetail] })
const [{ data: coaches }, { data: courses }, { data: cards }] = await Promise.all([
  useAsyncData("report-coaches", () => api.getCoaches({ enabled: true, limit: 100 })),
  useAsyncData("report-courses", () => api.getCourses({ enabled: true, limit: 100 })),
  useAsyncData("report-cards", () => api.getCards({ enabled: true, limit: 100 })),
])

const rows = computed(() => formatReportSummaryRows(summary.value))

function formatCell(key: string, value: unknown): unknown {
  if (value == null) return value
  if (key === "type" && typeof value === "string") return reportTransactionTypeLabels[value] || value
  if (key === "status" && typeof value === "string") return reportClassBookingStatusLabels[value] || value
  return value
}

const trendMax = computed(() => Math.max(...(trend.value?.points || []).map(item => Number(item.value) || 0), 1))

async function reloadAll() {
  await Promise.all([refresh(), refreshTrend(), refreshDetail()])
}

async function exportCurrent() {
  pendingExport.value = true
  errorMessage.value = ""
  try {
    await api.exportReport(activeDetail.value, query.value)
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "导出失败")
  } finally {
    pendingExport.value = false
  }
}
</script>

<template>
  <section class="panel">
    <div class="section-heading"><div><h2>经营数据概览</h2><p class="hint">真实经营指标、趋势、下钻与 Excel 导出</p></div><button class="button-secondary" type="button" @click="reloadAll">刷新</button></div>
    <form class="form-grid" @submit.prevent="reloadAll">
      <label>开始日期<input v-model="filters.dateFrom" type="date" /></label>
      <label>结束日期<input v-model="filters.dateTo" type="date" /></label>
      <label>教练<select v-model="filters.coachId"><option value="">全部</option><option v-for="coach in coaches?.items || []" :key="coach.id" :value="coach.id">{{ coach.name }}</option></select></label>
      <label>课程<select v-model="filters.courseId"><option value="">全部</option><option v-for="course in courses?.items || []" :key="course.id" :value="course.id">{{ course.name }}</option></select></label>
      <label>卡项<select v-model="filters.cardProductId"><option value="">全部</option><option v-for="card in cards?.items || []" :key="card.id" :value="card.id">{{ card.name }}</option></select></label>
    </form>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
  </section>

  <section class="panel">
    <CommonAsyncState :status="status" :empty="!rows.length" pending-text="加载报表…" empty-text="暂无报表数据" :error-message="getApiErrorMessage(error, '报表加载失败')" @retry="refresh">
      <div class="report-grid"><article v-for="item in rows" :key="item.label" class="report-item"><p>{{ item.label }}</p><strong>{{ item.value }}</strong></article></div>
    </CommonAsyncState>
  </section>

  <section class="panel">
    <div class="section-heading"><div><h3>趋势</h3><p class="hint">{{ activeTrend }}</p></div><select v-model="activeTrend"><option value="revenue">收入</option><option value="bookings">预约</option><option value="attendance">出勤</option><option value="private">私教</option></select></div>
    <div class="trend-bars"><div v-for="point in trend?.points || []" :key="point.bucket" class="trend-bar"><span :style="{ height: `${Math.max(8, (Number(point.value) || 0) / trendMax * 120)}px` }" /><small>{{ point.bucket }}</small></div></div>
  </section>

  <section class="panel">
    <div class="section-heading"><div><h3>明细下钻</h3><p class="hint">{{ detail?.total || 0 }} 条</p></div><div class="actions"><select v-model="activeDetail"><option value="transactions">交易</option><option value="refunds">退款</option><option value="expiring_members">即将到期</option><option value="attendance">团课出勤</option><option value="private">私教</option></select><button type="button" :disabled="pendingExport" @click="exportCurrent">{{ pendingExport ? "导出中…" : "导出 Excel" }}</button></div></div>
    <div class="table-wrap"><table><thead><tr><th v-for="key in Object.keys(detail?.items?.[0] || {})" :key="key">{{ reportHeaderLabel(key) }}</th></tr></thead><tbody><tr v-for="(item, idx) in detail?.items || []" :key="idx"><td v-for="key in Object.keys(item)" :key="key">{{ formatCell(key, item[key]) }}</td></tr></tbody></table></div>
    <p v-if="!(detail?.items || []).length" class="empty-state">暂无明细</p>
  </section>
</template>

<style scoped>
.trend-bars { display: flex; align-items: end; gap: 0.75rem; min-height: 160px; overflow-x: auto; padding: 1rem 0; }
.trend-bar { display: grid; gap: 0.5rem; justify-items: center; min-width: 56px; }
.trend-bar span { display: block; width: 28px; border-radius: 6px 6px 0 0; background: linear-gradient(180deg, #6a7b3f, #d9e6c3); }
.trend-bar small { color: #6b756f; font-size: 0.75rem; white-space: nowrap; }
</style>
