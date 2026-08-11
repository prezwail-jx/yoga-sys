<script setup lang="ts">
import type { NavigationGroup } from "~/utils/navigation"
import { isNavigationItemActive } from "~/utils/navigation"

defineProps<{
  groups: NavigationGroup[]
  currentPath: string
  username?: string
  role?: string
  mobile?: boolean
}>()

const emit = defineEmits<{ close: []; logout: [] }>()
</script>

<template>
  <aside :class="['app-sidebar', { 'is-mobile': mobile }]">
    <div class="sidebar-brand-row">
      <div>
        <div class="brand">Yoga SYS</div>
        <p class="brand-sub">会员约课与运营中台</p>
      </div>
      <button v-if="mobile" class="sidebar-close" type="button" aria-label="关闭导航" @click="emit('close')">
        <UIcon name="i-lucide-x" />
      </button>
    </div>

    <nav class="menu-list" aria-label="主导航">
      <section v-for="group in groups" :key="group.label" class="menu-group">
        <p class="menu-group-label">{{ group.label }}</p>
        <NuxtLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          :class="['menu-link', { 'is-active': isNavigationItemActive(item, currentPath) }]"
          @click="emit('close')"
        >
          <UIcon :name="item.icon" class="menu-icon" />
          <span>{{ item.label }}</span>
          <small v-if="item.mock" class="mock-badge">Mock</small>
        </NuxtLink>
      </section>
    </nav>

    <div v-if="username" class="sidebar-account">
      <div class="account-avatar">{{ username.slice(0, 1).toUpperCase() }}</div>
      <div class="account-copy"><strong>{{ username }}</strong><span>{{ role }}</span></div>
      <button class="sidebar-logout" type="button" aria-label="退出登录" @click="emit('logout')"><UIcon name="i-lucide-log-out" /></button>
    </div>
  </aside>
</template>
