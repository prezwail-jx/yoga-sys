<script setup lang="ts">
import type { AccountBindingInput, Member, MemberInput, MemberStatus, PasswordResetInput } from "~/types/domain"
import { accountOpeningError, isUsernameConflict, memberAccountPresentation, passwordValidationError, wechatBindingPresentation } from "~/utils/accountManagement"
import { getApiErrorMessage } from "~/utils/errors"
import { memberCardStatusLabels, memberStatusLabels } from "~/utils/labels"

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
const successMessage = ref("")
const accountTarget = ref<Member | null>(null)
const accountSubmit = useIdempotentSubmit()
const accountForm = reactive<AccountBindingInput>({ username: "", initialPassword: "" })
const resetForm = reactive<PasswordResetInput>({ newPassword: "" })
const resetConfirmation = ref("")
const wechatBound = ref(false)
const wechatLoading = ref(false)
const confirmUnbind = ref(false)

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

function openAccount(member: Member) {
  errorMessage.value = ""
  successMessage.value = ""
  accountTarget.value = member
  accountForm.username = ""
  accountForm.initialPassword = ""
  resetForm.newPassword = ""
  resetConfirmation.value = ""
  wechatBound.value = false
  confirmUnbind.value = false
  if (member.hasAccount && member.accountId) {
    loadWechatBindingStatus(member.accountId)
  }
}

async function loadWechatBindingStatus(accountId: string) {
  wechatLoading.value = true
  try {
    const status = await api.getWechatBindingStatus(accountId)
    wechatBound.value = status.bound
  } catch {
    wechatBound.value = false
  } finally {
    wechatLoading.value = false
  }
}

async function unbindWechatAccount() {
  if (!accountTarget.value?.accountId) return
  const accountId = accountTarget.value.accountId
  pending.value = true
  errorMessage.value = ""
  successMessage.value = ""
  try {
    await api.unbindWechat(accountId)
    wechatBound.value = false
    confirmUnbind.value = false
    successMessage.value = `已解除 ${accountTarget.value.name} 的微信绑定。`
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "微信解绑失败，请确认该账号已绑定微信")
  } finally {
    pending.value = false
  }
}

async function createAccount() {
  if (!accountTarget.value) return
  errorMessage.value = ""
  successMessage.value = ""
  const member = accountTarget.value
  try {
    const binding = await accountSubmit.submit(
      `member-account:${member.id}:${accountForm.username}`,
      key => api.createMemberAccount(member.id, { ...accountForm }, key),
    )
    accountSubmit.reset()
    accountTarget.value = null
    successMessage.value = `已为 ${member.name} 开通账号 ${binding.username}`
    await refresh()
  } catch (error: unknown) {
    errorMessage.value = isUsernameConflict(error) ? accountOpeningError(error, "会员") : getApiErrorMessage(error, "会员账号开通失败")
  }
}

