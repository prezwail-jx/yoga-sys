<script setup lang="ts">
import type { ClassBooking, ClassBookingStatus, ClassSessionStatus, Member } from "~/types/domain"
import { getCheckInAvailability } from "~/utils/classBooking"
import { getApiErrorMessage } from "~/utils/errors"
import { label, userRoleLabels } from "~/utils/labels"

const route = useRoute()
const sessionId = String(route.params.sessionId || "")
const api = useGymApi()
const { user, loadUser } = useAuth()
const operationSubmit = useIdempotentSubmit()
const operationPending = operationSubmit.pending

if (!user.value) {
  try {
    await loadUser()
  } catch {
    await navigateTo("/login")
  }
}

const {
  data: session,
  error: sessionError,
  refresh: refreshSession,
  status: sessionLoadStatus,
} = await useAsyncData(`class-session-${sessionId}`, () => api.getClassSession(sessionId))

const canAccess = computed(() => user.value?.role === "admin" || (
  user.value?.role === "coach" && user.value.coachProfileId === session.value?.coachProfileId
))

if (session.value && !canAccess.value) await navigateTo("/forbidden")

const {
  data: bookingList,
  error: bookingError,
  refresh: refreshBookings,
  status: bookingLoadStatus,
} = await useAsyncData(`class-session-bookings-${sessionId}`, async () => {
  if (!canAccess.value) return { items: [], total: 0, skip: 0, limit: 1 }
  return api.getClassSessionBookings(sessionId)
})

const now = ref(Date.now())
let clock: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 30_000)
})
onUnmounted(() => clearInterval(clock))

const isAdmin = computed(() => user.value?.role === "admin")
const bookings = computed(() => bookingList.value?.items || [])
const reservedCount = computed(() => bookings.value.filter(item => item.status === "reserved").length)
const checkInAvailability = computed(() => session.value
  ? getCheckInAvailability(session.value, now.value)
  : null)
const canComplete = computed(() => Boolean(
  isAdmin.value
  && session.value
  && ["published", "paused"].includes(session.value.status)
  && now.value >= new Date(session.value.endAt).getTime(),
))
const canCancelSession = computed(() => Boolean(
  isAdmin.value && session.value && ["draft", "published", "paused"].includes(session.value.status),
))

const errorMessage = ref("")
const successMessage = ref("")
const activeBookingId = ref<string | null>(null)
const memberSearch = ref("")
const memberResults = ref<Member[]>([])
const memberSearchPending = ref(false)
const selectedMember = ref<Member | null>(null)
const showProxyBooking = ref(false)
const cancelTarget = ref<ClassBooking | null>(null)
const cancellationReason = ref("")
const sessionAction = ref<"cancel" | "complete" | null>(null)
const completionStep = ref<1 | 2>(1)

const sessionStatusLabels: Record<ClassSessionStatus, string> = {
  draft: "草稿",
  published: "已发布",
  paused: "已暂停",
  cancelled: "已取消",
  completed: "已完成",
}
const bookingStatusLabels: Record<ClassBookingStatus, string> = {
  reserved: "已预约",
  checked_in: "已签到",
  cancelled: "已取消",
  absent: "缺勤",
}
const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "long",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})
const shortDateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "numeric",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

function formatDateTime(value: string | number) {
  return dateTimeFormatter.format(new Date(value))
}

function formatShortDateTime(value: string | number) {
  return shortDateTimeFormatter.format(new Date(value))
}

function checkInHint() {
  const availability = checkInAvailability.value
  if (!availability || availability.available) return ""
  if (availability.reason === "not_open") return `签到尚未开放，将于 ${formatShortDateTime(availability.opensAt)} 开放`
  if (availability.reason === "not_published") return "当前课次状态不允许签到"
  return "课次已进入终态，不能签到"
}

async function refreshOperationsData() {
  await Promise.all([refreshSession(), refreshBookings()])
}

function clearMessages() {
  errorMessage.value = ""
  successMessage.value = ""
}

async function searchMembers() {
  memberSearchPending.value = true
  errorMessage.value = ""
  try {
    const result = await api.getMembers({
      keyword: memberSearch.value.trim() || undefined,
      status: "normal",
      limit: 20,
    })
    memberResults.value = result.items
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "会员搜索失败")
  } finally {
    memberSearchPending.value = false
  }
}

