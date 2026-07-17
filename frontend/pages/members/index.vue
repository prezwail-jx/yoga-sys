<script setup lang="ts">
import type { Member, MemberInput, MemberStatus } from "~/types/domain"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-admin" })

const api = useGymApi()
const keyword = ref("")
const statusFilter = ref<MemberStatus | "">("")
const skip = ref(0)
const limit = 20
const showForm = ref(false)
const editingId = ref<string | null>(null)
const pending = ref(false)
const errorMessage = ref("")

const newForm = (): MemberInput => ({
  name: "",
  phone: "",
  joinDate: new Date().toISOString().slice(0, 10),
  gender: null,
  birthday: null,
  note: "",
  emergencyContact: "",
})
const form = reactive<MemberInput>(newForm())

const { data, refresh, status, error } = await useAsyncData(
  "real-members",
  () => api.getMembers({
    keyword: keyword.value || undefined,
    status: statusFilter.value || undefined,
    skip: skip.value,
    limit,
  }),
  { watch: [skip] },
)

function openCreate() {
  editingId.value = null
  Object.assign(form, newForm())
  showForm.value = true
}

function openEdit(member: Member) {
  editingId.value = member.id
  Object.assign(form, {
    name: member.name,
    phone: member.phone,
    joinDate: member.joinDate,
    gender: member.gender,
    birthday: member.birthday,
    note: member.note,
    emergencyContact: member.emergencyContact,
  })
  showForm.value = true
}

async function searchMembers() {
  skip.value = 0
  await refresh()
}

async function saveMember() {
  pending.value = true
  errorMessage.value = ""
  try {
    if (editingId.value) {
      await api.updateMember(editingId.value, {
        name: form.name,
        gender: form.gender,
        birthday: form.birthday,
        note: form.note,
        emergencyContact: form.emergencyContact,
      })
    } else {
      await api.createMember(form)
    }
    showForm.value = false
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "保存失败")
  } finally {
    pending.value = false
  }
}

async function changeStatus(member: Member, nextStatus: MemberStatus) {
  errorMessage.value = ""
  try {
    await api.updateMember(member.id, { status: nextStatus })
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "状态修改失败")
  }
}

async function removeMember(member: Member) {
  if (!confirm(`确认归档会员“${member.name}”？历史记录会保留。`)) return
  await api.deleteMember(member.id)
  await refresh()
}
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div>
        <h2>会员管理</h2>
        <p class="hint">真实数据 · 共 {{ data?.total || 0 }} 位会员</p>
      </div>
      <button type="button" @click="openCreate">新增会员</button>
    </div>

    <div class="toolbar">
      <input v-model="keyword" placeholder="按姓名或手机号搜索" @keyup.enter="searchMembers" />
      <select v-model="statusFilter">
        <option value="">全部状态</option>
        <option value="normal">正常</option>
        <option value="paused">暂停</option>
        <option value="disabled">禁用</option>
        <option value="expired">到期</option>
      </select>
      <button type="button" @click="searchMembers">搜索</button>
    </div>

    <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    <CommonAsyncState :status="status" :empty="!data?.items.length" pending-text="正在加载会员…" empty-text="暂无符合条件的会员" :error-message="error?.statusMessage || '会员加载失败'" @retry="refresh">
    <div class="table-wrap">
      <table>
        <thead><tr><th>姓名</th><th>手机号</th><th>状态</th><th>入会日期</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="member in data?.items || []" :key="member.id">
            <td>{{ member.name }}</td>
            <td>{{ member.phone }}</td>
            <td><span class="status-badge">{{ member.status }}</span></td>
            <td>{{ member.joinDate }}</td>
            <td class="actions">
              <NuxtLink class="button-secondary record-link" :to="`/members/${member.id}/timeline`">业务记录</NuxtLink>
              <button class="button-secondary" type="button" @click="openEdit(member)">编辑</button>
              <button v-if="member.status === 'normal'" class="button-secondary" type="button" @click="changeStatus(member, 'paused')">暂停</button>
              <button v-if="member.status === 'paused'" class="button-secondary" type="button" @click="changeStatus(member, 'normal')">恢复</button>
              <button v-if="member.status !== 'disabled'" class="button-danger" type="button" @click="changeStatus(member, 'disabled')">禁用</button>
              <button class="button-danger" type="button" @click="removeMember(member)">归档</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    </CommonAsyncState>

    <div class="pagination">
      <button class="button-secondary" type="button" :disabled="skip === 0" @click="skip = Math.max(0, skip - limit)">上一页</button>
      <span>第 {{ Math.floor(skip / limit) + 1 }} 页</span>
      <button class="button-secondary" type="button" :disabled="skip + limit >= (data?.total || 0)" @click="skip += limit">下一页</button>
    </div>
  </section>

  <section v-if="showForm" class="panel">
    <div class="section-heading">
      <h2>{{ editingId ? "编辑会员" : "新增会员" }}</h2>
      <button class="button-secondary" type="button" @click="showForm = false">关闭</button>
    </div>
    <form class="form-grid" @submit.prevent="saveMember">
      <label>姓名<input v-model="form.name" required maxlength="50" /></label>
      <label>手机号<input v-model="form.phone" required :disabled="Boolean(editingId)" /></label>
      <label>入会日期<input v-model="form.joinDate" type="date" required :disabled="Boolean(editingId)" /></label>
      <label>性别
        <select v-model="form.gender">
          <option :value="null">未填写</option><option value="female">女</option><option value="male">男</option><option value="other">其他</option>
        </select>
      </label>
      <label>生日<input v-model="form.birthday" type="date" /></label>
      <label>紧急联系人<input v-model="form.emergencyContact" maxlength="100" /></label>
      <label class="full-width">备注<textarea v-model="form.note" rows="3" /></label>
      <div class="full-width form-actions">
        <button type="submit" :disabled="pending">{{ pending ? "保存中…" : "保存" }}</button>
      </div>
    </form>
  </section>
</template>
