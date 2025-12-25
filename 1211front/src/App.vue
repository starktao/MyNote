<template>
  <div class="modern-app">
    <main class="app-shell">
      <RetroWindow>
        <template #title>
          <div class="window-title">
            <span>MyNote</span>
            <span class="window-status">{{ statusMessage }}</span>
          </div>
        </template>

        <template #default>
          <RouterView v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" />
            </Transition>
          </RouterView>
        </template>
      </RetroWindow>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useTaskStore } from './stores/taskStore'
import RetroWindow from './components/RetroWindow.vue'
import { useTaskLive } from './composables/useTaskLive'

const taskStore = useTaskStore()

// 启动时加载历史记录
onMounted(async () => {
  try {
    console.log('[App] 正在加载历史任务记录...')
    await taskStore.fetchHistory({ pageSize: 50 })
    console.log('[App] 历史任务记录加载完成')
  } catch (error) {
    console.error('[App] 加载历史任务记录失败:', error)
  }
})

// start live updates (纯SSE模式，无轮询降级)
useTaskLive()

const statusMessage = computed(() => {
  const status = taskStore.activeStatus

  switch (status) {
    case 'PENDING':
      return '任务已创建，准备开始...'
    case 'DOWNLOADING':
      return '正在下载音视频文件...'
    case 'DOWNLOADED':
      return '下载完成，准备转写...'
    case 'TRANSCRIBING':
      return '正在转写音频内容...'
    case 'GENERATING':
      return 'AI正在生成笔记...'
    case 'SCREENSHOT':
      return '正在处理截图...'
    case 'SUCCESS':
      return '笔记已生成完成！'
    case 'FAILED':
      return '任务失败 - 请查看历史记录了解详情'
    case 'RUNNING':
      return '任务进行中，请保持窗口打开...'
    case 'IDLE':
    default:
      return '空闲中'
  }
})
</script>

<style scoped>
.modern-app {
  min-height: 100vh;
  background: var(--bg-primary);
  display: flex;
  align-items: stretch;
  justify-content: center;
  padding: 0;
  position: relative;
  overflow: hidden;
  transition: background var(--duration-normal) var(--ease-out);
}

/* Subtle gradient background */
.modern-app::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle at 50% 0%,
    var(--primary-50) 0%,
    transparent 50%
  );
  opacity: 0.3;
  pointer-events: none;
}

.app-shell {
  position: relative;
  width: 100%;
  max-width: 1600px;
  height: 100vh;
  margin: 0 auto;
  z-index: var(--z-base);
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
}

.window-title {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.window-status {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}

/* Page transition animations */
.page-enter-active,
.page-leave-active {
  transition: all var(--duration-slow) var(--ease-smooth);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

@media (max-width: 768px) {
  .app-shell {
    padding: var(--space-2);
  }
}
</style>
