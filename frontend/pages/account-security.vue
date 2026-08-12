<script setup lang="ts">
import type { ChangePasswordInput } from "~/types/domain"
import { passwordValidationError } from "~/utils/accountManagement"
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ middleware: "require-account-user" })

const api = useGymApi()
const form = reactive<ChangePasswordInput>({ oldPassword: "", newPassword: "" })
const confirmation = ref("")
const pending = ref(false)
const errorMessage = ref("")
const successMessage = ref("")

async function submit() {
  errorMessage.value = passwordValidationError(form.newPassword, confirmation.value)
  successMessage.value = ""
  if (errorMessage.value) return
  pending.value = true
  try {
    await api.changePassword({ ...form })
    form.oldPassword = ""
    form.newPassword = ""
    confirmation.value = ""
    successMessage.value = "密码修改成功。下次登录请使用新密码。"
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "密码修改失败，请检查旧密码后重试")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <section class="panel security-panel">
    <div class="security-heading">
      <p class="eyebrow">账号安全</p>
      <h2>修改登录密码</h2>
      <p class="hint">验证当前密码后设置新密码。新密码至少 8 位，修改成功后旧密码立即失效。</p>
    </div>
    <p v-if="errorMessage" class="error-message" role="alert">{{ errorMessage }}</p>
    <p v-if="successMessage" class="success-message" role="status">{{ successMessage }}</p>
    <form class="password-form" @submit.prevent="submit">
      <label>旧密码<input v-model="form.oldPassword" type="password" autocomplete="current-password" required maxlength="128" /></label>
      <label>新密码<input v-model="form.newPassword" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      <label>确认新密码<input v-model="confirmation" type="password" autocomplete="new-password" required minlength="8" maxlength="128" /></label>
      <button type="submit" :disabled="pending">{{ pending ? "修改中…" : "确认修改密码" }}</button>
    </form>
  </section>
</template>

<style scoped>
.security-panel { width: min(640px, 100%); margin-inline: auto; border-top: 4px solid var(--brand); }
.security-heading { margin-bottom: 20px; }
.security-heading h2 { margin: 4px 0 8px; }
.security-heading p { margin-top: 0; }
.eyebrow { color: var(--brand); font-size: 12px; font-weight: 700; text-transform: uppercase; }
.password-form { display: grid; gap: 14px; }
.password-form label { display: grid; gap: 6px; color: var(--muted); font-size: 13px; }
.password-form input { width: 100%; }
.password-form button { justify-self: start; margin-top: 4px; }
.success-message { padding: 10px 12px; color: #37622a; background: #f0f9ec; border-radius: 8px; }
@media (max-width: 640px) { .password-form button { width: 100%; } }
</style>