async function resetPassword() {
  if (!accountTarget.value) return
  errorMessage.value = passwordValidationError(resetForm.newPassword, resetConfirmation.value)
  successMessage.value = ""
  if (errorMessage.value) return
  pending.value = true
  const member = accountTarget.value
  try {
    await api.resetMemberPassword(member.id, { ...resetForm })
    accountTarget.value = null
    successMessage.value = `已重置 ${member.name} 的登录密码，新密码立即生效。`
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "密码重置失败，请确认该会员已开通账号")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="panel">
    <div class="section-heading">
      <div>
        <h2>会员列表</h2>
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
    <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>
    <CommonAsyncState :status="status" :empty="!data?.items.length" pending-text="正在加载会员…" empty-text="暂无符合条件的会员" :error-message="error?.statusMessage || '会员加载失败'" @retry="refresh">
    <div class="table-wrap">
      <table>
        <thead><tr><th>姓名</th><th>手机号</th><th>状态</th><th>持有卡项</th><th>账号状态</th><th>入会日期</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="member in data?.items || []" :key="member.id">
            <td>{{ member.name }}</td>
            <td>{{ member.phone }}</td>
            <td><span class="status-badge">{{ memberStatusLabels[member.status] }}</span></td>
            <td>
              <div v-if="member.cardSummaries?.length" class="card-summary-list">
                <div v-for="card in member.cardSummaries" :key="card.id" :class="['card-summary', { 'is-muted': card.status === 'expired' || card.status === 'closed' }]">
                  <strong>{{ card.productName }}</strong>
                  <span>{{ memberCardStatusLabels[card.status] }} · {{ card.remainingTimes === null ? "不限次" : `剩余 ${card.remainingTimes} 次` }} · {{ card.expiresOn ? `${card.expiresOn} 到期` : "暂无到期日" }}</span>
                </div>
              </div>
              <span v-else class="hint">暂无卡项</span>
            </td>
            <td>
              <div class="account-status">
                <span :class="['account-badge', member.hasAccount ? 'is-open' : 'is-closed']">{{ memberAccountPresentation(member.hasAccount).label }}</span>
                <span v-if="member.username" class="account-username">{{ member.username }}</span>
              </div>
            </td>
            <td>{{ member.joinDate }}</td>
            <td class="actions primary-actions">
              <button type="button" @click="openAccount(member)">业务管理</button>
              <NuxtLink class="button-primary record-link" :to="{ path: '/transactions', query: { memberId: member.id } }">管理卡项</NuxtLink>
              <NuxtLink class="button-primary record-link" :to="`/members/${member.id}/timeline`">业务记录</NuxtLink>
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

  <section v-if="accountTarget" class="panel account-panel" aria-labelledby="member-management-title">
    <div class="section-heading">
      <div><h2 id="member-management-title">{{ accountTarget.name }} · 业务管理</h2><p class="hint">管理会员资料、状态和登录账号，不影响既有业务记录。</p></div>
      <button class="button-secondary" type="button" :disabled="accountSubmit.pending.value || pending" @click="accountTarget = null">关闭</button>
    </div>
    <div class="management-actions">
      <button class="button-secondary" type="button" @click="openEdit(accountTarget); accountTarget = null">编辑资料</button>
      <button v-if="accountTarget.status === 'normal'" class="button-secondary" type="button" @click="changeStatus(accountTarget, 'paused'); accountTarget = null">暂停会员</button>
      <button v-if="accountTarget.status === 'paused'" class="button-secondary" type="button" @click="changeStatus(accountTarget, 'normal'); accountTarget = null">恢复会员</button>
      <button v-if="accountTarget.status === 'disabled'" type="button" @click="changeStatus(accountTarget, 'normal'); accountTarget = null">重新启用</button>
      <button v-else class="button-danger" type="button" @click="changeStatus(accountTarget, 'disabled'); accountTarget = null">禁用会员</button>
      <button class="button-danger button-subtle-danger" type="button" @click="removeMember(accountTarget); accountTarget = null">归档会员</button>
    </div>
    <form v-if="!accountTarget.hasAccount" class="form-grid account-form" @submit.prevent="createAccount">
      <div class="full-width"><h3>开通登录账号</h3><p class="uniqueness-note">用户名在会员、教练和管理员账号中全局唯一，开通后初始密码不会回显。</p></div>
      <label>用户名<input v-model="accountForm.username" autocomplete="off" required minlength="3" maxlength="64" /></label>
      <label>初始密码<input v-model="accountForm.initialPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      <div class="full-width form-actions"><button type="submit" :disabled="accountSubmit.pending.value">{{ accountSubmit.pending.value ? "开通中…" : "确认开通" }}</button></div>
    </form>
    <form v-else class="form-grid account-form" @submit.prevent="resetPassword">
      <div class="full-width"><h3>重置登录密码</h3><p class="hint">账号 {{ accountTarget.username }}，提交后旧密码立即失效。</p></div>
      <label>新密码<input v-model="resetForm.newPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      <label>确认新密码<input v-model="resetConfirmation" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      <div class="full-width form-actions"><button type="submit" :disabled="pending">{{ pending ? "重置中…" : "确认重置" }}</button></div>
    </form>
    <div v-if="accountTarget.hasAccount" class="wechat-binding-section">
      <div class="section-heading">
        <div><h3>微信绑定</h3><p class="hint">{{ wechatBindingPresentation(wechatBound).description }}</p></div>
      </div>
      <div class="wechat-status">
        <span :class="['account-badge', wechatBound ? 'is-open' : 'is-closed']">{{ wechatBindingPresentation(wechatBound).label }}</span>
      </div>
      <div v-if="wechatBound && !confirmUnbind" class="form-actions">
        <button class="button-danger" type="button" @click="confirmUnbind = true">解除微信绑定</button>
      </div>
      <div v-if="wechatBound && confirmUnbind" class="unbind-confirm">
        <p class="warning-text">确认解除 {{ accountTarget.name }} 的微信绑定？该身份将不能再通过微信登录，但已签发的短期令牌在使用期限内仍然有效。</p>
        <div class="form-actions">
          <button class="button-danger" type="button" :disabled="pending" @click="unbindWechatAccount">{{ pending ? "解绑中…" : "确认解除" }}</button>
          <button class="button-secondary" type="button" @click="confirmUnbind = false">取消</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
.account-panel { border-top: 4px solid var(--brand); }
.account-status { display: grid; gap: 4px; justify-items: start; }
.account-badge { display: inline-flex; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.account-badge.is-open { color: #174e91; background: #e6f0ff; border: 1px solid #a9c9f7; }
.account-badge.is-closed { color: #59636e; background: #eef0f2; border: 1px solid #d3d7dc; }
.account-username { color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }
.card-summary-list { display: grid; gap: 6px; min-width: 220px; }
.card-summary { display: grid; gap: 2px; padding: 7px 9px; border: 1px solid var(--border); border-radius: 8px; background: #f8fbf9; }
.card-summary strong { font-size: 13px; }
.card-summary span { color: var(--muted); font-size: 12px; white-space: nowrap; }
.card-summary.is-muted { opacity: .58; background: #f2f2f2; }
.button-primary { display: inline-flex; align-items: center; padding: 9px 14px; color: #fff; background: var(--brand); border-radius: 10px; text-decoration: none; }
.primary-actions { flex-wrap: nowrap; }
.management-actions { display: flex; flex-wrap: wrap; gap: 8px; padding-bottom: 18px; border-bottom: 1px solid var(--border); }
.account-form { margin-top: 18px; }
.account-form h3, .account-form p { margin: 0; }
.uniqueness-note { margin-top: 6px !important; color: #6f4a12; font-weight: 600; }
.button-subtle-danger { opacity: .8; }
.wechat-binding-section { margin-top: 18px; border-top: 1px solid var(--border); padding-top: 18px; }
.wechat-binding-section h3 { margin: 0 0 4px; }
.wechat-status { margin: 8px 0 12px; }
.unbind-confirm { margin-top: 12px; padding: 12px; background: #fff3f0; border: 1px solid #f5c6cb; border-radius: 8px; }
.warning-text { color: #a71d2a; font-weight: 600; margin: 0 0 8px; }
@media (max-width: 760px) { .primary-actions { flex-direction: column; align-items: stretch; } .primary-actions > * { justify-content: center; text-align: center; } }
</style>