async function openProxyBooking() {
  clearMessages()
  selectedMember.value = null
  memberSearch.value = ""
  showProxyBooking.value = true
  await searchMembers()
}

async function createProxyBooking() {
  if (!selectedMember.value) return
  clearMessages()
  try {
    const member = selectedMember.value
    await operationSubmit.submit(
      `proxy-booking:${sessionId}:${member.id}`,
      key => api.createAdminClassBooking(sessionId, member.id, key),
    )
    operationSubmit.reset()
    showProxyBooking.value = false
    selectedMember.value = null
    successMessage.value = `已为 ${member.name} 代约`
    await refreshOperationsData()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "代约失败")
  }
}

function openBookingCancellation(booking: ClassBooking) {
  clearMessages()
  cancelTarget.value = booking
  cancellationReason.value = ""
}

async function cancelBooking() {
  if (!cancelTarget.value) return
  clearMessages()
  activeBookingId.value = cancelTarget.value.id
  try {
    const booking = cancelTarget.value
    const reason = cancellationReason.value.trim()
    await operationSubmit.submit(
      `cancel-booking:${booking.id}:${reason}`,
      key => api.cancelClassBooking(booking.id, { reason: reason || null }, key),
    )
    operationSubmit.reset()
    cancelTarget.value = null
    successMessage.value = `已取消 ${booking.memberName} 的预约`
    await refreshOperationsData()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "取消预约失败")
  } finally {
    activeBookingId.value = null
  }
}

async function checkIn(booking: ClassBooking) {
  clearMessages()
  activeBookingId.value = booking.id
  try {
    await operationSubmit.submit(
      `check-in:${booking.id}`,
      key => api.checkInClassBooking(booking.id, key),
    )
    operationSubmit.reset()
    successMessage.value = `${booking.memberName} 已签到`
    await refreshOperationsData()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "签到失败")
  } finally {
    activeBookingId.value = null
  }
}

function openSessionAction(action: "cancel" | "complete") {
  clearMessages()
  sessionAction.value = action
  completionStep.value = 1
}

async function submitSessionAction() {
  if (!sessionAction.value) return
  clearMessages()
  const action = sessionAction.value
  try {
    await operationSubmit.submit(
      `${action}-session:${sessionId}`,
      key => action === "cancel"
        ? api.cancelClassSession(sessionId, key)
        : api.completeClassSession(sessionId, key),
    )
    operationSubmit.reset()
    sessionAction.value = null
    successMessage.value = action === "cancel" ? "整节课已取消，预约权益已强制返还" : "课次已完成，缺勤已处理"
    await refreshOperationsData()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, action === "cancel" ? "取消课次失败" : "完成课次失败")
  }
}
</script>

