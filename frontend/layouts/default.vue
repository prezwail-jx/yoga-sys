<script setup lang="ts">
const { user, logout } = useAuth()
const menu = [
  { to: "/", label: "运营看板", mock: true },
  { to: "/members", label: "会员管理", mock: false },
  { to: "/cards", label: "卡项管理", mock: false },
  { to: "/transactions", label: "卡项办理", mock: false },
  { to: "/schedule", label: "团课课表", mock: true },
  { to: "/private-training", label: "私教预约", mock: true },
  { to: "/reports", label: "统计报表", mock: true },
]
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar">
      <div class="brand">Yoga SYS</div>
      <p class="brand-sub">会员约课与运营中台</p>
      <nav class="menu-list">
        <NuxtLink v-for="item in menu" :key="item.to" :to="item.to" class="menu-link">
          {{ item.label }} <small v-if="item.mock">Mock</small>
        </NuxtLink>
      </nav>
    </aside>

    <main class="app-main">
      <header class="top-header">
        <div>
          <h1>瑜伽馆会员管理系统</h1>
          <p>会员与卡项已接入真实服务；标记 Mock 的模块仍为演示数据。</p>
        </div>
        <div v-if="user" class="user-actions">
          <span>{{ user.username }} · {{ user.role }}</span>
          <button class="button-secondary" type="button" @click="logout">退出</button>
        </div>
      </header>
      <slot />
    </main>
  </div>
</template>
