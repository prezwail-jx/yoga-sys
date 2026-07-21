<script setup lang="ts">
import type { AccountBindingInput, CoachProfile, CoachProfileInput, Course, CourseDifficulty, CourseInput, Room, RoomInput } from "~/types/domain"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-admin" })

const api = useGymApi()
const keyword = ref("")
const pending = ref(false)
const errorMessage = ref("")
const successMessage = ref("")
const courseEditingId = ref<string | null>(null)
const roomEditingId = ref<string | null>(null)
const coachEditingId = ref<string | null>(null)
const showCourseForm = ref(false)
const showRoomForm = ref(false)
const showCoachForm = ref(false)
const accountTarget = ref<CoachProfile | null>(null)
const accountSubmit = useIdempotentSubmit()
const accountForm = reactive<AccountBindingInput>({ username: "", initialPassword: "" })
const boundCoachIds = ref(new Set<string>())

const newCourse = (): CourseInput => ({ name: "", durationMinutes: 60, difficulty: "all_levels", description: "", coverUrl: null, enabled: true })
const newRoom = (): RoomInput => ({ name: "", capacity: 20, enabled: true })
const newCoach = (): CoachProfileInput => ({ name: "", avatarUrl: null, bio: "", specialtyCourseIds: [], enabled: true })
const courseForm = reactive<CourseInput>(newCourse())
const roomForm = reactive<RoomInput>(newRoom())
const coachForm = reactive<CoachProfileInput>(newCoach())

const { data, refresh, status, error } = await useAsyncData("class-catalog", async () => {
  const [courses, rooms, coaches] = await Promise.all([
    api.getCourses({ limit: 100 }),
    api.getRooms({ limit: 100 }),
    api.getCoaches({ limit: 100 }),
  ])
  return { courses, rooms, coaches }
})

const matches = (value: string) => value.toLocaleLowerCase().includes(keyword.value.trim().toLocaleLowerCase())
const filteredCourses = computed(() => (data.value?.courses.items || []).filter(item => matches(`${item.name} ${item.description || ""}`)))
const filteredRooms = computed(() => (data.value?.rooms.items || []).filter(item => matches(item.name)))
const filteredCoaches = computed(() => (data.value?.coaches.items || []).filter(item => matches(`${item.name} ${item.bio || ""}`)))

const difficultyLabels: Record<CourseDifficulty, string> = {
  all_levels: "不限基础",
  beginner: "初级",
  intermediate: "中级",
  advanced: "高级",
}

function openCourse(course?: Course) {
  courseEditingId.value = course?.id || null
  Object.assign(courseForm, course ? {
    name: course.name,
    durationMinutes: course.durationMinutes,
    difficulty: course.difficulty,
    description: course.description,
    coverUrl: course.coverUrl,
    enabled: course.enabled,
  } : newCourse())
  showCourseForm.value = true
}

function openRoom(room?: Room) {
  roomEditingId.value = room?.id || null
  Object.assign(roomForm, room ? { name: room.name, capacity: room.capacity, enabled: room.enabled } : newRoom())
  showRoomForm.value = true
}

function openCoach(coach?: CoachProfile) {
  coachEditingId.value = coach?.id || null
  Object.assign(coachForm, coach ? {
    name: coach.name,
    avatarUrl: coach.avatarUrl,
    bio: coach.bio,
    specialtyCourseIds: [...(coach.specialtyCourseIds || [])],
    enabled: coach.enabled,
  } : newCoach())
  showCoachForm.value = true
}

async function runMutation(action: () => Promise<unknown>, close?: () => void) {
  pending.value = true
  errorMessage.value = ""
  try {
    await action()
    close?.()
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "操作失败")
  } finally {
    pending.value = false
  }
}

async function saveCourse() {
  await runMutation(
    () => courseEditingId.value ? api.updateCourse(courseEditingId.value, courseForm) : api.createCourse(courseForm),
    () => { showCourseForm.value = false },
  )
}

async function saveRoom() {
  await runMutation(
    () => roomEditingId.value ? api.updateRoom(roomEditingId.value, roomForm) : api.createRoom(roomForm),
    () => { showRoomForm.value = false },
  )
}

async function saveCoach() {
  await runMutation(
    () => coachEditingId.value ? api.updateCoach(coachEditingId.value, coachForm) : api.createCoach(coachForm),
    () => { showCoachForm.value = false },
  )
}

function openCoachAccount(coach: CoachProfile) {
  errorMessage.value = ""
  successMessage.value = ""
  accountTarget.value = coach
  accountForm.username = ""
  accountForm.initialPassword = ""
}

