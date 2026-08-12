<script setup lang="ts">
import type { TimelineCategory, TimelineEvent } from "~/types/domain"
import { timelineActionLabels } from "~/utils/timeline"
import { label, cardTypeLabels, timelineResultLabels, timelineSourceLabels, userRoleLabels } from "~/utils/labels"

definePageMeta({ middleware: "require-timeline-access" })
const route = useRoute()
const api = useGymApi()
const memberId = String(route.params.memberId)
const category = ref<TimelineCategory>("all")
const action = ref("")
const dateFrom = ref("")
const dateTo = ref("")
const skip = ref(0)
const limit = 50
const selectedBusinessRef = ref<string | null>(null)

const { data, refresh, status, error } = await useAsyncData(
  `member-timeline-${memberId}`,
  () => api.getMemberTimeline(memberId, {
    category: category.value, action: action.value || undefined,
    dateFrom: dateFrom.value || undefined, dateTo: dateTo.value || undefined,
    skip: skip.value, limit,
  }),
  { watch: [skip] },
)

async function applyFilters() {
  skip.value = 0
  await refresh()
}
function openChain(event: TimelineEvent) {
  if (event.businessRef) selectedBusinessRef.value = event.businessRef
}
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div><h2>会员业务时间线</h2><p class="hint">会员 ID：{{ memberId }} · 共 {{ data?.total || 0 }} 条记录</p></div>
      <NuxtLink class="button-link" to="/members">返回会员列表</NuxtLink>
    </div>
    <div class="toolbar">
      <select v-model="category">
        <option value="all">全部类别</option><option value="transaction">卡项交易</option>
        <option value="writeoff">核销事件</option><option value="audit">操作审计</option>
      </select>
      <select v-model="action">
        <option value="">全部动作</option>
        <option v-for="(actionLabel, value) in timelineActionLabels" :key="value" :value="value">{{ actionLabel }}</option>
      </select>
      <input v-model="dateFrom" type="date" aria-label="开始日期" />
      <input v-model="dateTo" type="date" aria-label="结束日期" />
      <button type="button" @click="applyFilters">查询</button>
    </div>
    <CommonAsyncState :status="status" :empty="!data?.items.length" pending-text="正在加载时间线…" empty-text="当前筛选条件下暂无业务记录。" :error-message="error?.statusMessage || '时间线加载失败'" @retry="refresh">
    <div class="timeline-stream">
      <article v-for="event in data?.items || []" :key="`${event.source}:${event.id}`" class="timeline-card">
        <div>
          <strong>{{ timelineActionLabels[event.action] || event.summary }}</strong>
          <span class="status-badge">{{ label(timelineResultLabels, event.result) }}</span>
        </div>
        <p>{{ new Date(event.occurredAt).toLocaleString("zh-CN") }} · {{ label(timelineSourceLabels, event.source) }}</p>
        <p v-if="event.productName"><strong>{{ event.productName }}</strong><span v-if="event.cardType"> · {{ label(cardTypeLabels, event.cardType) }}</span></p>
        <p v-if="event.amount !== null">金额：¥{{ event.amount }}</p>
        <p v-if="event.timesDelta !== null">次数变化：{{ event.timesDelta > 0 ? "+" : "" }}{{ event.timesDelta }}</p>
        <p v-if="event.validDaysDelta !== null">有效期变化：{{ event.validDaysDelta > 0 ? "+" : "" }}{{ event.validDaysDelta }} 天</p>
        <p v-if="event.reason">备注：{{ event.reason }}</p>
        <p v-if="event.operatorRole">操作人：{{ event.operatorId }}（{{ label(userRoleLabels, event.operatorRole) }}）</p>
        <button v-if="event.businessRef" class="button-secondary" type="button" @click="openChain(event)">查看核销链路</button>
      </article>
    </div>
    </CommonAsyncState>
    <div class="pagination">
      <button class="button-secondary" type="button" :disabled="skip === 0" @click="skip = Math.max(0, skip - limit)">上一页</button>
      <span>第 {{ Math.floor(skip / limit) + 1 }} 页</span>
      <button class="button-secondary" type="button" :disabled="skip + limit >= (data?.total || 0)" @click="skip += limit">下一页</button>
    </div>
  </section>
  <TimelineWriteoffChainDrawer :open="Boolean(selectedBusinessRef)" :member-id="memberId" :business-ref="selectedBusinessRef" @close="selectedBusinessRef = null" />
</template>

<style scoped>
.timeline-stream { display: grid; gap: 12px; margin-top: 18px; }
.timeline-card { padding: 16px; border: 1px solid var(--border); border-radius: 12px; background: #fff; }
.timeline-card > div { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.timeline-card p { margin: 8px 0; color: var(--muted); }
.button-link { padding: 9px 12px; color: #fff; text-decoration: none; background: var(--brand); border-radius: 10px; }
</style>
