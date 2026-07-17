<script setup lang="ts">
import type { TimelineEvent } from "~/types/domain"
import { orderWriteoffChain, timelineActionLabels, writeoffChainStatus } from "~/utils/timeline"

const props = defineProps<{ open: boolean; memberId: string; businessRef: string | null }>()
const emit = defineEmits<{ close: [] }>()
const api = useGymApi()
const items = ref<TimelineEvent[]>([])
const pending = ref(false)
const errorMessage = ref("")

async function loadChain() {
  if (!props.open || !props.businessRef) return
  pending.value = true
  errorMessage.value = ""
  try {
    const response = await api.getMemberTimeline(props.memberId, { category: "writeoff", businessRef: props.businessRef, limit: 100 })
    items.value = orderWriteoffChain(response.items)
  } catch {
    errorMessage.value = "核销链路加载失败"
  } finally {
    pending.value = false
  }
}
watch(() => [props.open, props.businessRef], loadChain, { immediate: true })
</script>

<template>
  <div v-if="open" class="drawer-backdrop" @click.self="emit('close')">
    <aside class="chain-drawer" aria-label="核销链路详情">
      <div class="section-heading">
        <div><h2>核销链路</h2><p class="hint">{{ businessRef }}</p></div>
        <button class="button-secondary" type="button" @click="emit('close')">关闭</button>
      </div>
      <p v-if="pending" class="hint">正在加载链路…</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <template v-else>
        <p class="status-badge">{{ writeoffChainStatus(items) }}</p>
        <ol class="chain-list">
          <li v-for="event in items" :key="event.id">
            <strong>{{ event.sequenceNo }}. {{ timelineActionLabels[event.action] || event.action }}</strong>
            <span>{{ new Date(event.occurredAt).toLocaleString("zh-CN") }}</span>
            <span>次数变化：{{ event.timesDelta ?? 0 }}</span>
            <span v-if="event.memberCardId">会员卡：{{ event.memberCardId }}</span>
          </li>
        </ol>
        <p v-if="!items.length" class="empty-state">未找到该业务单的核销事件。</p>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.drawer-backdrop { position: fixed; inset: 0; z-index: 20; display: flex; justify-content: flex-end; background: rgb(0 0 0 / 35%); }
.chain-drawer { width: min(520px, 100%); height: 100%; padding: 24px; overflow: auto; background: var(--panel); box-shadow: -8px 0 28px rgb(0 0 0 / 14%); }
.chain-list { display: grid; gap: 14px; padding-left: 22px; }
.chain-list li { display: grid; gap: 5px; padding: 14px; border: 1px solid var(--border); border-radius: 12px; }
.chain-list span { color: var(--muted); font-size: 13px; overflow-wrap: anywhere; }
</style>