async function createCoachAccount() {
  if (!accountTarget.value) return
  errorMessage.value = ""
  successMessage.value = ""
  const coach = accountTarget.value
  try {
    const binding = await accountSubmit.submit(
      `coach-account:${coach.id}:${accountForm.username}`,
      key => api.createCoachAccount(coach.id, { ...accountForm }, key),
    )
    accountSubmit.reset()
    boundCoachIds.value = new Set([...boundCoachIds.value, coach.id])
    accountTarget.value = null
    successMessage.value = `已为 ${coach.name} 开通账号 ${binding.username}`
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "教练账号开通失败")
  }
}
</script>

<template>
  <div class="catalog-header">
    <div>
      <h1>团课基础资料</h1>
      <p class="hint">维护排课使用的课程、教室和教练，不包含账号开户。</p>
    </div>
    <input v-model="keyword" aria-label="搜索基础资料" placeholder="搜索名称或简介" />
  </div>

  <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
  <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>
  <CommonAsyncState :status="status" :error-message="error?.statusMessage || '基础资料加载失败'" @retry="refresh">
    <section class="panel">
      <div class="section-heading">
        <div><h2>课程</h2><p class="hint">{{ filteredCourses.length }} 项</p></div>
        <button type="button" @click="openCourse()">新增课程</button>
      </div>
      <div class="catalog-grid">
        <article v-for="course in filteredCourses" :key="course.id" class="catalog-card">
          <div class="card-title"><strong>{{ course.name }}</strong><span class="status-badge">{{ course.enabled ? "启用" : "停用" }}</span></div>
          <p>{{ difficultyLabels[course.difficulty] }} · {{ course.durationMinutes }} 分钟</p>
          <p class="description">{{ course.description || "暂无简介" }}</p>
          <div class="actions">
            <button class="button-secondary" type="button" @click="openCourse(course)">编辑</button>
            <button :class="course.enabled ? 'button-danger' : 'button-secondary'" type="button" :disabled="pending" @click="runMutation(() => api.updateCourse(course.id, { enabled: !course.enabled }))">{{ course.enabled ? "停用" : "启用" }}</button>
          </div>
        </article>
        <p v-if="!filteredCourses.length" class="empty-state">暂无符合条件的课程</p>
      </div>
      <form v-if="showCourseForm" class="form-grid catalog-form" @submit.prevent="saveCourse">
        <h3 class="full-width">{{ courseEditingId ? "编辑课程" : "新增课程" }}</h3>
        <label>课程名称<input v-model="courseForm.name" required maxlength="100" /></label>
        <label>时长（分钟）<input v-model.number="courseForm.durationMinutes" type="number" min="1" max="600" required /></label>
        <label>难度<select v-model="courseForm.difficulty"><option v-for="(label, value) in difficultyLabels" :key="value" :value="value">{{ label }}</option></select></label>
        <label>封面 URL<input v-model="courseForm.coverUrl" type="url" placeholder="可选" /></label>
        <label class="full-width">简介<textarea v-model="courseForm.description" rows="3" /></label>
        <label class="checkbox-label"><input v-model="courseForm.enabled" type="checkbox" /> 启用</label>
        <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存" }}</button><button class="button-secondary" type="button" @click="showCourseForm = false">取消</button></div>
      </form>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div><h2>教室</h2><p class="hint">{{ filteredRooms.length }} 项</p></div>
        <button type="button" @click="openRoom()">新增教室</button>
      </div>
      <div class="catalog-grid compact-grid">
        <article v-for="room in filteredRooms" :key="room.id" class="catalog-card">
          <div class="card-title"><strong>{{ room.name }}</strong><span class="status-badge">{{ room.enabled ? "启用" : "停用" }}</span></div>
          <p>最多容纳 {{ room.capacity }} 人</p>
          <div class="actions"><button class="button-secondary" type="button" @click="openRoom(room)">编辑</button><button :class="room.enabled ? 'button-danger' : 'button-secondary'" type="button" :disabled="pending" @click="runMutation(() => api.updateRoom(room.id, { enabled: !room.enabled }))">{{ room.enabled ? "停用" : "启用" }}</button></div>
        </article>
        <p v-if="!filteredRooms.length" class="empty-state">暂无符合条件的教室</p>
      </div>
      <form v-if="showRoomForm" class="form-grid catalog-form" @submit.prevent="saveRoom">
        <h3 class="full-width">{{ roomEditingId ? "编辑教室" : "新增教室" }}</h3>
        <label>教室名称<input v-model="roomForm.name" required maxlength="100" /></label>
        <label>容量<input v-model.number="roomForm.capacity" type="number" min="1" max="500" required /></label>
        <label class="checkbox-label"><input v-model="roomForm.enabled" type="checkbox" /> 启用</label>
        <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存" }}</button><button class="button-secondary" type="button" @click="showRoomForm = false">取消</button></div>
      </form>
    </section>

    <section class="panel">
      <div class="section-heading">
        <div><h2>教练</h2><p class="hint">{{ filteredCoaches.length }} 项</p></div>
        <button type="button" @click="openCoach()">新增教练</button>
      </div>
      <div class="catalog-grid">
        <article v-for="coach in filteredCoaches" :key="coach.id" class="catalog-card">
          <div class="card-title"><strong>{{ coach.name }}</strong><span class="status-badge">{{ coach.enabled ? "启用" : "停用" }}</span></div>
          <p class="description">{{ coach.bio || "暂无简介" }}</p>
          <p>擅长课程：{{ coach.specialtyCourseIds?.length || 0 }} 项</p>
          <div class="actions"><button class="button-secondary" type="button" @click="openCoach(coach)">编辑</button><button class="button-secondary" type="button" :disabled="!coach.enabled || boundCoachIds.has(coach.id)" @click="openCoachAccount(coach)">{{ boundCoachIds.has(coach.id) ? "账号已开通" : "开通账号" }}</button><button :class="coach.enabled ? 'button-danger' : 'button-secondary'" type="button" :disabled="pending" @click="runMutation(() => api.updateCoach(coach.id, { enabled: !coach.enabled }))">{{ coach.enabled ? "停用" : "启用" }}</button></div>
        </article>
        <p v-if="!filteredCoaches.length" class="empty-state">暂无符合条件的教练</p>
      </div>
      <form v-if="showCoachForm" class="form-grid catalog-form" @submit.prevent="saveCoach">
        <h3 class="full-width">{{ coachEditingId ? "编辑教练" : "新增教练" }}</h3>
        <label>姓名<input v-model="coachForm.name" required maxlength="100" /></label>
        <label>头像 URL<input v-model="coachForm.avatarUrl" type="url" placeholder="可选" /></label>
        <label class="full-width">简介<textarea v-model="coachForm.bio" rows="3" /></label>
        <fieldset class="full-width specialty-field"><legend>擅长课程</legend><label v-for="course in data?.courses.items || []" :key="course.id" class="checkbox-label"><input v-model="coachForm.specialtyCourseIds" type="checkbox" :value="course.id" /> {{ course.name }}</label></fieldset>
        <label class="checkbox-label"><input v-model="coachForm.enabled" type="checkbox" /> 启用</label>
        <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存" }}</button><button class="button-secondary" type="button" @click="showCoachForm = false">取消</button></div>
      </form>
    </section>

    <section v-if="accountTarget" class="panel account-panel">
      <div class="section-heading"><div><h2>为 {{ accountTarget.name }} 开通教练账号</h2><p class="hint">账号将唯一绑定该教练档案，停用教练后不可登录。</p></div><button class="button-secondary" type="button" :disabled="accountSubmit.pending.value" @click="accountTarget = null">关闭</button></div>
      <form class="form-grid" @submit.prevent="createCoachAccount">
        <label>用户名<input v-model="accountForm.username" autocomplete="off" required minlength="3" maxlength="64" /></label>
        <label>初始密码<input v-model="accountForm.initialPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
        <div class="full-width form-actions"><button type="submit" :disabled="accountSubmit.pending.value">{{ accountSubmit.pending.value ? "开通中…" : "确认开通" }}</button></div>
      </form>
    </section>
  </CommonAsyncState>
</template>

<style scoped>
.catalog-header { display: flex; align-items: end; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; }
.catalog-header h1, .catalog-header p, .catalog-card p { margin: 0; }
.catalog-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: .75rem; }
.compact-grid { grid-template-columns: repeat(auto-fit, minmax(200px, 280px)); }
.catalog-card { display: grid; gap: .75rem; padding: 1rem; border: 1px solid var(--border); border-radius: 12px; background: #fffcf8; }
.card-title { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
.description { min-height: 2.5rem; color: var(--muted); }
.catalog-form { margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border); }
.catalog-form h3 { margin: 0; }
.specialty-field { display: flex; flex-wrap: wrap; gap: .75rem 1rem; margin: 0; border: 1px solid var(--border); border-radius: 10px; }
.specialty-field legend { color: var(--muted); font-size: 13px; }
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
.account-panel { border-top: 4px solid var(--brand); }
@media (max-width: 640px) { .catalog-header { align-items: stretch; flex-direction: column; } .catalog-grid, .compact-grid { grid-template-columns: 1fr; } }
</style>
