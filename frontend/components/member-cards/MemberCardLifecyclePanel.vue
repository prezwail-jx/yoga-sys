<script setup lang="ts">
import type { MemberCard } from "~/types/domain"

defineProps<{ card: MemberCard; pending?: boolean }>()
const emit = defineEmits<{
  renew: [card: MemberCard]
  reissue: [card: MemberCard]
  refund: [card: MemberCard]
  extend: [payload: { card: MemberCard; days: number; reason: string }]
  freeze: [payload: { card: MemberCard; until: string; reason: string }]
  unfreeze: [payload: { card: MemberCard; reason: string }]
}>()
const extendDays = ref(7)
const extendReason = ref("")
const frozenUntil = ref("")
const freezeReason = ref("")
const statusLabels: Record<MemberCard["status"], string> = { pending_activation: "待首次约课开卡", active: "使用中", frozen: "冻结中", expired: "已过期", closed: "已关闭" }
</script>

<template>
  <article class="panel member-card-panel">
    <div class="section-heading">
      <div>
        <h3>{{ card.productName }}</h3>
        <p class="hint">{{ statusLabels[card.status] }} <span v-if="card.expiringSoon" class="status-badge">即将到期</span></p>
      </div>
      <span class="status-badge">{{ card.remainingTimes === null ? "不限次" : `剩余 ${card.remainingTimes} 次` }}</span>
    </div>
    <p>开卡：{{ card.openedOn || "首次约课时" }} · 到期：{{ card.expiresOn || "尚未计算" }} · 累计冻结：{{ card.totalFrozenDays }} 天</p>
    <p v-if="card.status === 'frozen'" class="hint">冻结至 {{ card.frozenUntil }}，原因：{{ card.freezeReason }}</p>
    <div v-if="card.status !== 'closed'" class="actions">
      <button type="button" :disabled="pending" @click="emit('renew', card)">续费</button>
      <button v-if="['pending_activation','active','frozen'].includes(card.status)" class="button-secondary" type="button" :disabled="pending" @click="emit('reissue', card)">补卡</button>
      <button v-if="card.refundableTransactionId" class="button-danger" type="button" :disabled="pending" @click="emit('refund', card)">整笔退款</button>
    </div>
    <div v-if="['pending_activation','active','frozen'].includes(card.status)" class="toolbar">
      <input v-model.number="extendDays" type="number" min="1" placeholder="延期天数" />
      <input v-model="extendReason" placeholder="延期原因" />
      <button class="button-secondary" type="button" :disabled="pending" @click="emit('extend', { card, days: extendDays, reason: extendReason })">延期</button>
    </div>
    <div v-if="card.status === 'active'" class="toolbar">
      <input v-model="frozenUntil" type="date" />
      <input v-model="freezeReason" placeholder="冻结原因" />
      <button class="button-secondary" type="button" :disabled="pending || !frozenUntil || !freezeReason" @click="emit('freeze', { card, until: frozenUntil, reason: freezeReason })">冻结</button>
    </div>
    <div v-if="card.status === 'frozen'" class="toolbar">
      <input v-model="freezeReason" placeholder="提前解冻原因（可选）" />
      <button class="button-secondary" type="button" :disabled="pending" @click="emit('unfreeze', { card, reason: freezeReason })">提前解冻</button>
    </div>
  </article>
</template>