<template>
  <CommonAsyncState
    :status="sessionLoadStatus"
    :empty="!session"
    pending-text="正在加载课次运营台…"
    empty-text="课次不存在"
    :error-message="getApiErrorMessage(sessionError, '课次加载失败')"
    @retry="refreshSession"
  >
    <template v-if="session && canAccess">
      <section class="panel session-hero">
        <div class="hero-copy">
          <NuxtLink class="back-link" to="/schedule">← 返回周课表</NuxtLink>
          <div class="session-title-row">
            <div>
              <p class="eyebrow">课次运营</p>
              <h2>{{ session.courseName }}</h2>
            </div>
            <span class="session-status" :class="`session-status--${session.status}`">{{ sessionStatusLabels[session.status] }}</span>
          </div>
          <p class="session-time">{{ formatDateTime(session.startAt) }} 至 {{ formatDateTime(session.endAt) }}</p>
          <p class="session-place">{{ session.coachName }} 教练 · {{ session.roomName }}</p>
        </div>
        <div class="capacity-ring" :aria-label="`已约 ${session.bookedCount} 人，容量 ${session.capacity} 人`">
          <strong>{{ session.bookedCount }}<small>/{{ session.capacity }}</small></strong>
          <span>已约人数</span>
        </div>
      </section>

      <section class="session-metrics">
        <article><span>教练</span><strong>{{ session.coachName }}</strong></article>
        <article><span>教室</span><strong>{{ session.roomName }}</strong></article>
        <article><span>容量</span><strong>{{ session.capacity }} 人</strong></article>
        <article><span>剩余</span><strong>{{ session.remainingCapacity }} 位</strong></article>
      </section>

      <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>

      <section v-if="isAdmin" class="panel operations-panel">
        <div class="section-heading">
          <div><h2>运营操作</h2><p class="hint">高风险操作由后端再次校验权限和课次状态</p></div>
          <div class="actions operation-actions">
            <button type="button" :disabled="operationPending || session.status !== 'published' || session.remainingCapacity === 0" @click="openProxyBooking">会员代约</button>
            <button class="button-danger" type="button" :disabled="operationPending || !canCancelSession" @click="openSessionAction('cancel')">取消整节课</button>
            <button type="button" :disabled="operationPending || !canComplete" @click="openSessionAction('complete')">完成课次</button>
          </div>
        </div>
        <p v-if="!canComplete && ['published', 'paused'].includes(session.status)" class="operation-hint">课次结束后才能完成；当前结束时间为 {{ formatDateTime(session.endAt) }}。</p>
      </section>

      <section class="panel roster-panel">
        <div class="section-heading roster-heading">
          <div><h2>预约名单</h2><p class="hint">全部状态 · {{ bookingList?.total || 0 }} 条记录</p></div>
          <span v-if="checkInHint()" class="check-in-notice">{{ checkInHint() }}</span>
        </div>
        <CommonAsyncState
          :status="bookingLoadStatus"
          :empty="!bookings.length"
          pending-text="正在加载预约名单…"
          empty-text="本课次暂无预约记录"
          :error-message="getApiErrorMessage(bookingError, '预约名单加载失败')"
          @retry="refreshBookings"
        >
          <div class="roster-list">
            <article v-for="booking in bookings" :key="booking.id" class="booking-row" :class="`booking-row--${booking.status}`">
              <div class="member-avatar">{{ booking.memberName.slice(0, 1) }}</div>
              <div class="member-details">
                <div class="member-name-row"><strong>{{ booking.memberName }}</strong><span class="booking-status" :class="`booking-status--${booking.status}`">{{ bookingStatusLabels[booking.status] }}</span></div>
                <p>预约于 {{ formatShortDateTime(booking.bookedAt) }}<span v-if="booking.bookedByRole"> · {{ label(userRoleLabels, booking.bookedByRole) }}</span></p>
                <p v-if="booking.terminalAt">处理于 {{ formatShortDateTime(booking.terminalAt) }}<span v-if="booking.cancellationReason"> · 原因：{{ booking.cancellationReason }}</span></p>
              </div>
              <div v-if="booking.status === 'reserved'" class="booking-actions">
                <button type="button" :disabled="operationPending || !checkInAvailability?.available" @click="checkIn(booking)">{{ activeBookingId === booking.id ? "处理中…" : "签到" }}</button>
                <button v-if="isAdmin" class="button-secondary" type="button" :disabled="operationPending" @click="openBookingCancellation(booking)">取消预约</button>
              </div>
            </article>
          </div>
        </CommonAsyncState>
      </section>

      <section v-if="isAdmin && showProxyBooking" class="panel action-sheet">
        <div class="section-heading"><div><p class="eyebrow">管理员操作</p><h2>选择正常会员代约</h2></div><button class="button-secondary" type="button" @click="showProxyBooking = false">关闭</button></div>
        <form class="member-search" @submit.prevent="searchMembers">
          <input v-model="memberSearch" placeholder="按会员姓名或手机号搜索" aria-label="会员搜索关键词" />
          <button type="submit" :disabled="memberSearchPending">{{ memberSearchPending ? "搜索中…" : "搜索" }}</button>
        </form>
        <div class="member-results">
          <button v-for="member in memberResults" :key="member.id" class="member-option" :class="{ 'member-option--selected': selectedMember?.id === member.id }" type="button" @click="selectedMember = member">
            <span><strong>{{ member.name }}</strong><small>{{ member.phone }}</small></span><span>{{ selectedMember?.id === member.id ? "已选择" : "选择" }}</span>
          </button>
          <p v-if="!memberSearchPending && !memberResults.length" class="empty-inline">没有符合条件的正常会员</p>
        </div>
        <div class="confirm-bar"><span>{{ selectedMember ? `将为 ${selectedMember.name} 预约本课次` : "请先选择会员" }}</span><button type="button" :disabled="!selectedMember || operationPending" @click="createProxyBooking">{{ operationPending ? "提交中…" : "确认代约" }}</button></div>
      </section>

      <section v-if="isAdmin && cancelTarget" class="panel action-sheet danger-sheet">
        <div class="section-heading"><div><p class="eyebrow">取消预约</p><h2>{{ cancelTarget.memberName }}</h2></div><button class="button-secondary" type="button" @click="cancelTarget = null">关闭</button></div>
        <label class="reason-field">取消原因（选填）<textarea v-model="cancellationReason" rows="3" maxlength="255" placeholder="填写后将保留在预约记录中" /></label>
        <div class="confirm-bar"><span>仅可取消状态为“已预约”的记录</span><button class="button-danger" type="button" :disabled="operationPending" @click="cancelBooking">{{ operationPending ? "处理中…" : "确认取消预约" }}</button></div>
      </section>

      <section v-if="isAdmin && sessionAction === 'cancel'" class="panel action-sheet danger-sheet">
        <p class="eyebrow">高风险操作</p><h2>确认取消整节课？</h2>
        <p>系统将取消全部 {{ reservedCount }} 条有效预约，并<strong>强制返还所有预扣权益</strong>，不受会员卡项取消返还规则影响。已有签到时后端会拒绝取消。</p>
        <div class="confirm-bar"><button class="button-secondary" type="button" @click="sessionAction = null">返回</button><button class="button-danger" type="button" :disabled="operationPending" @click="submitSessionAction">{{ operationPending ? "处理中…" : "确认取消并强制返还" }}</button></div>
      </section>

      <section v-if="isAdmin && sessionAction === 'complete'" class="panel action-sheet completion-sheet">
        <p class="eyebrow">完成课次 · 第 {{ completionStep }} 次确认</p><h2>预计缺勤 {{ reservedCount }} 人</h2>
        <p>完成后，当前仍为“已预约”的 {{ reservedCount }} 条记录将批量标记为缺勤并完成权益核销，此操作不可撤销。</p>
        <div class="absence-preview"><span>已签到 {{ bookings.filter(item => item.status === 'checked_in').length }} 人</span><strong>预计缺勤 {{ reservedCount }} 人</strong></div>
        <div class="confirm-bar">
          <button class="button-secondary" type="button" @click="sessionAction = null">返回</button>
          <button v-if="completionStep === 1" type="button" @click="completionStep = 2">确认人数，继续</button>
          <button v-else class="button-danger" type="button" :disabled="operationPending" @click="submitSessionAction">{{ operationPending ? "处理中…" : "二次确认并完成课次" }}</button>
        </div>
      </section>
    </template>
  </CommonAsyncState>
