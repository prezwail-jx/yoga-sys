<script setup lang="ts">
import type { ClassSession, ClassSessionInput, ClassSessionStatus, CopyWeekResult } from "~/types/domain"
import { getMemberBookingAvailability } from "~/utils/classBooking"
import { addLocalDays, getNaturalWeekStart, groupSessionsByWeek, isoToLocalDateTime, localDateTimeToIso } from "~/utils/classSchedule"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-auth" })

const api = useGymApi()
const { user, loadUser } = useAuth()
const copySubmit = useIdempotentSubmit()
const bookingSubmit = useIdempotentSubmit()
if (!user.value) await loadUser()

const weekStart = ref(getNaturalWeekStart())
const showForm = ref(false)
const editingId = ref<string | null>(null)
const pending = ref(false)
const actionId = ref<string | null>(null)
const bookingSessionId = ref<string | null>(null)
const errorMessage = ref("")
const successMessage = ref("")
const copyResult = ref<CopyWeekResult | null>(null)
const isAdmin = computed(() => user.value?.role === "admin")
const isMember = computed(() => user.value?.role === "member")
const canOpenDetails = computed(() => user.value?.role === "admin" || user.value?.role === "coach")

const newSession = (): ClassSessionInput => ({
  courseId: "",
  coachProfileId: "",
  roomId: "",
  startAt: `${weekStart.value}T09:00`,
  endAt: `${weekStart.value}T10:00`,
  capacity: 20,
  bookingOpenHoursBefore: 168,
  bookingCloseMinutesBefore: 60,
  cancelCutoffMinutesBefore: 120,
})
const form = reactive<ClassSessionInput>(newSession())

const { data: schedule, refresh, status, error } = await useAsyncData(
  "class-sessions-week",
  () => api.getClassSessions(weekStart.value),
  { watch: [weekStart] },
)
const { data: catalog } = await useAsyncData("enabled-class-catalog", async () => {
  if (!isAdmin.value) return null
  const [courses, rooms, coaches] = await Promise.all([
    api.getCourses({ enabled: true, limit: 100 }),
    api.getRooms({ enabled: true, limit: 100 }),
    api.getCoaches({ enabled: true, limit: 100 }),
  ])
  return { courses: courses.items, rooms: rooms.items, coaches: coaches.items }
})
const { data: myBookingList, refresh: refreshMyBookings } = await useAsyncData(
  "member-schedule-bookings",
  () => isMember.value
    ? api.getMyClassBookings({ limit: 100 })
    : Promise.resolve({ items: [], total: 0, skip: 0, limit: 100 }),
)

const now = ref(Date.now())
let clock: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  clock = setInterval(() => { now.value = Date.now() }, 30_000)
})
onUnmounted(() => clearInterval(clock))

const visibleSessions = computed(() => {
  const items = schedule.value?.items || []
  if (user.value?.role !== "coach") return items
  return items.filter(item => item.coachProfileId === user.value?.coachProfileId)
})
const days = computed(() => groupSessionsByWeek(visibleSessions.value, weekStart.value))
const weekEnd = computed(() => addLocalDays(weekStart.value, 6))
const activeBookingsBySession = computed(() => new Map(
  (myBookingList.value?.items || [])
    .filter(booking => booking.status === "reserved" || booking.status === "checked_in")
    .map(booking => [booking.classSessionId, booking]),
))

const statusLabels: Record<ClassSessionStatus, string> = {
  draft: "草稿",
  published: "已发布",
  paused: "已暂停",
  cancelled: "已取消",
  completed: "已完成",
}
const weekdayFormatter = new Intl.DateTimeFormat("zh-CN", { weekday: "long" })
const dayFormatter = new Intl.DateTimeFormat("zh-CN", { month: "numeric", day: "numeric" })
const timeFormatter = new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })

function formatDay(date: string) {
  const value = new Date(`${date}T12:00:00`)
  return `${weekdayFormatter.format(value)} · ${dayFormatter.format(value)}`
}

function formatTime(value: string) {
  return timeFormatter.format(new Date(value))
}

function memberBookingAvailability(session: ClassSession) {
  return getMemberBookingAvailability(session, activeBookingsBySession.value.has(session.id), now.value)
}

