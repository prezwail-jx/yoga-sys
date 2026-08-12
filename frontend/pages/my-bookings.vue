<script setup lang="ts">
import type { ClassBooking, ClassBookingStatus, ClassSession, ClassSessionStatus } from "~/types/domain"
import { getMemberCancellationAvailability } from "~/utils/classBooking"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-auth" })

const api = useGymApi()
const { user, loadUser } = useAuth()
const cancelSubmit = useIdempotentSubmit()

if (!user.value) await loadUser()
if (user.value?.role !== "member") await navigateTo("/forbidden")

const skip = ref(0)
const limit = 20
const now = ref(Date.now())
const cancelTarget = ref<ClassBooking | null>(null)
const cancellationReason = ref("")
const errorMessage = ref("")
const successMessage = ref("")

let clock: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 30_000)
})
onUnmounted(() => clearInterval(clock))

const { data, refresh, status, error } = await useAsyncData(
  "my-class-bookings",
  async () => {
    const bookingList = await api.getMyClassBookings({ skip: skip.value, limit })
    const reservedSessionIds = [...new Set(
      bookingList.items.filter(booking => booking.status === "reserved").map(booking => booking.classSessionId),
    )]
    const sessions = await Promise.all(reservedSessionIds.map(id => api.getClassSession(id)))
    return { bookingList, sessions: Object.fromEntries(sessions.map(session => [session.id, session])) }
  },
  { watch: [skip] },
)

const bookings = computed(() => data.value?.bookingList.items || [])
const total = computed(() => data.value?.bookingList.total || 0)
const sessions = computed<Record<string, ClassSession>>(() => data.value?.sessions || {})

const bookingStatusLabels: Record<ClassBookingStatus, string> = {
  reserved: "已预约",
  checked_in: "已签到",
  cancelled: "已取消",
  absent: "缺勤",
}
const sessionStatusLabels: Record<ClassSessionStatus, string> = {
  draft: "草稿",
  published: "已发布",
  paused: "已暂停",
  cancelled: "已取消",
  completed: "已完成",
}
const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "long",
  day: "numeric",
  weekday: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

function formatDateTime(value: string | number) {
  return dateTimeFormatter.format(new Date(value))
}

function cancellationAvailability(booking: ClassBooking) {
  const session = sessions.value[booking.classSessionId]
  if (!session) return null
  return getMemberCancellationAvailability(booking, session.cancelCutoffMinutesBefore, now.value)
}

function cancellationHint(booking: ClassBooking) {
  const availability = cancellationAvailability(booking)
  if (!availability || availability.available) return ""
  if (availability.reason === "cutoff_passed") return `已于 ${formatDateTime(availability.cutoffAt)} 截止取消`
  if (availability.reason === "session_terminal") return "课次已结束或取消"
  return "预约已处理，不能取消"
}

function openCancellation(booking: ClassBooking) {
  errorMessage.value = ""
  successMessage.value = ""
  cancellationReason.value = ""
  cancelTarget.value = booking
}

async function cancelBooking() {
  if (!cancelTarget.value) return
  errorMessage.value = ""
  successMessage.value = ""
  const booking = cancelTarget.value
  const reason = cancellationReason.value.trim()
  try {
    await cancelSubmit.submit(
      `member-cancel-booking:${booking.id}:${reason}`,
      key => api.cancelClassBooking(booking.id, { reason: reason || null }, key),
    )
    cancelSubmit.reset()
    cancelTarget.value = null
    successMessage.value = `已取消 ${booking.courseName} 的预约`
    await refresh()
  } catch (submitError: unknown) {
    errorMessage.value = getApiErrorMessage(submitError, "取消预约失败")
  }
}
</script>

