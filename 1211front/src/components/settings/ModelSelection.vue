<template>
  <div class="model-selection">
    <div class="model-selection__header">
      <h3>AI模型配置</h3>
      <p class="model-selection__subtitle">选择并配置您想要使用的AI模型</p>
    </div>

    <div class="model-selection__content">
      <!-- 模型配置区域 -->
      <div class="config-section">
        <div class="selection-form">
          <div class="form-group">
            <label class="form-label">选择模型 <span class="required">*</span></label>
            <select
              v-model="selectedModelId"
              class="form-select"
              :class="{ 'form-select--error': errors.selectedModel }"
              @change="onModelChange"
              required
            >
              <option value="">请选择AI模型</option>
              <option
                v-for="model in modelStore.availableModels"
                :key="model.id"
                :value="model.id"
                :disabled="isModelConfigured(model.id)"
              >
                {{ model.name }} ({{ model.provider }}) {{ isModelConfigured(model.id) ? '- 已配置' : '' }}
              </option>
            </select>
            <span v-if="errors.selectedModel" class="form-error">{{ errors.selectedModel }}</span>
          </div>

          <div v-if="selectedModel && !isModelConfigured(selectedModel.id)" class="form-group">
            <label class="form-label">API Key <span class="required">*</span></label>
            <div class="input-group">
              <input
                v-model="apiKey"
                :type="showApiKey ? 'text' : 'password'"
                class="form-input"
                :class="{ 'form-input--error': errors.apiKey }"
                placeholder="输入您的API密钥"
                required
              />
              <button
                type="button"
                class="toggle-password"
                @click="showApiKey = !showApiKey"
              >
                {{ showApiKey ? '隐藏' : '显示' }}
              </button>
            </div>
            <span v-if="errors.apiKey" class="form-error">{{ errors.apiKey }}</span>
          </div>

          <div v-if="selectedModel" class="form-actions">
            <div v-if="!isModelConfigured(selectedModel.id)">
              <button
                type="button"
                class="retro-button primary"
                :disabled="configuring || !apiKey.trim()"
                @click="handleConfigSubmit"
              >
                {{ configuring ? '配置中...' : '配置模型' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 当前激活的模型 -->
        <div class="current-active" v-if="modelStore.activeModel">
          <h4>当前使用模型</h4>
          <div class="active-model-card">
            <div class="active-model-info">
              <div class="active-model-logo">{{ modelStore.activeModel.provider_id.charAt(0) || 'A' }}</div>
              <div class="active-model-details">
                <h5>{{ modelStore.activeModel.alias }}</h5>
                <span>{{ modelStore.activeModel.provider_id }}</span>
              </div>
            </div>
            <div class="active-status">使用中</div>
          </div>
        </div>

        <!-- 已配置的模型列表 -->
        <div class="configured-models" v-show="configuredModelsList.length > 0">
          <h4>已配置的模型</h4>
          <div class="configured-list">
            <div
              v-for="model in configuredModelsList"
              :key="model.id"
              class="configured-item"
              :class="{ active: modelStore.activeModel?.id === model.id }"
            >
              <div class="configured-item__info">
                <div class="configured-item__logo">
                  {{ model.provider.charAt(0) }}
                </div>
                <div class="configured-item__details">
                  <h5>{{ model.name }}</h5>
                  <span class="configured-item__provider">{{ model.provider }}</span>
                </div>
              </div>
              <div class="configured-item__actions">
                <button
                  class="view-button-small"
                  @click="selectModelToView(model)"
                >
                  查看
                </button>
                <button
                  class="activate-button-small"
                  @click="activateModel(model)"
                  :disabled="modelStore.activeModel?.id === model.id || activatingModel === model.id"
                >
                  {{ activatingModel === model.id ? '激活中...' : (modelStore.activeModel?.id === model.id ? '使用中' : '使用') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 如果没有已配置的模型，显示提示 -->
        <div class="empty-configured" v-show="configuredModelsList.length === 0 && selectedModel === null">
          <p>还没有配置任何模型，请从上方下拉菜单选择模型进行配置</p>
        </div>
      </div>
    </div>

    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useModelStore } from '../../stores/modelStore'

interface SupportedModel {
  id: string
  name: string
  provider: string
  provider_id: string
  model_name: string
  description: string
  base_url: string
}

const emit = defineEmits<{
  modelConfigured: [model: SupportedModel],
  modelDetailView: [model: SupportedModel | null]
}>()

const modelStore = useModelStore()

const selectedModelId = ref('')
const apiKey = ref('')
const showApiKey = ref(false)
const configuring = ref(false)
const activatingModel = ref<string | null>(null)

const errors = ref({
  selectedModel: '',
  apiKey: ''
})

const selectedModel = computed(() => {
  return modelStore.availableModels.find(model => model.id === selectedModelId.value) || null
})

const configuredModelsList = computed(() => {
  return modelStore.configuredModels.map(model => {
    // 找到对应的预定义模型信息来补充名称和提供商
    const predefinedModel = modelStore.availableModels.find(am =>
      am.provider_id === model.provider_id && am.model_name === model.model_name
    )
    return {
      ...model,
      name: predefinedModel?.name || model.alias || model.model_name,
      provider: predefinedModel?.provider || model.provider_id,
      description: predefinedModel?.description || '',
      base_url: predefinedModel?.base_url || ''
    }
  })
})

const isModelConfigured = (modelId: string) => {
  // 检查模型是否已配置
  return modelStore.configuredModels.some(model => {
    const predefinedModel = modelStore.availableModels.find(am => am.id === modelId)
    return predefinedModel && model.provider_id === predefinedModel.provider_id && model.model_name === predefinedModel.model_name
  })
}

const onModelChange = () => {
  // 清空错误信息
  errors.value.selectedModel = ''
  errors.value.apiKey = ''
  // 清空API密钥
  apiKey.value = ''
}

const validateForm = (): boolean => {
  // 清空错误
  errors.value.selectedModel = ''
  errors.value.apiKey = ''

  let isValid = true

  // 验证模型选择
  if (!selectedModelId.value) {
    errors.value.selectedModel = '请选择一个AI模型'
    isValid = false
  }

  // 验证API密钥
  if (!selectedModel.value || isModelConfigured(selectedModel.value.id)) {
    // 已配置的模型不需要验证API密钥
    return isValid
  }

  if (!apiKey.value.trim()) {
    errors.value.apiKey = '请输入API密钥'
    isValid = false
  } else if (apiKey.value.length < 8) {
    errors.value.apiKey = 'API密钥长度不正确'
    isValid = false
  }

  return isValid
}

const handleConfigSubmit = async () => {
  if (!validateForm()) return

  configuring.value = true
  const result = await modelStore.configureModel(selectedModel.value!.id, apiKey.value)

  if (result.success) {
    emit('modelConfigured', selectedModel.value!)
    // 从主表单提交的，清空选择
    selectedModelId.value = ''
    apiKey.value = ''
    alert('模型配置成功！')
  } else {
    alert(result.message)
  }

  configuring.value = false
}

const selectModelToView = (model: SupportedModel) => {
  emit('modelDetailView', model)
}

const activateModel = async (model: SupportedModel) => {
  if (activatingModel.value === model.id) return

  activatingModel.value = model.id

  const result = await modelStore.activateModel(model.id)

  if (result.success) {
    alert(`${model.name} 已设置为使用模型`)
  } else {
    alert(`设置失败: ${result.message}`)
  }

  activatingModel.value = null
}

onMounted(() => {
  modelStore.initialize()
})
</script>

<style scoped>
.model-selection {
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.model-selection__header {
  margin-bottom: 32px;
}

.model-selection__header h3 {
  margin: 0 0 var(--space-2) 0;
  color: var(--text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.model-selection__subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
}

.model-selection__content {
  width: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.config-section {
  width: 100%;
  max-width: none;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.selection-form {
  max-width: 100%;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  margin-bottom: var(--space-2);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
}

.required {
  color: var(--error);
}

.form-select,
.form-input {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--surface-tertiary);
  color: var(--text-primary);
  font-size: var(--font-size-sm);
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--primary-100);
}

.form-select--error,
.form-input--error {
  border-color: var(--error);
  box-shadow: 0 0 0 3px var(--error-light);
}

.form-error {
  margin-top: 4px;
  color: var(--error);
  font-size: 13px;
  font-weight: 500;
}

.input-group {
  display: flex;
  gap: 8px;
}

.input-group .form-input {
  flex: 1;
}

.toggle-password {
  padding: 12px;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  background: var(--surface-tertiary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 60px;
}

.toggle-password:hover {
  background: var(--surface-hover);
  border-color: var(--border-secondary);
  color: var(--text-primary);
}

.form-actions {
  display: flex;
  justify-content: flex-start;
  gap: 12px;
  margin-top: 16px;
}

.retro-button {
  padding: 12px 24px;
  border: 1px solid;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.retro-button.primary {
  background: var(--info);
  color: white;
  border-color: var(--info);
}

.retro-button.primary:hover:not(:disabled) {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

.retro-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.current-active {
  margin: 32px 0;
}

.current-active h4 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

.active-model-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border: 2px solid var(--success);
  border-radius: 8px;
  background: var(--success-light);
  box-shadow: 0 2px 8px var(--success-light);
}

.active-model-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.active-model-logo {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: var(--success);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
  margin-right: 12px;
}

.active-model-details {
  flex: 1;
}

.active-model-details h5 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.active-model-details span {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.active-status {
  background: var(--success);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.configured-models {
  margin-top: 32px;
}

.configured-models h4 {
  margin: 0 0 var(--space-4) 0;
  color: var(--text-primary);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

.configured-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.configured-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  background: var(--surface-primary);
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
}

.configured-item:hover {
  border-color: var(--primary-400);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.configured-item.active {
  border-color: var(--success);
  background: var(--success-light);
  box-shadow: var(--shadow-md);
}

.configured-item__info {
  display: flex;
  align-items: center;
  flex: 1;
}

.configured-item__logo {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary-500);
  color: var(--text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  margin-right: var(--space-3);
}

.configured-item__details {
  flex: 1;
}

.configured-item__details h5 {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

.configured-item__provider {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

.configured-item__actions {
  display: flex;
  gap: 10px;
  min-width: 140px;
}

.empty-configured {
  margin-top: 32px;
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
  font-size: 14px;
  background: var(--surface-tertiary);
  border-radius: 8px;
  border: 1px solid var(--border-primary);
}

.model-selection__content .test-button-small,
.model-selection__content .reconfig-button-small,
.model-selection__content .delete-button-small,
.model-selection__content .view-button-small,
.model-selection__content .activate-button-small {
  padding: 8px 12px !important;
  border: none !important;
  border-radius: 6px !important;
  cursor: pointer !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
  flex: 1;
  font-family: 'IBM Plex Mono', Monaco, 'Lucida Console', monospace !important;
  text-decoration: none !important;
  outline: none !important;
  box-shadow: none !important;
}

.test-button-small {
  background: var(--success) !important;
  color: white !important;
}

.test-button-small:hover:not(:disabled) {
  background: var(--success-hover) !important;
}

.test-button-small:disabled {
  opacity: 0.6 !important;
  cursor: not-allowed !important;
}

.reconfig-button-small {
  background: var(--warning) !important;
  color: white !important;
}

.reconfig-button-small:hover {
  background: var(--warning-hover) !important;
}

.delete-button-small {
  background: var(--error) !important;
  color: white !important;
}

.delete-button-small:hover:not(:disabled) {
  background: var(--error-hover) !important;
}

.delete-button-small:disabled {
  opacity: 0.6 !important;
  cursor: not-allowed !important;
}

.view-button-small {
  background: var(--info) !important;
  color: white !important;
}

.view-button-small:hover {
  background: var(--info-hover) !important;
}

.activate-button-small {
  background: var(--primary-500) !important;
  color: white !important;
}

.activate-button-small:hover:not(:disabled) {
  background: var(--primary-600) !important;
}

.activate-button-small:disabled {
  opacity: 0.6 !important;
  cursor: not-allowed !important;
  background: var(--success) !important;
}


.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-2xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  border-bottom: 1px solid var(--border-primary);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.modal-body {
  padding: 24px;
}

.config-info {
  background: var(--surface-tertiary);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 14px;
}

.info-value {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 14px;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.retro-button {
  padding: 12px 24px;
  border: 1px solid;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.retro-button.ghost {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--border-primary);
}

.retro-button.ghost:hover {
  background: var(--surface-tertiary);
  color: var(--text-primary);
}

.retro-button.primary {
  background: var(--info);
  color: white;
  border-color: var(--info);
}

.retro-button.primary:hover:not(:disabled) {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

.retro-button.danger {
  background: var(--error);
  color: white;
  border-color: var(--error);
}

.retro-button.danger:hover:not(:disabled) {
  background: var(--error-hover);
  border-color: var(--error-hover);
}

.retro-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.delete-warning {
  text-align: center;
}

.delete-warning p {
  margin: 0 0 16px 0;
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
}

.delete-model-info {
  background: var(--surface-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
}

.delete-model-info strong {
  display: block;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.delete-model-info span {
  color: var(--text-secondary);
  font-size: 14px;
}

.warning-text {
  color: var(--error) !important;
  font-size: 13px !important;
  margin: 16px 0 0 0 !important;
}

/* 详情视图样式 */
.model-detail-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}

/* 强制覆盖全局样式 */
.model-selection__content button.view-button-small {
  background: var(--info) !important;
  color: white !important;
}

.model-selection__content button.activate-button-small {
  background: var(--primary-500) !important;
  color: white !important;
}

</style>