function memberBookingLabel(session: ClassSession) {
  const availability = memberBookingAvailability(session)
  if (availability.available) return "立即预约"
  if (availability.reason === "already_booked") return "已预约"
  if (availability.reason === "full") return "已满员"
  if (availability.reason === "not_open") return "未开放"
  if (availability.reason === "closed") return "已截止"
  if (session.status === "paused") return "已暂停"
  if (session.status === "cancelled") return "已取消"
  if (session.status === "completed") return "已完成"
  return "未发布"
}

function changeWeek(days: number) {
  weekStart.value = addLocalDays(weekStart.value, days)
  copyResult.value = null
  showForm.value = false
}

async function bookSession(session: ClassSession) {
  bookingSessionId.value = session.id
  errorMessage.value = ""
  successMessage.value = ""
  try {
    await bookingSubmit.submit(
      `member-booking:${session.id}`,
      key => api.createMemberClassBooking(session.id, key),
    )
    bookingSubmit.reset()
    successMessage.value = `已预约 ${session.courseName}`
    await Promise.all([refresh(), refreshMyBookings()])
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "预约失败")
  } finally {
    bookingSessionId.value = null
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, newSession())
  if (catalog.value) {
    form.courseId = catalog.value.courses[0]?.id || ""
    form.coachProfileId = catalog.value.coaches[0]?.id || ""
    form.roomId = catalog.value.rooms[0]?.id || ""
    form.capacity = catalog.value.rooms[0]?.capacity || 20
  }
  showForm.value = true
}

function openEdit(session: ClassSession) {
  editingId.value = session.id
  Object.assign(form, {
    courseId: session.courseId,
    coachProfileId: session.coachProfileId,
    roomId: session.roomId,
    startAt: isoToLocalDateTime(session.startAt),
    endAt: isoToLocalDateTime(session.endAt),
    capacity: session.capacity,
    bookingOpenHoursBefore: session.bookingOpenHoursBefore,
    bookingCloseMinutesBefore: session.bookingCloseMinutesBefore,
    cancelCutoffMinutesBefore: session.cancelCutoffMinutesBefore,
  })
  showForm.value = true
}

async function saveSession() {
  pending.value = true
  errorMessage.value = ""
  try {
    const payload: ClassSessionInput = {
      ...form,
      startAt: localDateTimeToIso(form.startAt),
      endAt: localDateTimeToIso(form.endAt),
    }
    if (editingId.value) await api.updateClassSession(editingId.value, payload)
    else await api.createClassSession(payload)
    showForm.value = false
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "课次保存失败")
  } finally {
    pending.value = false
  }
}

async function transition(session: ClassSession, action: "publish" | "pause" | "resume") {
  actionId.value = session.id
  errorMessage.value = ""
  try {
    if (action === "publish") await api.publishClassSession(session.id)
    if (action === "pause") await api.pauseClassSession(session.id)
    if (action === "resume") await api.resumeClassSession(session.id)
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "状态修改失败")
  } finally {
    actionId.value = null
  }
}

