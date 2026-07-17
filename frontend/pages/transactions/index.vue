<script setup lang="ts">
import type { MemberCard, TransactionInput } from "~/types/domain"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-admin" })
const route = useRoute()
const api = useGymApi()
const { pending, submit, reset } = useIdempotentSubmit()
const selectedMemberId = ref(typeof route.query.memberId === "string" ? route.query.memberId : "")
const selectedProductId = ref("")
const message = ref("")
const errorMessage = ref("")

const { data: members, status: membersStatus, error: membersError, refresh: refreshMembers } = await useAsyncData("transaction-members", () => api.getMembers({ limit: 100 }))
const { data: products, status: productsStatus, error: productsError, refresh: refreshProducts } = await useAsyncData("transaction-products", () => api.getCards({ enabled: true, limit: 100 }))
const { data: cards, refresh: refreshCards, status: cardsStatus, error: cardsError } = await useAsyncData(
  "transaction-member-cards",
  () => selectedMemberId.value ? api.getMemberCards(selectedMemberId.value) : Promise.resolve({ items: [], total: 0 }),
  { watch: [selectedMemberId] },
)

const setupStatus = computed<"idle" | "pending" | "success" | "error">(() => {
  if (membersStatus.value === "error" || productsStatus.value === "error") return "error"
  if (membersStatus.value === "pending" || productsStatus.value === "pending") return "pending"
  return "success"
})
const setupError = computed(() => membersError.value?.statusMessage || productsError.value?.statusMessage || "办理数据加载失败")
async function retrySetup() { await Promise.all([refreshMembers(), refreshProducts()]) }

watch(selectedMemberId, async (memberId) => {
  await navigateTo({ path: "/transactions", query: memberId ? { memberId } : {} }, { replace: true })
})

async function run(payload: TransactionInput) {
  message.value = ""
  errorMessage.value = ""
  const signature = JSON.stringify(payload)
  try {
    const result = await submit(signature, key => api.createTransaction(payload, key))
    message.value = `操作成功，交易号：${result.transaction.id}`
    reset()
    await refreshCards()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "操作失败")
  }
}

async function purchase() {
  if (!selectedMemberId.value || !selectedProductId.value) return
  await run({ txnType: "purchase", memberId: selectedMemberId.value, cardProductId: selectedProductId.value })
}
async function renew(card: MemberCard) { await run({ txnType: "renew", memberId: card.memberId, memberCardId: card.id }) }
async function reissue(card: MemberCard) {
  if (confirm(`确认补发“${card.productName}”？原卡将关闭。`)) await run({ txnType: "reissue", memberId: card.memberId, memberCardId: card.id, reason: "后台补卡" })
}
async function refund(card: MemberCard) {
  if (card.refundableTransactionId && confirm(`确认整笔退款“${card.productName}”？`)) await run({ txnType: "refund", memberId: card.memberId, memberCardId: card.id, originTransactionId: card.refundableTransactionId, reason: "后台整笔退款" })
}
async function extend(payload: { card: MemberCard; days: number; reason: string }) {
  await run({ txnType: "extend", memberId: payload.card.memberId, memberCardId: payload.card.id, validDaysDelta: payload.days, reason: payload.reason })
}
async function freeze(payload: { card: MemberCard; until: string; reason: string }) {
  const body = { frozenUntil: payload.until, reason: payload.reason }
  try {
    await submit(`freeze:${payload.card.id}:${JSON.stringify(body)}`, key => api.freezeMemberCard(payload.card.id, body, key))
    message.value = "冻结成功"
    reset(); await refreshCards()
  } catch (error: unknown) { errorMessage.value = getApiErrorMessage(error, "冻结失败") }
}
async function unfreeze(payload: { card: MemberCard; reason: string }) {
  const body = { reason: payload.reason || undefined }
  try {
    await submit(`unfreeze:${payload.card.id}:${JSON.stringify(body)}`, key => api.unfreezeMemberCard(payload.card.id, body, key))
    message.value = "解冻成功"
    reset(); await refreshCards()
  } catch (error: unknown) { errorMessage.value = getApiErrorMessage(error, "解冻失败") }
}
</script>

<template>
  <section class="panel">
    <div class="section-heading"><div><h2>卡项办理</h2><p class="hint">选择会员后办理购卡、续费、补卡、退款和生命周期操作。</p></div></div>
    <CommonAsyncState :status="setupStatus" :empty="false" pending-text="正在加载会员和卡项…" :error-message="setupError" @retry="retrySetup">
    <div class="toolbar">
      <select v-model="selectedMemberId">
        <option value="">请选择会员</option>
        <option v-for="member in members?.items || []" :key="member.id" :value="member.id">{{ member.name }} · {{ member.phone }}</option>
      </select>
      <select v-model="selectedProductId" :disabled="!selectedMemberId">
        <option value="">选择购卡产品</option>
        <option v-for="product in products?.items || []" :key="product.id" :value="product.id">{{ product.name }} · ¥{{ product.price }}</option>
      </select>
      <button type="button" :disabled="pending || !selectedMemberId || !selectedProductId" @click="purchase">办理购卡</button>
    </div>
    </CommonAsyncState>
    <p v-if="message" class="success-message">{{ message }}</p>
    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
  </section>
  <CommonAsyncState v-if="selectedMemberId" :status="cardsStatus" :empty="!cards?.items.length" pending-text="正在加载会员卡…" empty-text="该会员暂无卡项，可在上方办理购卡。" :error-message="cardsError?.statusMessage || '会员卡加载失败'" @retry="refreshCards">
  <div>
    <MemberCardLifecyclePanel v-for="card in cards?.items || []" :key="card.id" :card="card" :pending="pending" @renew="renew" @reissue="reissue" @refund="refund" @extend="extend" @freeze="freeze" @unfreeze="unfreeze" />
  </div>
  </CommonAsyncState>
</template>
