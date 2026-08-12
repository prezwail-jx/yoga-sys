<script setup lang="ts">
import { label, userRoleLabels } from "~/utils/labels"
const { user, logout } = useAuth()
</script>

<template>
  <section class="panel empty-state">
    <h2>没有管理权限</h2>
    <p>当前账号 {{ user?.username }}（{{ label(userRoleLabels, user?.role) || user?.role }}）不能修改会员或卡项。</p>
    <button type="button" @click="logout">返回登录</button>
  </section>
</template>
