<script setup lang="ts">
import type { PrivateBooking, PrivateBookingDecisionInput, PrivateSlotInput } from "~/types/domain"
import { canCancelPendingPrivateBooking, canConfirmPrivateBooking, canRejectPrivateBooking, canSignInPrivateBooking } from "~/utils/privateTraining"
import { privateTrainingErrorMessage } from "~/utils/privateTrainingErrors"

definePageMeta({ middleware: "require-auth" })

const api = useGymApi()
const { user } = useAuth()

const today = new Date().toISOString().slice(0, 10)
const filters = reactive({ dateFrom: today, dateTo: "" })
const slotForm = reactive({ coachProfileId: "", startAt: "", endAt: "" })
const bookingMessage = ref("")
const decisionReason = ref("")
const lessonForm = reactive({ content: "", consumedHours: "1.0", memberStatusNotes: "" })
const selectedBooking = ref<PrivateBooking | null>(null)
const pending = ref(false)
const errorMessage = ref("")
const successMessage = ref("")

const isAdmin = computed(() => user.value?.role === "admin")
const isCoach = computed(() => user.value?.role === "coach")
const isMember = computed(() => user.value?.role === "member")
const currentRole = computed(() => user.value?.role)

const { data: slots, status: slotStatus, error: slotError, refresh: refreshSlots } = await useAsyncData("private-real-slots", () => api.getPrivateSlots(filters))
const { data: bookings, status: bookingStatus, error: bookingError, refresh: refreshBookings } = await useAsyncData("private-real-bookings", () => api.getPrivateBookings({ limit: 100 }))
const { data: coaches } = await useAsyncData("private-coaches", () => api.getCoaches({ enabled: true, limit: 100 }))

const slotItems = computed(() => slots.value?.items || [])
const bookingItems = computed(() => bookings.value?.items || [])

function localToIso(value: string) {
  return new Date(value).toISOString()
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false })
}

function key(prefix: string) {
  return `${prefix}:${crypto.randomUUID()}`
}

async function reloadAll() {
  await Promise.all([refreshSlots(), refreshBookings()])
}

async function createSlot() {
  pending.value = true
  errorMessage.value = ""
  try {
    const payload: PrivateSlotInput = {
      coachProfileId: isAdmin.value ? slotForm.coachProfileId || null : undefined,
      startAt: localToIso(slotForm.startAt),
      endAt: localToIso(slotForm.endAt),
    }
    await api.createPrivateSlot(payload)
    successMessage.value = "私教空闲时段已创建"
    slotForm.startAt = ""
    slotForm.endAt = ""
    await refreshSlots()
  } catch (error: unknown) {
    errorMessage.value = privateTrainingErrorMessage(error, "创建时段失败")
  } finally {
    pending.value = false
  }
}

async function bookSlot(slotId: string) {
  pending.value = true
  errorMessage.value = ""
  try {
    await api.createPrivateBooking({ availabilityId: slotId, memberMessage: bookingMessage.value || null }, key(`private-book:${slotId}`))
    successMessage.value = "已提交私教预约，等待教练确认"
    bookingMessage.value = ""
    await reloadAll()
  } catch (error: unknown) {
    errorMessage.value = privateTrainingErrorMessage(error, "预约失败")
  } finally {
    pending.value = false
  }
}

async function bookingAction(action: "confirm" | "reject" | "cancel") {
  if (!selectedBooking.value) return
  pending.value = true
  errorMessage.value = ""
  const payload: PrivateBookingDecisionInput = { reason: decisionReason.value || null }
  try {
    if (action === "confirm") await api.confirmPrivateBooking(selectedBooking.value.id, key(`private-confirm:${selectedBooking.value.id}`))
    if (action === "reject") await api.rejectPrivateBooking(selectedBooking.value.id, payload, key(`private-reject:${selectedBooking.value.id}`))
    if (action === "cancel") await api.cancelPrivateBooking(selectedBooking.value.id, payload, key(`private-cancel:${selectedBooking.value.id}`))
    successMessage.value = "预约状态已更新"
    selectedBooking.value = null
    decisionReason.value = ""
    await reloadAll()
  } catch (error: unknown) {
    errorMessage.value = privateTrainingErrorMessage(error, "操作失败")
    await reloadAll()
  } finally {
    pending.value = false
  }
}

