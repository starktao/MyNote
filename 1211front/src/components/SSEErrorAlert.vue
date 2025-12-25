<template>
  <div v-if="error" class="sse-error-alert">
    <div class="alert-content">
      <h3>⚠️ 实时连接失败</h3>
      <p>{{ error }}</p>
      <button @click="$emit('retry')" class="retry-btn">重试连接</button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  error: string | null
}

interface Emits {
  (e: 'retry'): void
}

defineProps<Props>()
defineEmits<Emits>()
</script>

<style scoped>
.sse-error-alert {
  background: var(--error-light);
  border: 1px solid var(--error);
  border-radius: 4px;
  padding: 16px;
  margin: 16px 0;
}

.alert-content h3 {
  margin: 0 0 8px 0;
  color: var(--error);
}

.alert-content p {
  margin: 0 0 12px 0;
  color: var(--text-secondary);
}

.retry-btn {
  background: var(--error);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: var(--error-hover);
}

.retry-btn:active {
  background: var(--error-dark);
}
</style>