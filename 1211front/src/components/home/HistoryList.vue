<template>
  <section class="retro-panel history-panel">
    <header class="panel-header">
      <h3>历史笔记</h3>
    </header>

    <div class="search-wrapper">
      <input
        v-model="keyword"
        type="search"
        class="retro-input"
        placeholder="搜索标题..."
      />
    </div>

    <div class="history-list">
      <article
        v-for="task in filteredTasks"
        :key="task.id"
        :class="['history-card', { active: currentTaskId === task.id }]"
        @click="handleTaskClick(task.id, task.markdown)"
      >
        <div class="card-header">
          <span class="status-badge" :class="`status-badge--${getStatusColor(task.status)}`">
            {{ getStatusText(task.status) }}
          </span>
          <h4 :title="task.audioMeta.title || '未命名笔记'">
            {{ task.audioMeta.title || '未命名笔记' }}
          </h4>
        </div>

        <p class="card-meta">
          {{ formatDate(task.createdAt) }} · {{ task.formData.model_name }}
        </p>

        <footer>
          <button class="retro-link" @click.stop="taskStore.removeTask(task.id)">
            删除
          </button>
          <button
            v-if="task.status === 'FAILED'"
            class="retro-link"
            @click.stop="taskStore.retryTask(task.id)"
            style="margin-left: 8px;"
          >
            重试
          </button>
        </footer>
      </article>

      <p v-if="filteredTasks.length === 0" class="empty-state">
        暂无记录，提交任务后可在此查看进度。
      </p>

      <!-- 加载更多按钮 -->
      <div v-if="taskStore.historyHasMore" class="load-more-container">
        <button
          class="retro-button load-more-btn"
          :disabled="taskStore.isLoadingHistory"
          @click="taskStore.loadMoreHistory()"
        >
          {{ taskStore.isLoadingHistory ? '加载中...' : '加载更多' }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTaskStore } from '../../stores/taskStore'
import type { TaskStatus } from '../../types/task'

const taskStore = useTaskStore()
const keyword = ref('')

const filteredTasks = computed(() => {
  if (!keyword.value.trim()) return taskStore.tasks
  return taskStore.tasks.filter(task =>
    task.audioMeta.title.toLowerCase().includes(keyword.value.toLowerCase()),
  )
})

const currentTaskId = computed(() => taskStore.currentTaskId)

/**
 * 处理任务点击事件
 * 对于历史任务，如果内容为空则先加载详情
 */
const handleTaskClick = async (taskId: string, markdown: string | string[]) => {
  // 选中任务
  taskStore.selectTask(taskId)

  // 如果是历史任务且没有内容，加载详情
  const hasContent = Array.isArray(markdown) ? markdown.length > 0 && markdown[0] : markdown
  if (!hasContent) {
    try {
      console.log(`[HistoryList] 任务 ${taskId} 内容为空，正在加载详情...`)
      await taskStore.loadTaskResult(taskId)
    } catch (error) {
      console.error(`[HistoryList] 加载任务详情失败:`, error)
    }
  }
}

const formatDate = (value: string) => {
  return new Date(value).toLocaleString()
}

const getStatusText = (status: TaskStatus): string => {
  switch (status) {
    case 'PENDING': return '等待中'
    case 'DOWNLOADING': return '下载中'
    case 'DOWNLOADED': return '已下载'
    case 'TRANSCRIBING': return '转写中'
    case 'GENERATING': return '生成中'
    case 'SCREENSHOT': return '截图中'
    case 'SUCCESS': return '已完成'
    case 'FAILED': return '失败'
    case 'RUNNING': return '运行中'
    case 'IDLE': return '空闲'
    default: return status
  }
}

const getStatusColor = (status: TaskStatus): string => {
  switch (status) {
    case 'PENDING':
    case 'IDLE':
      return 'gray'
    case 'DOWNLOADING':
    case 'DOWNLOADED':
      return 'blue'
    case 'TRANSCRIBING':
      return 'purple'
    case 'GENERATING':
      return 'orange'
    case 'SCREENSHOT':
      return 'cyan'
    case 'SUCCESS':
      return 'green'
    case 'FAILED':
      return 'red'
    case 'RUNNING':
      return 'blue'
    default:
      return 'gray'
  }
}
</script>

<style scoped>
.history-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-primary);
}

.panel-header h3 {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.search-wrapper {
  margin-bottom: var(--space-4);
}

.retro-input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--surface-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  color: var(--text-primary);
  transition: all var(--duration-fast) var(--ease-out);
}

.retro-input:hover {
  border-color: var(--border-secondary);
  background: var(--surface-hover);
}

.retro-input:focus {
  border-color: var(--border-focus);
  background: var(--bg-tertiary);
  box-shadow: 0 0 0 3px var(--primary-100);
  outline: none;
}

.retro-input::placeholder {
  color: var(--text-tertiary);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
  flex: 1;
  padding-right: var(--space-2); /* 避免滚动条遮挡内容 */
}

.history-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-2); /* 增加卡片之间的间距 */
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  min-height: 88px; /* 设置最小高度，确保内容不会挤在一起 */
  box-shadow: var(--shadow-sm);
}

.history-card:hover {
  background: var(--surface-hover);
  border-color: var(--primary-400);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.history-card.active {
  background: var(--primary-50);
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px var(--primary-100), var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
  flex-wrap: wrap;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  line-height: 1.5;
  white-space: nowrap;
  transition: all var(--duration-fast) var(--ease-out);
}

.status-badge--gray {
  background: var(--neutral-100);
  color: var(--neutral-700);
}

.status-badge--blue {
  background: var(--info-light);
  color: var(--info);
}

.status-badge--purple {
  background: rgba(139, 92, 246, 0.1);
  color: rgb(139, 92, 246);
}

.status-badge--orange {
  background: var(--warning-light);
  color: var(--warning);
}

.status-badge--cyan {
  background: rgba(6, 182, 212, 0.1);
  color: rgb(6, 182, 212);
}

.status-badge--green {
  background: var(--success-light);
  color: var(--success);
}

.status-badge--red {
  background: var(--error-light);
  color: var(--error);
}

.card-header h4 {
  margin: 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  flex: 1;
  min-width: 0; /* 允许 flex item 缩小 */

  /* 文本截断效果 */
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 100%;

  /* 鼠标悬停时显示指针，提示有 tooltip */
  cursor: inherit;
}

.card-meta {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin: 0 0 var(--space-3) 0;
}

.history-card footer {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--border-primary);
}

.retro-link {
  background: none;
  border: none;
  color: var(--primary-500);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  padding: 0;
  transition: color var(--duration-fast) var(--ease-out);
}

.retro-link:hover {
  color: var(--primary-600);
  text-decoration: underline;
}

.empty-state {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

/* 加载更多按钮 */
.load-more-container {
  padding: var(--space-4);
  text-align: center;
}

.load-more-btn {
  width: 100%;
  padding: var(--space-3);
  background: var(--surface-hover);
  border: 1px solid var(--border-primary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  border-radius: var(--radius-md);
}

.load-more-btn:hover:not(:disabled) {
  background: var(--primary-50);
  border-color: var(--primary-400);
  color: var(--primary-600);
}

.load-more-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
