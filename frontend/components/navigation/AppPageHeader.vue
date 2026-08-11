<script setup lang="ts">
defineProps<{ group: string; title: string; description: string }>()
defineEmits<{ menu: [] }>()
</script>

<template>
  <header class="top-header">
    <button class="mobile-menu-button" type="button" aria-label="打开导航" @click="$emit('menu')">
      <UIcon name="i-lucide-menu" />
    </button>
    <div class="page-heading-copy">
      <p class="page-breadcrumb">{{ group }}</p>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
  </header>
</template>