<template>
  <section class="panel bookings-panel">
    <div class="section-heading bookings-heading">
      <div>
        <p class="eyebrow">我的预约</p>
        <h2>预约记录</h2>
        <p class="hint">共 {{ total }} 条预约记录，身份由当前登录账号确定</p>
      </div>
      <NuxtLink class="schedule-link" to="/schedule">查看团课课表</NuxtLink>
    </div>

    <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>

    <CommonAsyncState
      :status="status"
      :empty="!bookings.length"
      pending-text="正在加载我的预约…"
      empty-text="暂无预约记录，可前往团课课表预约。"
      :error-message="getApiErrorMessage(error, '预约记录加载失败')"
      @retry="refresh"
    >
      <div class="booking-list">
        <article v-for="booking in bookings" :key="booking.id" class="booking-card" :class="`booking-card--${booking.status}`">
          <div class="booking-date">
            <span>{{ new Date(booking.startAt).toLocaleDateString("zh-CN", { month: "short", day: "numeric" }) }}</span>
            <strong>{{ new Date(booking.startAt).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false }) }}</strong>
          </div>
          <div class="booking-main">
            <div class="booking-title">
              <h3>{{ booking.courseName }}</h3>
              <span class="booking-status" :class="`booking-status--${booking.status}`">{{ bookingStatusLabels[booking.status] }}</span>
            </div>
            <p>{{ booking.coachName }} 教练 · {{ booking.roomName }}</p>
            <p>{{ formatDateTime(booking.startAt) }} 至 {{ formatDateTime(booking.endAt) }}</p>
            <div class="booking-meta">
              <span>课次：{{ sessionStatusLabels[booking.sessionStatus] }}</span>
              <span>预约于 {{ formatDateTime(booking.bookedAt) }}</span>
            </div>
            <p v-if="booking.cancellationReason" class="cancel-reason">取消原因：{{ booking.cancellationReason }}</p>
          </div>
          <div class="booking-actions">
            <button
              v-if="booking.status === 'reserved'"
              class="button-secondary"
              type="button"
              :disabled="cancelSubmit.pending.value || !cancellationAvailability(booking)?.available"
              @click="openCancellation(booking)"
            >取消预约</button>
            <small v-if="cancellationHint(booking)">{{ cancellationHint(booking) }}</small>
          </div>
        </article>
      </div>
    </CommonAsyncState>

    <div class="pagination">
      <button class="button-secondary" type="button" :disabled="skip === 0" @click="skip = Math.max(0, skip - limit)">上一页</button>
      <span>第 {{ Math.floor(skip / limit) + 1 }} 页</span>
      <button class="button-secondary" type="button" :disabled="skip + limit >= total" @click="skip += limit">下一页</button>
    </div>
  </section>

  <section v-if="cancelTarget" class="panel cancel-panel">
    <div class="section-heading">
      <div><p class="eyebrow">取消预约</p><h2>{{ cancelTarget.courseName }}</h2></div>
      <button class="button-secondary" type="button" :disabled="cancelSubmit.pending.value" @click="cancelTarget = null">关闭</button>
    </div>
    <p>{{ formatDateTime(cancelTarget.startAt) }} · {{ cancelTarget.coachName }} 教练</p>
    <label>取消原因（选填）<textarea v-model="cancellationReason" rows="3" maxlength="255" placeholder="填写后将保留在预约记录中" /></label>
    <div class="confirm-bar">
      <span>提交后将按卡项规则处理预扣权益</span>
      <button class="button-danger" type="button" :disabled="cancelSubmit.pending.value" @click="cancelBooking">{{ cancelSubmit.pending.value ? "处理中…" : "确认取消预约" }}</button>
    </div>
  </section>
</template>

<style scoped>
.bookings-heading { align-items: flex-start; }
.eyebrow { margin: 0 0 .35rem; color: var(--brand); font-size: .72rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
.bookings-heading h2, .booking-title h3, .booking-card p, .cancel-panel h2 { margin: 0; }
.schedule-link { display: inline-flex; align-items: center; padding: 9px 12px; color: #fff; background: var(--brand); border-radius: 10px; font-weight: 600; }
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
.booking-list { display: grid; gap: .75rem; }
.booking-card { display: grid; grid-template-columns: 90px minmax(0, 1fr) auto; gap: 1rem; padding: 1rem; border: 1px solid var(--border); border-left: 4px solid var(--brand); border-radius: 12px; background: #fff; }
.booking-card--cancelled, .booking-card--absent { border-left-color: #94a3b8; }
.booking-date { display: grid; align-content: center; gap: .25rem; padding-right: 1rem; border-right: 1px solid var(--border); text-align: center; }
.booking-date span { color: var(--muted); font-size: .8rem; }
.booking-date strong { font-size: 1.2rem; }
.booking-main { display: grid; gap: .45rem; min-width: 0; }
.booking-title { display: flex; align-items: flex-start; justify-content: space-between; gap: .75rem; }
.booking-main > p { color: var(--muted); font-size: .85rem; }
.booking-meta { display: flex; flex-wrap: wrap; gap: .45rem; }
.booking-meta span { padding: .25rem .5rem; border-radius: 999px; color: #6b4a37; background: #fff4eb; font-size: .75rem; }
.booking-status { flex: none; padding: .25rem .55rem; border-radius: 999px; color: #8c3d1f; background: #fff2e9; font-size: .75rem; font-weight: 700; }
.booking-status--checked_in { color: #37622a; background: #eaf6e4; }
.booking-status--cancelled, .booking-status--absent { color: #475569; background: #e2e8f0; }
.booking-main .cancel-reason { color: #7f1d1d; }
.booking-actions { display: grid; align-content: center; justify-items: end; gap: .4rem; max-width: 230px; }
.booking-actions small { color: var(--muted); text-align: right; }
.pagination { display: flex; align-items: center; justify-content: center; gap: .75rem; margin-top: 1rem; }
.cancel-panel { border-top: 4px solid #a43c2f; }
.cancel-panel > p { margin: .5rem 0 1rem; color: var(--muted); }
.cancel-panel label { display: grid; gap: .5rem; color: var(--muted); font-size: .85rem; }
.cancel-panel textarea { width: 100%; color: var(--ink); }
.confirm-bar { display: flex; align-items: center; justify-content: flex-end; gap: .75rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.confirm-bar span { margin-right: auto; color: var(--muted); font-size: .85rem; }
@media (max-width: 720px) {
  .bookings-heading { align-items: stretch; flex-direction: column; }
  .schedule-link { justify-content: center; }
  .booking-card { grid-template-columns: 64px minmax(0, 1fr); gap: .75rem; padding: .8rem; }
  .booking-date { padding-right: .75rem; }
  .booking-actions { grid-column: 1 / -1; justify-items: stretch; max-width: none; }
  .booking-actions small { text-align: left; }
  .confirm-bar { align-items: stretch; flex-direction: column; }
  .confirm-bar span { margin-right: 0; }
}
</style>
