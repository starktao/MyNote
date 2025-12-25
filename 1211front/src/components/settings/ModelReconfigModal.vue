<template>
  <div v-if="visible" class="modal-overlay" @click="handleOverlayClick">
    <div class="reconfig-modal" @click.stop>
      <div class="modal-header">
        <h3 class="modal-title">重新配置模型</h3>
        <button class="close-button" @click="handleClose">×</button>
      </div>

      <div class="modal-body">
        <!-- Model Info -->
        <div class="model-info">
          <div class="model-item">
            <span class="label">模型名称:</span>
            <span class="value">{{ config?.model_name }}</span>
          </div>
          <div class="model-item">
            <span class="label">提供商:</span>
            <span class="value">{{ config?.provider_name }}</span>
          </div>
        </div>

        <!-- Current API Key -->
        <div class="form-group">
          <label class="form-label">当前API密钥:</label>
          <div class="masked-key">
            {{ config?.api_key || '未配置' }}
          </div>
        </div>

        <!-- New API Key -->
        <div class="form-group">
          <label class="form-label" for="new-api-key">新API密钥:</label>
          <input
            id="new-api-key"
            v-model="newApiKey"
            type="password"
            class="form-input"
            :class="{ 'error': validationError }"
            placeholder="请输入新的API密钥"
            @input="handleApiKeyInput"
          />
          <div v-if="validationError" class="error-message">
            {{ validationError }}
          </div>
        </div>

        <!-- Status Message -->
        <div v-if="statusMessage" class="status-message" :class="statusType">
          {{ statusMessage }}
        </div>

        <!-- Loading State -->
        <div v-if="loading" class="loading-overlay">
          <div class="loading-spinner"></div>
          <span>{{ loadingMessage }}</span>
        </div>
      </div>

      <div class="modal-footer">
        <button class="button secondary" @click="handleClose" :disabled="loading">
          取消
        </button>
        <button
          class="button primary"
          @click="handleConfirm"
          :disabled="loading || !isFormValid"
        >
          {{ loading ? '处理中...' : '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ModelConfiguration } from '../../services/modelReconfigService'
import { getModelConfiguration, reconfigureModel, validateApiKey } from '../../services/modelReconfigService'

interface Props {
  visible: boolean
  modelId: string
}

interface Emits {
  (e: 'close'): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Reactive state
const config = ref<ModelConfiguration | null>(null)
const newApiKey = ref('')
const loading = ref(false)
const loadingMessage = ref('')
const statusMessage = ref('')
const statusType = ref<'success' | 'error' | 'warning'>('success')
const validationError = ref('')

// Computed properties
const isFormValid = computed(() => {
  return newApiKey.value.trim().length > 0 && !validationError.value
})

// Watch for modal visibility changes
watch(() => props.visible, (newVisible) => {
  if (newVisible && props.modelId) {
    loadConfiguration()
  } else {
    resetForm()
  }
})

// Methods
const loadConfiguration = async () => {
  try {
    loading.value = true
    loadingMessage.value = '加载配置中...'
    config.value = await getModelConfiguration(props.modelId)
  } catch (error) {
    console.error('Failed to load model configuration:', error)
    statusMessage.value = '加载配置失败: ' + (error as Error).message
    statusType.value = 'error'
  } finally {
    loading.value = false
    loadingMessage.value = ''
  }
}

const handleApiKeyInput = () => {
  const validation = validateApiKey(newApiKey.value)
  validationError.value = validation.error || ''

  // Clear status message when user starts typing
  if (statusMessage.value) {
    statusMessage.value = ''
  }
}

const handleOverlayClick = () => {
  if (!loading.value) {
    handleClose()
  }
}

const handleClose = () => {
  if (!loading.value) {
    emit('close')
  }
}

const handleConfirm = async () => {
  if (!isFormValid.value || loading.value || !config.value) {
    return
  }

  try {
    loading.value = true
    loadingMessage.value = '验证新API密钥...'
    statusMessage.value = ''

    // Reconfigure model (this will automatically test the connection)
    const result = await reconfigureModel(props.modelId, newApiKey.value.trim())

    statusMessage.value = result.message || '模型重新配置成功！'
    statusType.value = 'success'

    // Emit success event after a short delay
    setTimeout(() => {
      emit('success')
      emit('close')
    }, 1500)

  } catch (error) {
    console.error('Reconfiguration failed:', error)
    statusMessage.value = '重新配置失败: ' + (error as Error).message
    statusType.value = 'error'
  } finally {
    loading.value = false
    loadingMessage.value = ''
  }
}

const resetForm = () => {
  newApiKey.value = ''
  loading.value = false
  loadingMessage.value = ''
  statusMessage.value = ''
  statusType.value = 'success'
  validationError.value = ''
  config.value = null
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.reconfig-modal {
  background: var(--bg-tertiary);
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-2xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-primary);
}

.modal-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.close-button {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--text-secondary);
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 20px;
  position: relative;
}

.model-info {
  background: var(--surface-tertiary);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  text-align: center;
}

.model-item {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.model-item:last-child {
  margin-bottom: 0;
}

.label {
  font-weight: 500;
  color: var(--text-secondary);
}

.value {
  color: var(--text-primary);
  font-weight: 500;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.masked-key {
  padding: 10px 12px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  background: var(--surface-tertiary);
  color: var(--text-secondary);
  font-family: monospace;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: var(--info);
  box-shadow: 0 0 0 3px var(--info-light);
}

.form-input.error {
  border-color: var(--error);
}

.error-message {
  color: var(--error);
  font-size: 12px;
  margin-top: 5px;
}

.status-message {
  padding: 10px;
  border-radius: 6px;
  font-size: 14px;
  margin-bottom: 15px;
}

.status-message.success {
  background: var(--success-light);
  color: var(--success-dark);
  border: 1px solid var(--success);
}

.status-message.error {
  background: var(--error-light);
  color: var(--error-dark);
  border: 1px solid var(--error);
}

.status-message.warning {
  background: var(--warning-light);
  color: var(--warning-dark);
  border: 1px solid var(--warning);
}

.loading-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 20px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border-primary);
  border-top: 2px solid var(--info);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-primary);
}

.button {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.button.primary {
  background: var(--info);
  color: white;
}

.button.primary:hover:not(:disabled) {
  background: var(--info-hover);
}

.button.secondary {
  background: var(--surface-secondary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

.button.secondary:hover:not(:disabled) {
  background: var(--surface-hover);
}

.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>