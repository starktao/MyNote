<template>
  <div
    class="provider-card"
    :class="{
      'provider-card--selected': selected,
      'provider-card--disabled': !provider.enabled
    }"
    @click="$emit('select', provider.id)"
  >
    <div class="provider-card__header">
      <div class="provider-card__logo">
        <div class="provider-logo">
          {{ provider.logo.charAt(0).toUpperCase() }}
        </div>
      </div>
      <div class="provider-card__info">
        <h3 class="provider-card__name">{{ provider.name }}</h3>
        <span class="provider-card__type" :class="`provider-card__type--${provider.type}`">
          {{ provider.type === 'built-in' ? '内置' : '自定义' }}
        </span>
      </div>
      <div class="provider-card__toggle">
        <label class="toggle-switch">
          <input
            type="checkbox"
            :checked="provider.enabled"
            @change.stop="handleToggle"
          >
          <span class="toggle-slider"></span>
        </label>
      </div>
    </div>

    <div class="provider-card__status">
      <div class="status-item">
        <span class="status-label">API密钥:</span>
        <span class="status-value" :class="{ 'status-value--empty': !provider.api_key }">
          {{ provider.api_key ? maskApiKey(provider.api_key) : '未配置' }}
        </span>
      </div>
      <div class="status-item">
        <span class="status-label">Base URL:</span>
        <span class="status-value">{{ provider.base_url || '未配置' }}</span>
      </div>
    </div>

    <div class="provider-card__actions" v-if="provider.enabled && provider.api_key">
      <button
        class="test-button"
        :disabled="testing"
        @click.stop="handleTest"
      >
        {{ testing ? '测试中...' : '测试连接' }}
      </button>

      <!-- 图像能力检测按钮 -->
      <button
        class="capability-button"
        :disabled="capabilityTesting"
        @click.stop="handleCapabilityTest"
      >
        <span class="capability-icon">{{ capabilityIcon }}</span>
        {{ capabilityButtonText }}
      </button>
    </div>

    <div class="provider-card__result" v-if="testResult">
      <div
        class="test-result"
        :class="testResult.success ? 'test-result--success' : 'test-result--error'"
      >
        {{ testResult.message }}
      </div>
    </div>

    <!-- 简化的模型能力检测说明 -->
    <div class="provider-card__capability-info" v-if="provider.api_key && capabilityResult">
      <div class="capability-info-content">
        <div class="capability-result" :class="{ 'has-vision': capabilityStatus === 'has_vision' }">
          <span class="capability-status-icon">{{ capabilityIcon }}</span>
          <div class="capability-details">
            <div class="capability-title">模型图像理解能力检测结果</div>
            <div class="capability-description">
              {{ capabilityResult.interpretation }}
            </div>
            <div class="capability-model-answer" v-if="capabilityResult.model_answer">
              <span class="model-answer-label">模型回答：</span>
              <span class="model-answer-text">{{ capabilityResult.model_answer }}</span>
            </div>
            <div class="capability-method">
              检测方法：{{ capabilityResult.detection_method === 'red_color_recognition' ? '红色图片识别' : capabilityResult.detection_method }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Provider } from '../../stores/providerStore'
import { testConnection } from '../../stores/providerStore'
import { checkModelCapability, type CapabilityCheckRequest } from '../../services/modelCapabilityService'

interface Props {
  provider: Provider
  selected?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  select: [id: string]
  update: [provider: Provider]
}>()

// 原有连接测试状态
const testing = ref(false)
const testResult = ref<{ success: boolean; message: string } | null>(null)

// 图像能力检测状态
const capabilityTesting = ref(false)
const capabilityStatus = ref<'unknown' | 'checking' | 'has_vision' | 'no_vision'>('unknown')
const capabilityError = ref<string>('')
const capabilityResult = ref<{
  model_answer: string
  interpretation: string
  detection_method: string
} | null>(null)

// 监听provider变化，重置能力检测状态
watch(() => props.provider, (newProvider, oldProvider) => {
  if (newProvider && oldProvider && newProvider.id !== oldProvider.id) {
    console.log(`Provider切换: ${oldProvider.id} -> ${newProvider.id}, 已重置能力检测状态`)

    // 重置状态
    capabilityStatus.value = 'unknown'
    capabilityError.value = ''
    capabilityResult.value = null
  }
}, { deep: true, immediate: false })


// 监听capabilityStatus变化用于调试
watch(capabilityStatus, (newStatus) => {
  console.log('ProviderCard: Capability status changed to:', newStatus)
})

