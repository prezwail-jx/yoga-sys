<script setup lang="ts">
const { user, logout } = useAuth()
const route = useRoute()
const mobileOpen = ref(false)
const groups = computed(() => getNavigationGroups(user.value?.role))
const pageContext = computed(() => getPageContext(route.path, user.value?.role))

watch(() => route.fullPath, () => { mobileOpen.value = false })
</script>

<template>
  <div class="app-shell">
    <NavigationAppSidebar :groups="groups" :current-path="route.path" :username="user?.username" :role="user?.role" @logout="logout" />

    <Transition name="drawer">
      <div v-if="mobileOpen" class="mobile-nav-layer" @click.self="mobileOpen = false">
        <NavigationAppSidebar mobile :groups="groups" :current-path="route.path" :username="user?.username" :role="user?.role" @close="mobileOpen = false" @logout="logout" />
      </div>
    </Transition>

    <main class="app-main">
      <NavigationAppPageHeader v-bind="pageContext" @menu="mobileOpen = true" />
      <slot />
    </main>
  </div>
</template>