async function signIn() {
  if (!selectedBooking.value) return
  pending.value = true
  errorMessage.value = ""
  try {
    await api.signInPrivateBooking(selectedBooking.value.id, {
      content: lessonForm.content,
      consumedHours: lessonForm.consumedHours,
      memberStatusNotes: lessonForm.memberStatusNotes || null,
    }, key(`private-sign-in:${selectedBooking.value.id}`))
    successMessage.value = "私教课已签到并记录"
    selectedBooking.value = null
    lessonForm.content = ""
    lessonForm.consumedHours = "1.0"
    lessonForm.memberStatusNotes = ""
    await refreshBookings()
  } catch (error: unknown) {
    errorMessage.value = privateTrainingErrorMessage(error, "签到失败")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div><h2>私教业务</h2><p class="hint">真实私教时段、预约确认与课时记录</p></div>
      <button class="button-secondary" type="button" @click="reloadAll">刷新</button>
    </div>
    <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-text">{{ successMessage }}</p>
  </section>

  <section v-if="isAdmin || isCoach" class="panel">
    <h3>发布空闲时段</h3>
    <form class="form-grid" @submit.prevent="createSlot">
      <label v-if="isAdmin">教练<select v-model="slotForm.coachProfileId" required><option value="">请选择</option><option v-for="coach in coaches?.items || []" :key="coach.id" :value="coach.id">{{ coach.name }}</option></select></label>
      <label>开始时间<input v-model="slotForm.startAt" type="datetime-local" required /></label>
      <label>结束时间<input v-model="slotForm.endAt" type="datetime-local" required /></label>
      <div class="full-width form-actions"><button type="submit" :disabled="pending">创建时段</button></div>
    </form>
  </section>

  <section class="panel">
    <div class="section-heading"><div><h3>空闲时段</h3><p class="hint">{{ slotItems.length }} 个时段</p></div></div>
    <CommonAsyncState :status="slotStatus" :empty="!slotItems.length" pending-text="加载私教时段…" empty-text="暂无可用时段" :error-message="getApiErrorMessage(slotError, '私教时段加载失败')" @retry="refreshSlots">
      <div class="catalog-grid">
        <article v-for="slot in slotItems" :key="slot.id" class="catalog-card">
          <div class="card-title"><strong>{{ slot.coachName }}</strong><span class="status-badge">{{ slot.status }}</span></div>
          <p>{{ formatDateTime(slot.startAt) }} - {{ formatDateTime(slot.endAt) }}</p>
          <p>{{ slot.durationMinutes }} 分钟</p>
          <textarea v-if="isMember && slot.status === 'available'" v-model="bookingMessage" placeholder="给教练留言（选填）" rows="2" />
          <div class="actions">
            <button v-if="isMember && slot.status === 'available'" type="button" :disabled="pending" @click="bookSlot(slot.id)">预约</button>
            <button v-if="(isAdmin || isCoach) && slot.status === 'available'" class="button-danger" type="button" :disabled="pending" @click="async () => { await api.deletePrivateSlot(slot.id); await refreshSlots() }">取消时段</button>
          </div>
        </article>
      </div>
    </CommonAsyncState>
  </section>

  <section class="panel">
    <div class="section-heading"><div><h3>预约记录</h3><p class="hint">{{ bookingItems.length }} 条</p></div></div>
    <CommonAsyncState :status="bookingStatus" :empty="!bookingItems.length" pending-text="加载预约…" empty-text="暂无预约记录" :error-message="getApiErrorMessage(bookingError, '预约加载失败')" @retry="refreshBookings">
      <div class="table-wrap"><table><thead><tr><th>会员</th><th>教练</th><th>时间</th><th>状态</th><th>操作</th></tr></thead><tbody>
        <tr v-for="booking in bookingItems" :key="booking.id">
          <td>{{ booking.memberName }}</td><td>{{ booking.coachName }}</td><td>{{ formatDateTime(booking.startAt) }}</td><td>{{ booking.status }}</td>
          <td><button class="button-secondary" type="button" @click="selectedBooking = booking">处理</button></td>
        </tr>
      </tbody></table></div>
    </CommonAsyncState>
  </section>

  <section v-if="selectedBooking" class="panel action-sheet">
    <div class="section-heading"><div><h3>{{ selectedBooking.memberName }} · {{ selectedBooking.status }}</h3><p class="hint">{{ formatDateTime(selectedBooking.startAt) }}</p></div><button class="button-secondary" type="button" @click="selectedBooking = null">关闭</button></div>
    <label v-if="selectedBooking.status === 'pending'" class="full-width">原因（拒绝/取消时选填）<textarea v-model="decisionReason" rows="2" /></label>
    <div v-if="selectedBooking.status === 'confirmed'" class="form-grid">
      <label class="full-width">上课内容<textarea v-model="lessonForm.content" rows="3" required /></label>
      <label>消耗课时<input v-model="lessonForm.consumedHours" type="number" step="0.5" min="0.5" /></label>
      <label class="full-width">会员状态<textarea v-model="lessonForm.memberStatusNotes" rows="2" /></label>
    </div>
    <div class="form-actions">
      <button v-if="canConfirmPrivateBooking(currentRole, selectedBooking.status)" type="button" :disabled="pending" @click="bookingAction('confirm')">确认</button>
      <button v-if="canRejectPrivateBooking(currentRole, selectedBooking.status)" class="button-secondary" type="button" :disabled="pending" @click="bookingAction('reject')">拒绝</button>
      <button v-if="canCancelPendingPrivateBooking(currentRole, selectedBooking.status)" class="button-danger" type="button" :disabled="pending" @click="bookingAction('cancel')">取消待确认</button>
      <button v-if="canSignInPrivateBooking(currentRole, selectedBooking.status)" type="button" :disabled="pending || !lessonForm.content" @click="signIn">签到并记录</button>
    </div>
  </section>
</template>
