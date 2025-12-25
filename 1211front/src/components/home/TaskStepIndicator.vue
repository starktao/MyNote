<template>
  <div class="task-steps">
    <div
      v-for="(step, index) in steps"
      :key="step.id"
      :class="['step', {
        'step--active': currentStepIndex === index,
        'step--completed': currentStepIndex > index,
        'step--error': status === 'FAILED' && currentStepIndex === index
      }]"
    >
      <div class="step-indicator">
        <span v-if="currentStepIndex > index" class="step-icon">✓</span>
        <span v-else-if="status === 'FAILED' && currentStepIndex === index" class="step-icon">✗</span>
        <span v-else class="step-number">{{ index + 1 }}</span>
      </div>
      <div class="step-content">
        <div class="step-label">{{ step.label }}</div>
        <div v-if="currentStepIndex === index" class="step-description">
          {{ getCurrentDescription(step, index) }}
        </div>
        <!-- 转写进度条 -->
        <div
          v-if="index === 1 && currentStepIndex === 1 && transcribeProgress && transcribeProgress.progress > 0"
          class="progress-bar"
        >
          <div class="progress-fill" :style="{ width: `${transcribeProgress.progress}%` }"></div>
          <span class="progress-text">{{ transcribeProgress.progress }}%</span>
        </div>
      </div>
      <div v-if="index < steps.length - 1" class="step-connector" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { TaskStatus } from '../../types/task'
import { useTranscribeProgress } from '../../composables/useTranscribeProgress'

interface Props {
  status: TaskStatus
  taskId?: string
}

const props = defineProps<Props>()

interface Step {
  id: TaskStatus | TaskStatus[]
  label: string
  description?: string
}

const steps: Step[] = [
  { id: ['PENDING', 'DOWNLOADING'], label: '下载音视频', description: '正在获取媒体文件...' },
  { id: ['DOWNLOADED', 'TRANSCRIBING'], label: '转写音频', description: '正在识别语音内容...' },
  { id: 'GENERATING', label: '生成笔记', description: 'AI正在整理笔记...' },
  { id: 'SCREENSHOT', label: '处理截图', description: '正在提取关键画面...' },
  { id: 'SUCCESS', label: '完成', description: '笔记已生成' }
]

const currentStepIndex = computed(() => {
  const status = props.status

  // 特殊处理
  if (status === 'FAILED') {
    // 找到当前应该在哪一步失败了
    for (let i = 0; i < steps.length; i++) {
      const stepIds = Array.isArray(steps[i].id) ? steps[i].id : [steps[i].id]
      if (stepIds.includes('FAILED' as TaskStatus)) return i
    }
    return 0 // 默认第一步
  }

  if (status === 'SUCCESS') {
    return steps.length - 1
  }

  if (status === 'IDLE' || status === 'RUNNING') {
    return -1 // 未开始
  }

  // 查找匹配的步骤
  for (let i = 0; i < steps.length; i++) {
    const stepIds = Array.isArray(steps[i].id) ? steps[i].id : [steps[i].id]
    if (stepIds.includes(status)) {
      return i
    }
  }

  return -1
})

// 转写进度
const { progress: transcribeProgress, connect, disconnect } = props.taskId
  ? useTranscribeProgress(props.taskId)
  : { progress: null, connect: () => {}, disconnect: () => {} }

// 监听状态变化，当进入转写阶段时连接 SSE
watch(
  () => props.status,
  (newStatus) => {
    if (newStatus === 'TRANSCRIBING' && props.taskId) {
      connect()
    } else if (newStatus !== 'TRANSCRIBING') {
      disconnect()
    }
  },
  { immediate: true }
)

const getCurrentDescription = (step: Step, index: number): string => {
  // 如果是转写阶段且有进度信息，显示更详细的状态
  if (index === 1 && transcribeProgress?.value) {
    const tp = transcribeProgress.value
    if (tp.message) return tp.message
    if (tp.status === 'loading_model') return '正在加载模型...'
    if (tp.status === 'transcribing') return `正在转写中 (${tp.progress}%)`
    if (tp.status === 'completed') return '转写完成！'
  }
  return step.description || ''
}
</script>

<style scoped>
.task-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  margin: 0 auto var(--space-4);
  max-width: 800px;
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
  transition: all var(--duration-normal) var(--ease-out);
}

.step {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
  min-width: 120px;
  position: relative;
}

.step-indicator {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--surface-tertiary);
  border: 2px solid var(--border-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  transition: all var(--duration-normal) var(--ease-out);
  flex-shrink: 0;
  box-shadow: var(--shadow-sm);
}

.step--active .step-indicator {
  background: linear-gradient(135deg, var(--primary-400), var(--primary-500));
  border-color: var(--primary-500);
  color: var(--text-inverse);
  box-shadow: 0 0 0 4px var(--primary-100), var(--shadow-md);
  animation: pulse 2s ease-in-out infinite;
}

.step--completed .step-indicator {
  background: linear-gradient(135deg, var(--success), var(--success-hover));
  border-color: var(--success);
  color: var(--text-inverse);
  box-shadow: var(--shadow-sm);
}

.step--error .step-indicator {
  background: linear-gradient(135deg, var(--error), var(--error-hover));
  border-color: var(--error);
  color: var(--text-inverse);
  box-shadow: 0 0 0 4px var(--error-light), var(--shadow-sm);
}

.step-icon {
  font-size: 18px;
  line-height: 1;
}

.step-number {
  font-size: 15px;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin-bottom: var(--space-1);
  transition: color var(--duration-fast) var(--ease-out);
}

.step--active .step-label {
  color: var(--primary-600);
  font-weight: var(--font-weight-bold);
}

.step--completed .step-label {
  color: var(--success-dark);
}

.step--error .step-label {
  color: var(--error-dark);
}

.step-description {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: var(--space-2);
}

.progress-bar {
  position: relative;
  width: 100%;
  height: 24px;
  background: var(--surface-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-top: var(--space-2);
  box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--primary-400) 0%,
    var(--primary-500) 50%,
    var(--primary-600) 100%
  );
  transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: var(--radius-full);
  box-shadow: inset 0 1px 2px 0 rgba(255, 255, 255, 0.2);
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  z-index: 1;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
}

.step-connector {
  position: absolute;
  top: 18px;
  left: calc(36px + var(--space-3));
  right: calc(-1 * var(--space-3));
  height: 2px;
  background: var(--border-primary);
  transition: all var(--duration-normal) var(--ease-out);
}

.step--completed .step-connector {
  background: linear-gradient(
    to right,
    var(--success) 0%,
    var(--success-hover) 100%
  );
  box-shadow: 0 1px 3px rgba(16, 185, 129, 0.3);
}

.step--active .step-connector {
  background: linear-gradient(
    to right,
    var(--primary-500) 0%,
    var(--border-primary) 100%
  );
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 4px var(--primary-100), var(--shadow-md);
  }
  50% {
    box-shadow: 0 0 0 8px var(--primary-100), var(--shadow-lg);
  }
}

/* 移动端适配 */
@media (max-width: 768px) {
  .task-steps {
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .step {
    flex-direction: row;
    min-width: 100%;
  }

  .step-connector {
    display: none;
  }

  .step-indicator {
    width: 32px;
    height: 32px;
  }
}
</style>
