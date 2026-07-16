<script setup lang="ts">
const api = useGymApi()
const { data: summary } = await useAsyncData("reports-page-summary", () => api.getReportSummary())

const rows = computed(() => {
  if (!summary.value) {
    return []
  }

  return [
    { label: "总会员数", value: summary.value.totalMembers },
    { label: "活跃会员", value: summary.value.activeMembers },
    { label: "即将到期会员", value: summary.value.expiringSoonMembers },
    { label: "售卡收入", value: `¥${summary.value.cardSales}` },
    { label: "续费收入", value: `¥${summary.value.renewalSales}` },
    { label: "退款金额", value: `¥${summary.value.refundAmount}` },
    { label: "团课出勤率", value: `${Math.round(summary.value.attendanceRate * 100)}%` },
    { label: "满课率", value: `${Math.round(summary.value.fullClassRate * 100)}%` },
  ]
})
</script>

<template>
  <section class="panel">
    <h2>统计报表</h2>
    <div class="report-grid">
      <article v-for="item in rows" :key="item.label" class="report-item">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
      </article>
    </div>
    <p class="hint">当前为 mock 数据，后续可替换为后端真实聚合接口并接入导出能力。</p>
  </section>
</template>
