<script setup lang="ts">
type Status = 'idle' | 'pending' | 'success' | 'error'

withDefaults(defineProps<{
  status: Status
  empty?: boolean
  pendingText?: string
  emptyText?: string
  errorMessage?: string
}>(), {
  empty: false,
  pendingText: '加载中…',
  emptyText: '暂无数据',
  errorMessage: '加载失败，请稍后重试',
})

defineEmits<{ retry: [] }>()
</script>

<template>
  <div v-if="status === 'pending' || status === 'idle'" class="async-state" role="status" aria-live="polite">
    {{ pendingText }}
  </div>
  <div v-else-if="status === 'error'" class="async-state async-state--error" role="alert">
    <p>{{ errorMessage }}</p>
    <button type="button" @click="$emit('retry')">重试</button>
  </div>
  <div v-else-if="empty" class="async-state" role="status">
    {{ emptyText }}
  </div>
  <slot v-else />
</template>

<style scoped>
.async-state { padding: 2rem; text-align: center; color: #64748b; }
.async-state--error { color: #b91c1c; }
.async-state button { margin-top: .75rem; padding: .45rem .9rem; border: 1px solid currentColor; border-radius: .5rem; background: transparent; cursor: pointer; }
</style>