async function copyPreviousWeek() {
  pending.value = true
  errorMessage.value = ""
  copyResult.value = null
  const sourceWeekStart = addLocalDays(weekStart.value, -7)
  try {
    copyResult.value = await copySubmit.submit(
      `copy-week:${sourceWeekStart}:${weekStart.value}`,
      key => api.copyClassSessionWeek(
        { sourceWeekStart, targetWeekStart: weekStart.value },
        key,
      ),
    )
    await refresh()
    copySubmit.reset()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "复制上周失败")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="panel schedule-panel">
    <div class="section-heading schedule-heading">
      <div>
        <h2>团课周课表</h2>
        <p class="hint">{{ weekStart }} 至 {{ weekEnd }}<span v-if="user?.role === 'coach'"> · 仅显示我的课次</span></p>
      </div>
      <div v-if="isAdmin" class="actions">
        <NuxtLink class="button-secondary link-button" to="/class-catalog">基础资料</NuxtLink>
        <button class="button-secondary" type="button" :disabled="pending" @click="copyPreviousWeek">复制上周</button>
        <button type="button" :disabled="!catalog?.courses.length || !catalog?.rooms.length || !catalog?.coaches.length" @click="openCreate">新建课次</button>
      </div>
    </div>

    <div class="week-toolbar">
      <button class="button-secondary" type="button" @click="changeWeek(-7)">上一周</button>
      <button class="button-secondary" type="button" @click="weekStart = getNaturalWeekStart()">本周</button>
      <button class="button-secondary" type="button" @click="changeWeek(7)">下一周</button>
    </div>

    <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>
    <div v-if="copyResult" class="copy-result" role="status">
      <strong>复制完成：新建 {{ copyResult.created.length }} 节，冲突 {{ copyResult.conflicts.length }} 节</strong>
      <ul v-if="copyResult.conflicts.length"><li v-for="conflict in copyResult.conflicts" :key="`${conflict.sourceSessionId}-${conflict.targetStartAt}`">{{ new Date(conflict.targetStartAt).toLocaleString("zh-CN") }}：{{ conflict.reason }}</li></ul>
    </div>

    <CommonAsyncState :status="status" :empty="!visibleSessions.length" pending-text="正在加载周课表…" empty-text="本周暂无课次" :error-message="error?.statusMessage || '课表加载失败'" @retry="refresh">
      <div class="agenda">
        <section v-for="day in days" :key="day.date" class="agenda-day">
          <header><h3>{{ formatDay(day.date) }}</h3><span>{{ day.sessions.length }} 节</span></header>
          <div v-if="day.sessions.length" class="session-list">
            <article v-for="session in day.sessions" :key="session.id" class="session-card" :class="`session-card--${session.status}`">
              <div class="session-time"><strong>{{ formatTime(session.startAt) }}</strong><span>{{ formatTime(session.endAt) }}</span></div>
              <div class="session-main">
                <div class="session-title"><h4>{{ session.courseName }}</h4><span class="status-badge">{{ session.isFull && session.status === "published" ? "已满" : statusLabels[session.status] }}</span></div>
                <p>{{ session.coachName }} · {{ session.roomName }}</p>
                <p class="capacity">已约 {{ session.bookedCount }}/{{ session.capacity }} · 剩余 {{ session.remainingCapacity }}</p>
                <div v-if="isMember" class="member-booking-action">
                  <button
                    type="button"
                    :disabled="bookingSubmit.pending.value || !memberBookingAvailability(session).available"
                    @click="bookSession(session)"
                  >{{ bookingSessionId === session.id ? "预约中…" : memberBookingLabel(session) }}</button>
                </div>
                <div v-if="isAdmin || canOpenDetails" class="session-actions">
                  <button v-if="isAdmin" class="button-secondary" type="button" @click="openEdit(session)">编辑</button>
                  <button v-if="isAdmin && session.status === 'draft'" type="button" :disabled="actionId === session.id" @click="transition(session, 'publish')">发布</button>
                  <button v-if="isAdmin && session.status === 'published'" class="button-secondary" type="button" :disabled="actionId === session.id" @click="transition(session, 'pause')">暂停</button>
                  <button v-if="isAdmin && session.status === 'paused'" type="button" :disabled="actionId === session.id" @click="transition(session, 'resume')">恢复</button>
                  <NuxtLink v-if="canOpenDetails" class="detail-link" :to="`/sessions/${session.id}`">课次详情<span v-if="isAdmin"> / 取消 / 完成</span></NuxtLink>
                </div>
              </div>
            </article>
          </div>
          <p v-else class="day-empty">无课次</p>
        </section>
      </div>
    </CommonAsyncState>
  </section>

  <section v-if="isAdmin && showForm" class="panel">
    <div class="section-heading"><h2>{{ editingId ? "编辑课次" : "新建课次" }}</h2><button class="button-secondary" type="button" @click="showForm = false">关闭</button></div>
    <form class="form-grid" @submit.prevent="saveSession">
      <label>课程<select v-model="form.courseId" required><option v-for="course in catalog?.courses || []" :key="course.id" :value="course.id">{{ course.name }}</option></select></label>
      <label>教练<select v-model="form.coachProfileId" required><option v-for="coach in catalog?.coaches || []" :key="coach.id" :value="coach.id">{{ coach.name }}</option></select></label>
      <label>教室<select v-model="form.roomId" required><option v-for="room in catalog?.rooms || []" :key="room.id" :value="room.id">{{ room.name }}（最多 {{ room.capacity }} 人）</option></select></label>
      <label>容量<input v-model.number="form.capacity" type="number" min="1" max="500" required /></label>
      <label>开始时间<input v-model="form.startAt" type="datetime-local" required /></label>
      <label>结束时间<input v-model="form.endAt" type="datetime-local" required /></label>
      <label>提前开放预约（小时）<input v-model.number="form.bookingOpenHoursBefore" type="number" min="0" required /></label>
      <label>课前停止预约（分钟）<input v-model.number="form.bookingCloseMinutesBefore" type="number" min="0" required /></label>
      <label>课前停止取消（分钟）<input v-model.number="form.cancelCutoffMinutesBefore" type="number" min="0" required /></label>
      <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存课次" }}</button><button class="button-secondary" type="button" @click="showForm = false">取消</button></div>
    </form>
  </section>
</template>

<style scoped>
.schedule-heading { align-items: flex-start; }
.link-button { display: inline-flex; align-items: center; padding: 9px 12px; border: 1px solid var(--border); border-radius: 10px; }
.week-toolbar { display: flex; justify-content: center; gap: .5rem; margin: .5rem 0 1rem; }
.copy-result { margin-bottom: 1rem; padding: .75rem 1rem; border: 1px solid #b7d3aa; border-radius: 10px; background: #f3faef; }
.copy-result ul { margin: .5rem 0 0; padding-left: 1.25rem; color: var(--muted); }
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
.agenda { display: grid; grid-template-columns: repeat(7, minmax(190px, 1fr)); gap: .75rem; overflow-x: auto; padding-bottom: .25rem; }
.agenda-day { min-width: 0; padding: .75rem; border: 1px solid var(--border); border-radius: 12px; background: #faf8f4; }
.agenda-day > header { display: flex; justify-content: space-between; gap: .5rem; padding-bottom: .65rem; border-bottom: 1px solid var(--border); }
.agenda-day h3, .agenda-day header span, .session-card p, .session-card h4 { margin: 0; }
.agenda-day h3 { font-size: .95rem; }
.agenda-day header span, .day-empty { color: var(--muted); font-size: .8rem; }
.session-list { display: grid; gap: .65rem; margin-top: .65rem; }
.session-card { display: grid; gap: .65rem; padding: .75rem; border-left: 4px solid var(--brand); border-radius: 9px; background: #fff; box-shadow: 0 2px 8px rgb(31 41 55 / 6%); }
.session-card--draft { border-left-color: #94a3b8; }
.session-card--paused { border-left-color: #d69e2e; }
.session-card--cancelled, .session-card--completed { border-left-color: #64748b; opacity: .72; }
.session-time { display: flex; align-items: baseline; gap: .35rem; }
.session-time strong { font-size: 1.05rem; }
.session-time span { color: var(--muted); font-size: .8rem; }
.session-title { display: flex; align-items: flex-start; justify-content: space-between; gap: .35rem; }
.session-main { display: grid; gap: .45rem; }
.session-main > p { color: var(--muted); font-size: .85rem; }
.session-main .capacity { color: var(--ink); }
.session-actions { display: flex; flex-wrap: wrap; gap: .35rem; padding-top: .25rem; }
.session-actions button { padding: .4rem .6rem; font-size: .78rem; }
.member-booking-action button { width: 100%; padding: .5rem .65rem; font-size: .8rem; }
.detail-link { align-self: center; color: var(--brand); font-size: .78rem; font-weight: 600; }
.day-empty { margin: 1rem 0 .25rem; text-align: center; }
@media (max-width: 1200px) { .agenda { grid-template-columns: repeat(2, minmax(260px, 1fr)); overflow: visible; } }
@media (max-width: 640px) { .schedule-heading, .schedule-heading .actions { align-items: stretch; flex-direction: column; } .week-toolbar { display: grid; grid-template-columns: repeat(3, 1fr); } .agenda { grid-template-columns: 1fr; } .agenda-day { padding: .65rem; } }
</style>
