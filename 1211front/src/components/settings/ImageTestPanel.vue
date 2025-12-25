<template>
  <div class="capability-test-panel">
    <div class="panel-header">
      <h4>🔍 模型能力检测</h4>
    </div>

    <div class="panel-content">
      <!-- 状态信息 -->
      <div class="status-info">
        <div>Provider ID: {{ providerId }}</div>
        <div>模型名称: {{ modelName }}</div>
        <div>检测状态: {{ capabilityStatusText }}</div>
      </div>

      <!-- 能力检测按钮 -->
      <div class="test-controls">
        <button
          class="capability-button"
          :disabled="capabilityTesting"
          @click="checkCapability"
        >
          <span class="capability-icon">{{ capabilityIcon }}</span>
          {{ capabilityButtonText }}
        </button>
      </div>

      <!-- 检测结果 -->
      <div class="capability-result" v-if="capabilityStatus !== 'unknown' && !capabilityTesting">
        <div class="result-card" :class="{ 'has-vision': capabilityStatus === 'has_vision' }">
          <div class="result-icon">{{ capabilityIcon }}</div>
          <div class="result-details">
            <div class="result-title">模型图像理解能力检测结果</div>
            <div class="result-description">
              {{ capabilityStatus === 'has_vision' ? '该模型支持图像识别功能，可以用于分析截图内容' : '该模型不支持图像识别功能，仅支持文本处理' }}
            </div>
            <div class="result-method">检测方法：文本问答方式</div>
            <div class="result-confidence" v-if="capabilityResult">
              置信度：{{ capabilityResult.confidence === 'high' ? '高' : capabilityResult.confidence === 'medium' ? '中' : '低' }}
            </div>
          </div>
        </div>
      </div>

      <!-- 错误信息 -->
      <div class="error-info" v-if="capabilityError">
        <div class="error-message">
          ❌ {{ capabilityError }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { checkModelCapability, type CapabilityCheckRequest, type CapabilityCheckResponse } from '../../services/modelCapabilityService'

interface Props {
  providerId: string
  modelName: string
}

const props = defineProps<Props>()

// 能力检测状态
const capabilityTesting = ref(false)
const capabilityStatus = ref<'unknown' | 'checking' | 'has_vision' | 'no_vision'>('unknown')
const capabilityError = ref<string>('')
const capabilityResult = ref<CapabilityCheckResponse | null>(null)

// 计算属性
const capabilityIcon = computed(() => {
  switch (capabilityStatus.value) {
    case 'checking': return '⏳'
    case 'has_vision': return '🟢'
    case 'no_vision': return '🔴'
    default: return '⚪'
  }
})

const capabilityButtonText = computed(() => {
  switch (capabilityStatus.value) {
    case 'checking': return '检测中...'
    case 'has_vision': return '支持图像识别'
    case 'no_vision': return '不支持图像识别'
    default: return '检测图像能力'
  }
})

const capabilityStatusText = computed(() => {
  switch (capabilityStatus.value) {
    case 'checking': return '检测中'
    case 'has_vision': return '支持图像识别'
    case 'no_vision': return '不支持图像识别'
    default: return '未检测'
  }
})

// 监听provider和model变化，重置状态
watch([() => props.providerId, () => props.modelName], ([newProviderId, newModelName], [oldProviderId, oldModelName]) => {
  if (newProviderId && newModelName && (newProviderId !== oldProviderId || newModelName !== oldModelName)) {
    // 重置状态
    capabilityStatus.value = 'unknown'
    capabilityError.value = ''
    capabilityResult.value = null

    console.log(`模型切换: ${oldModelName} -> ${newModelName}, 已重置能力检测状态`)
  }
}, { immediate: false })

// 能力检测方法
const checkCapability = async () => {
  if (!props.providerId || !props.modelName) {
    capabilityError.value = 'Provider或模型信息缺失'
    return
  }

  capabilityTesting.value = true
  capabilityStatus.value = 'checking'
  capabilityError.value = ''

  try {
    const request: CapabilityCheckRequest = {
      provider_id: props.providerId,
      model_name: props.modelName
    }

    const result = await checkModelCapability(request)
    capabilityResult.value = result
    capabilityStatus.value = result.has_vision_capability ? 'has_vision' : 'no_vision'

    console.log(`模型能力检测: ${props.modelName} - ${result.has_vision_capability ? '支持' : '不支持'}图像识别`)

  } catch (error) {
    console.error('模型能力检测失败:', error)
    capabilityError.value = error instanceof Error ? error.message : '能力检测失败'
    capabilityStatus.value = 'unknown'
  } finally {
    capabilityTesting.value = false
  }
}
</script>

<style scoped>
.capability-test-panel {
  margin-top: 20px;
  border-top: 1px solid var(--border-primary);
  padding-top: 20px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h4 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-info {
  background: var(--surface-tertiary);
  padding: 12px;
  margin: 12px 0;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.status-info > div {
  margin-bottom: 4px;
}

.status-info > div:last-child {
  margin-bottom: 0;
}

.test-controls {
  display: flex;
  gap: 8px;
}

.capability-button {
  background: var(--success);
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.capability-button:hover:not(:disabled) {
  background: var(--success-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.capability-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.capability-icon {
  font-size: 18px;
  line-height: 1;
}

.capability-result {
  margin-top: 8px;
}

.result-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid var(--border-primary);
  background: var(--surface-secondary);
  transition: all 0.2s ease;
}

.result-card.has-vision {
  border-color: var(--success);
  background: var(--success-light);
}

.result-icon {
  font-size: 24px;
  line-height: 1;
  flex-shrink: 0;
}

.result-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.result-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 16px;
}

.result-description {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.result-method {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}

.result-confidence {
  font-size: 13px;
  color: var(--info);
  font-weight: 500;
}

.error-info {
  margin-top: 12px;
}

.error-message {
  padding: 16px;
  background: var(--error-light);
  border: 1px solid var(--error);
  border-radius: 8px;
  color: var(--error);
  font-size: 14px;
  text-align: center;
}
</style>