</template>

<style scoped>
.session-hero { display: grid; grid-template-columns: 1fr auto; gap: 2rem; padding: 1.5rem; background: linear-gradient(135deg, #fff 20%, #fff6ee); }
.hero-copy { min-width: 0; }
.back-link { display: inline-block; margin-bottom: 1.25rem; color: var(--brand); font-size: .88rem; font-weight: 600; }
.eyebrow { margin: 0 0 .35rem; color: var(--brand); font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
.session-title-row { display: flex; align-items: flex-start; gap: 1rem; }
.session-title-row h2 { margin: 0; font-size: clamp(1.8rem, 4vw, 2.6rem); }
.session-status, .booking-status { display: inline-flex; border-radius: 999px; font-size: .75rem; font-weight: 700; }
.session-status { margin-top: .4rem; padding: .35rem .7rem; color: #8c3d1f; background: var(--brand-soft); }
.session-status--cancelled, .session-status--completed { color: #475569; background: #e2e8f0; }
.session-status--paused { color: #854d0e; background: #fef3c7; }
.session-status--draft { color: #475569; background: #f1f5f9; }
.session-time { margin: 1rem 0 .35rem; font-size: 1rem; font-weight: 700; }
.session-place { margin: 0; color: var(--muted); }
.capacity-ring { display: grid; place-content: center; width: 145px; aspect-ratio: 1; border: 10px solid #f1dfd1; border-top-color: var(--brand); border-radius: 50%; text-align: center; }
.capacity-ring strong { font-size: 2rem; line-height: 1; }
.capacity-ring small { color: var(--muted); font-size: 1rem; }
.capacity-ring span { margin-top: .4rem; color: var(--muted); font-size: .75rem; }
.session-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: .75rem; margin-bottom: 1rem; }
.session-metrics article { display: grid; gap: .45rem; padding: 1rem; border: 1px solid var(--border); border-radius: 12px; background: rgb(255 255 255 / 80%); }
.session-metrics span { color: var(--muted); font-size: .75rem; }
.session-metrics strong { font-size: 1rem; }
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
.operations-panel .hint, .roster-heading .hint { margin-top: .35rem; }
.operation-hint { margin: -.25rem 0 0; color: var(--muted); font-size: .82rem; }
.roster-heading { align-items: flex-start; }
.check-in-notice { max-width: 360px; padding: .5rem .75rem; border-radius: 8px; color: #854d0e; background: #fef9e7; font-size: .78rem; }
.roster-list { display: grid; }
.booking-row { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 1rem; padding: 1rem .25rem; border-bottom: 1px solid var(--border); }
.booking-row:last-child { border-bottom: 0; }
.booking-row--cancelled, .booking-row--absent { opacity: .68; }
.member-avatar { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 50%; color: #8c3d1f; background: var(--brand-soft); font-weight: 800; }
.member-details { min-width: 0; }
.member-name-row { display: flex; align-items: center; gap: .55rem; }
.member-details p { margin: .25rem 0 0; overflow: hidden; color: var(--muted); font-size: .78rem; text-overflow: ellipsis; white-space: nowrap; }
.booking-status { padding: .25rem .55rem; color: #8c3d1f; background: #fff2e9; }
.booking-status--checked_in { color: #37622a; background: #eaf6e4; }
.booking-status--cancelled, .booking-status--absent { color: #475569; background: #e2e8f0; }
.booking-actions { display: flex; gap: .45rem; }
.action-sheet { border-top: 4px solid var(--brand); }
.danger-sheet { border-top-color: #a43c2f; }
.action-sheet > p:not(.eyebrow) { max-width: 760px; color: var(--muted); line-height: 1.65; }
.member-search { display: flex; gap: .5rem; margin-bottom: .75rem; }
.member-search input { flex: 1; }
.member-results { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; max-height: 290px; overflow: auto; }
.member-option { display: flex; align-items: center; justify-content: space-between; padding: .75rem; color: var(--ink); background: #fff; text-align: left; }
.member-option span:first-child { display: grid; gap: .2rem; }
.member-option small { color: var(--muted); }
.member-option--selected { border-color: var(--brand); background: #fff8f2; }
.empty-inline { grid-column: 1 / -1; color: var(--muted); text-align: center; }
.confirm-bar { display: flex; align-items: center; justify-content: flex-end; gap: .75rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.confirm-bar span { margin-right: auto; color: var(--muted); font-size: .85rem; }
.reason-field { display: grid; gap: .5rem; color: var(--muted); font-size: .82rem; }
.reason-field textarea { width: 100%; color: var(--ink); }
.absence-preview { display: flex; justify-content: space-between; max-width: 560px; padding: 1rem; border-radius: 10px; background: #fff6ee; }
.absence-preview strong { color: #9a3412; }
@media (max-width: 760px) {
  .session-hero { grid-template-columns: 1fr; gap: 1rem; }
  .capacity-ring { width: 115px; }
  .session-metrics { grid-template-columns: repeat(2, 1fr); }
  .operations-panel .section-heading, .operation-actions, .roster-heading { align-items: stretch; flex-direction: column; }
  .booking-row { grid-template-columns: auto minmax(0, 1fr); }
  .booking-actions { grid-column: 1 / -1; }
  .booking-actions button { flex: 1; }
  .member-results { grid-template-columns: 1fr; }
  .confirm-bar { align-items: stretch; flex-direction: column; }
  .confirm-bar span { margin-right: 0; }
  .confirm-bar button { width: 100%; }
}
@media (max-width: 480px) {
  .session-title-row { flex-direction: column; gap: .25rem; }
  .session-status { margin-top: 0; }
  .session-metrics { grid-template-columns: 1fr; }
  .member-search, .absence-preview { flex-direction: column; }
}
</style>
