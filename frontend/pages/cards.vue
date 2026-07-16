<script setup lang="ts">
import type { CardProduct, CardProductInput, CardType, CourseScope } from "~/types/domain"
import { parseSpecificCourseIds } from "~/utils/cardProduct"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-admin" })

const api = useGymApi()
const showForm = ref(false)
const editingId = ref<string | null>(null)
const pending = ref(false)
const errorMessage = ref("")
const specificCourseText = ref("")

const newForm = (): CardProductInput => ({
  name: "",
  cardType: "times",
  price: 0,
  costPrice: null,
  totalTimes: 10,
  validDays: null,
  activationMode: "immediate",
  applicableCourseScope: "group",
  specificCourseIds: null,
  absenceDeductEnabled: true,
  cancelRefundEnabled: true,
})
const form = reactive<CardProductInput>(newForm())
const { data, refresh, status, error } = await useAsyncData("real-card-products", () => api.getCards())

function openCreate() {
  editingId.value = null
  specificCourseText.value = ""
  Object.assign(form, newForm())
  showForm.value = true
}

function openEdit(card: CardProduct) {
  editingId.value = card.id
  specificCourseText.value = card.specificCourseIds?.join(", ") || ""
  Object.assign(form, {
    name: card.name,
    cardType: card.cardType,
    price: Number(card.price),
    costPrice: card.costPrice === null ? null : Number(card.costPrice),
    totalTimes: card.totalTimes,
    validDays: card.validDays,
    activationMode: card.activationMode,
    applicableCourseScope: card.applicableCourseScope,
    specificCourseIds: card.specificCourseIds,
    absenceDeductEnabled: card.absenceDeductEnabled,
    cancelRefundEnabled: card.cancelRefundEnabled,
  })
  showForm.value = true
}

function normalizeByType() {
  if (form.cardType === "duration") form.totalTimes = null
  if (form.cardType === "times" || form.cardType === "private") form.validDays ||= null
}

async function saveCard() {
  pending.value = true
  errorMessage.value = ""
  normalizeByType()
  form.specificCourseIds = form.applicableCourseScope === "specific"
    ? parseSpecificCourseIds(specificCourseText.value)
    : null
  try {
    if (editingId.value) await api.updateCard(editingId.value, form)
    else await api.createCard(form)
    showForm.value = false
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "保存失败")
  } finally {
    pending.value = false
  }
}

async function toggleCard(card: CardProduct) {
  await api.updateCard(card.id, { enabled: !card.enabled })
  await refresh()
}

const typeLabels: Record<CardType, string> = {
  duration: "期限卡", times: "次数卡", private: "私教卡", trial: "体验卡",
}
const scopeLabels: Record<CourseScope, string> = {
  group: "团课", private: "私教", specific: "指定课程",
}
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div>
        <h2>卡项管理</h2>
        <p class="hint">真实数据 · 共 {{ data?.total || 0 }} 个卡项模板</p>
      </div>
      <button type="button" @click="openCreate">新建卡项</button>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <p v-if="error" class="error-message">加载失败：{{ error.statusMessage }}</p>
    <p v-else-if="status === 'pending'" class="hint">正在加载卡项…</p>
    <div v-else class="table-wrap">
      <table>
        <thead><tr><th>名称</th><th>类型</th><th>售价</th><th>次数/有效期</th><th>开卡方式</th><th>适用范围</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="card in data?.items || []" :key="card.id">
            <td>{{ card.name }}</td>
            <td>{{ typeLabels[card.cardType] }}</td>
            <td>¥{{ card.price }}</td>
            <td>{{ card.totalTimes ? card.totalTimes + " 次" : "" }} {{ card.validDays ? card.validDays + " 天" : "" }}</td>
            <td>{{ card.activationMode === "immediate" ? "购卡即开" : "首次约课" }}</td>
            <td>{{ scopeLabels[card.applicableCourseScope] }}</td>
            <td><span class="status-badge">{{ card.enabled ? "启用" : "停用" }}</span></td>
            <td class="actions">
              <button class="button-secondary" type="button" @click="openEdit(card)">编辑</button>
              <button :class="card.enabled ? 'button-danger' : 'button-secondary'" type="button" @click="toggleCard(card)">
                {{ card.enabled ? "停用" : "启用" }}
              </button>
            </td>
          </tr>
          <tr v-if="!data?.items.length"><td colspan="8" class="empty-state">暂无卡项模板</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section v-if="showForm" class="panel">
    <div class="section-heading">
      <h2>{{ editingId ? "编辑卡项" : "新建卡项" }}</h2>
      <button class="button-secondary" type="button" @click="showForm = false">关闭</button>
    </div>
    <form class="form-grid" @submit.prevent="saveCard">
      <label>卡项名称<input v-model="form.name" required maxlength="100" /></label>
      <label>卡项类型
        <select v-model="form.cardType" @change="normalizeByType">
          <option value="duration">期限卡</option><option value="times">次数卡</option>
          <option value="private">私教卡</option><option value="trial">体验卡</option>
        </select>
      </label>
      <label>售价<input v-model.number="form.price" type="number" min="0" step="0.01" required /></label>
      <label>成本价<input v-model.number="form.costPrice" type="number" min="0" step="0.01" /></label>
      <label v-if="form.cardType !== 'duration'">总次数<input v-model.number="form.totalTimes" type="number" min="1" required /></label>
      <label v-if="form.cardType === 'duration' || form.cardType === 'trial'">有效期（天）<input v-model.number="form.validDays" type="number" min="1" required /></label>
      <label>开卡方式
        <select v-model="form.activationMode"><option value="immediate">购卡即开</option><option value="first_booking">首次约课</option></select>
      </label>
      <label>适用课程
        <select v-model="form.applicableCourseScope"><option value="group">团课</option><option value="private">私教</option><option value="specific">指定课程</option></select>
      </label>
      <label v-if="form.applicableCourseScope === 'specific'" class="full-width">课程 ID（逗号分隔）
        <input v-model="specificCourseText" required placeholder="course-001, course-002" />
      </label>
      <label class="checkbox-label"><input v-model="form.absenceDeductEnabled" type="checkbox" /> 缺勤扣次</label>
      <label class="checkbox-label"><input v-model="form.cancelRefundEnabled" type="checkbox" /> 取消返还</label>
      <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存" }}</button></div>
    </form>
  </section>
</template>