// 图像能力检测计算属性
const capabilityIcon = computed(() => {
  console.log('ProviderCard: Computing icon for status:', capabilityStatus.value)
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


const maskApiKey = (key: string) => {
  if (!key || key.length <= 8) return key
  return key.slice(0, 4) + '*'.repeat(key.length - 8) + key.slice(-4)
}

// 原有方法
const handleToggle = async () => {
  const updatedProvider = { ...props.provider, enabled: !props.provider.enabled }
  emit('update', updatedProvider)
}

const handleTest = async () => {
  if (!props.provider.api_key) return

  testing.value = true
  testResult.value = null

  try {
    const result = await testConnection(props.provider.id)
    testResult.value = {
      success: result.ok,
      message: result.message
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: error instanceof Error ? error.message : '连接测试失败'
    }
  } finally {
    testing.value = false
  }
}

// 处理图像能力检测
const handleCapabilityTest = async () => {
  if (!props.provider.api_key) {
    capabilityError.value = '请先配置API密钥'
    return
  }

  // 根据provider类型使用默认模型进行检测
  let model_name = ''
  switch (props.provider.id) {
    case 'openai':
      model_name = 'gpt-4o'
      break
    case 'deepseek':
      model_name = 'deepseek-chat'
      break
    case 'qwen':
      model_name = 'qwen-vl-plus'
      break
    case 'anthropic':
      model_name = 'claude-3-5-sonnet-20241022'
      break
    default:
      model_name = 'gpt-3.5-turbo'
  }

  capabilityTesting.value = true
  capabilityStatus.value = 'checking'
  capabilityError.value = ''

  try {
    const request: CapabilityCheckRequest = {
      provider_id: props.provider.id,
      model_name: model_name
    }

    const result = await checkModelCapability(request)

    // 更新状态
    capabilityStatus.value = result.has_vision_capability ? 'has_vision' : 'no_vision'

    // 保存详细结果
    capabilityResult.value = {
      model_answer: result.model_answer,
      interpretation: result.interpretation,
      detection_method: result.detection_method
    }

  } catch (error) {
    capabilityError.value = error instanceof Error ? error.message : '能力检测失败'
    capabilityStatus.value = 'unknown'
  } finally {
    capabilityTesting.value = false
  }
}

</script>

<style scoped>
.provider-card {
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 16px;
  background: var(--bg-tertiary);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
}

.provider-card:hover {
  border-color: var(--info);
  box-shadow: var(--shadow-md);
}

.provider-card--selected {
  border-color: var(--info);
  background: var(--info-light);
  box-shadow: var(--shadow-md);
}

.provider-card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.provider-card__header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.provider-card__logo {
  margin-right: 16px;
}

.provider-logo {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background: var(--info);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 18px;
}

.provider-card__info {
  flex: 1;
}

.provider-card__name {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.provider-card__type {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.provider-card__type--built-in {
  background: var(--success-light);
  color: var(--success);
}

.provider-card__type--custom {
  background: var(--warning-light);
  color: var(--warning);
}

.provider-card__toggle {
  margin-left: 16px;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--neutral-400);
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

input:checked + .toggle-slider {
  background-color: var(--info);
}

input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.provider-card__status {
  margin-bottom: 16px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 14px;
}

.status-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.status-value {
  color: var(--text-primary);
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  font-size: 13px;
  background: var(--surface-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
}

.status-value--empty {
  color: var(--error);
  background: var(--error-light);
}

.provider-card__actions {
  margin-top: 12px;
}

.test-button {
  background: var(--neutral-800);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.test-button:hover:not(:disabled) {
  background: var(--neutral-700);
}

.test-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.capability-button {
  background: var(--success);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 8px;
}

.capability-button:hover:not(:disabled) {
  background: var(--success-hover);
}

.capability-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.capability-icon {
  font-size: 16px;
  line-height: 1;
}

.provider-card__result {
  margin-top: 12px;
}

.test-result {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
  text-align: center;
  font-weight: 500;
}

.test-result--success {
  background: var(--success-light);
  color: var(--success);
  border: 1px solid var(--success);
}

.test-result--error {
  background: var(--error-light);
  color: var(--error);
  border: 1px solid var(--error);
}

/* 简化的模型能力检测样式 */
.provider-card__capability-info {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-primary);
}

.capability-info-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.capability-result {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--surface-tertiary);
  transition: all 0.2s ease;
}

.capability-result.has-vision {
  border-color: var(--success);
  background: var(--success-light);
}

.capability-status-icon {
  font-size: 20px;
  line-height: 1;
  flex-shrink: 0;
}

.capability-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.capability-title {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 14px;
}

.capability-description {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.capability-method {
  font-size: 12px;
  color: var(--text-tertiary);
  font-style: italic;
}

.capability-model-answer {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: var(--surface-secondary);
  border-radius: 4px;
  margin-top: 8px;
}

.model-answer-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}

.model-answer-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
}
</style>
