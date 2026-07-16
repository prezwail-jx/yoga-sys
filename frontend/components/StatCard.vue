<script setup lang="ts">
defineProps<{
  title: string
  value: string | number
  subtitle?: string
}>()
</script>

<template>
  <section class="stat-card">
    <p class="stat-title">{{ title }}</p>
    <p class="stat-value">{{ value }}</p>
    <p v-if="subtitle" class="stat-subtitle">{{ subtitle }}</p>
  </section>
</template>
