<script setup lang="ts">
import { getApiErrorMessage } from "~/utils/errors"

definePageMeta({ layout: false })

const { login } = useAuth()
const username = ref("admin")
const password = ref("admin123")
const pending = ref(false)
const errorMessage = ref("")

async function submit() {
  pending.value = true
  errorMessage.value = ""
  try {
    const user = await login(username.value, password.value)
    await navigateTo(user.role === "admin" ? "/members" : "/forbidden")
  } catch (error: unknown) {
    errorMessage.value = getApiErrorMessage(error, "登录失败")
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <main class="login-shell">
    <form class="login-card" @submit.prevent="submit">
      <p class="eyebrow">Yoga SYS</p>
      <h1>登录运营中台</h1>
      <label>用户名<input v-model="username" autocomplete="username" required /></label>
      <label>密码<input v-model="password" type="password" autocomplete="current-password" required /></label>
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <button type="submit" :disabled="pending">{{ pending ? "登录中…" : "登录" }}</button>
      <p class="hint">本地开发：管理员 admin/admin123，教练 coach/coach123。</p>
    </form>
  </main>
</template>
