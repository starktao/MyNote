<template>
  <div v-if="active" class="retro-panel">
    <div class="panel-header">
      <h3>批量进度</h3>
      <span class="text-xs">Batch: {{ batchId }}</span>
    </div>
    <div>
      <div class="mb-2">
        总数：{{ total }}，已完成：{{ finished }}，失败：{{ failed }}
      </div>
      <div class="progress-bar-container">
        <div class="progress-bar-fill" :style="{ width: pct + '%' }" />
      </div>
    </div>
  </div>
  <div v-else class="retro-panel">
    <div class="panel-header">
      <h3>批量进度</h3>
      <span class="text-xs">暂无批量</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useBatchStore } from '../../stores/batchStore'

const store = useBatchStore()
const active = computed(() => !!store.activeBatchId)
const total = computed(() => store.total)
const finished = computed(() => store.finished)
const failed = computed(() => store.failed)
const batchId = computed(() => store.activeBatchId)
const pct = computed(() => {
  const t = total.value || 0
  const done = finished.value + failed.value
  return t > 0 ? Math.min(100, Math.round((done / t) * 100)) : 0
})
</script>

