<template>
  <div class="model-selector">
    <div class="model-selector__header">
      <h3>模型管理</h3>
      <p class="model-selector__subtitle">为 {{ providerName }} 管理AI模型</p>
    </div>

    <div class="model-selector__content">
      <!-- 连接状态 -->
      <div class="connection-status" v-if="!hasApiKey">
        <div class="alert alert--warning">
          <span class="alert__icon">!</span>
          <span class="alert__text">请先配置API密钥后再管理模型</span>
        </div>
      </div>

      <!-- 模型列表 -->
      <div class="model-list" v-else>
        <div class="model-list__header">
          <h4>可用模型</h4>
          <button
            class="refresh-button"
            :disabled="loading"
            @click="refreshModels"
          >
            {{ loading ? '刷新中...' : '刷新' }}
          </button>
        </div>

        <div class="model-grid" v-if="!loading">
          <div
            v-for="model in availableModels"
            :key="model.model_name"
            class="model-item"
            :class="{
              'model-item--added': model.added,
              'model-item--enabled': model.enabled
            }"
          >
            <div class="model-item__info">
              <span class="model-item__name">{{ model.model_name }}</span>
              <span class="model-item__status" v-if="model.added">
                {{ model.enabled ? '已启用' : '已添加' }}
              </span>
            </div>
            <div class="model-item__actions">
              <button
                v-if="!model.added"
                class="add-button"
                @click="handleAddModel(model.model_name)"
              >
                添加
              </button>
              <button
                v-else
                class="remove-button"
                @click="handleRemoveModel(model.model_name)"
              >
                移除
              </button>
            </div>
          </div>
        </div>

        <div class="loading-placeholder" v-else>
          <div class="loading-spinner"></div>
          <p>加载模型列表中...</p>
        </div>

        <!-- 空状态 -->
        <div class="empty-state" v-if="!loading && availableModels.length === 0">
          <p>暂无可用模型</p>
        </div>
      </div>

      <!-- 自定义模型添加 -->
      <div class="custom-model" v-if="hasApiKey">
        <h4>添加自定义模型</h4>
        <form class="custom-model__form" @submit.prevent="handleAddCustomModel">
          <div class="form-field">
            <label>模型名称</label>
            <input
              v-model="customModelName"
              type="text"
              placeholder="例如: gpt-4-turbo"
              required
            />
          </div>
          <button
            type="submit"
            class="add-custom-button"
            :disabled="!customModelName.trim()"
          >
            添加自定义模型
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import type { Provider, ProviderModel } from '../../stores/providerStore'
import { useModelStore } from '../../stores/modelStore'
import { getModelListByProvider, addModel } from '../../stores/providerStore'

interface Props {
  provider: Provider
}

const props = defineProps<Props>()

const modelStore = useModelStore()
const customModelName = ref('')

const hasApiKey = computed(() => !!props.provider.api_key)
const providerName = computed(() => props.provider.name)

const availableModels = computed(() => modelStore.providerModels)
const loading = computed(() => modelStore.loading)

const refreshModels = async () => {
  if (!hasApiKey.value) return

  try {
    await modelStore.loadModelsByProvider(props.provider.id)
  } catch (error) {
    console.error('刷新模型列表失败:', error)
  }
}

const handleAddModel = async (modelName: string) => {
  try {
    await modelStore.addNewModel(props.provider.id, modelName)
    // 刷新列表
    await refreshModels()
  } catch (error) {
    console.error('添加模型失败:', error)
    alert(error instanceof Error ? error.message : '添加模型失败')
  }
}

const handleRemoveModel = async (modelName: string) => {
  try {
    // 找到对应的模型ID
    const model = modelStore.models.find(m =>
      m.provider_id === props.provider.id && m.model_name === modelName
    )
    if (model) {
      await modelStore.deleteModelById(parseInt(model.id))
      // 刷新列表
      await refreshModels()
    }
  } catch (error) {
    console.error('移除模型失败:', error)
    alert(error instanceof Error ? error.message : '移除模型失败')
  }
}

const handleAddCustomModel = async () => {
  if (!customModelName.value.trim()) return

  try {
    await handleAddModel(customModelName.value.trim())
    customModelName.value = ''
  } catch (error) {
    console.error('添加自定义模型失败:', error)
  }
}

// 监听提供商变化
watch(() => props.provider.id, (newId) => {
  if (newId && hasApiKey.value) {
    refreshModels()
  }
}, { immediate: true })

onMounted(() => {
  if (hasApiKey.value) {
    refreshModels()
  }
})
</script>

<style scoped>
.model-selector {
  padding: 16px;
}

.model-selector__header {
  margin-bottom: 32px;
}

.model-selector__header h3 {
  margin: 0 0 8px 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.model-selector__subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.connection-status {
  margin-bottom: 32px;
}

.alert {
  display: flex;
  align-items: center;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid;
}

.alert--warning {
  background: var(--warning-light);
  border-color: var(--warning);
  color: var(--text-primary);
}

.alert__icon {
  margin-right: 8px;
  font-size: 16px;
  font-weight: bold;
  color: var(--warning);
}

.alert__text {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
}

.model-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.model-list__header h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}

.refresh-button {
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

.refresh-button:hover:not(:disabled) {
  background: var(--neutral-700);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.model-grid {
  display: grid;
  gap: 12px;
  margin-bottom: 32px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  background: var(--bg-tertiary);
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.model-item:hover {
  border-color: var(--info);
  box-shadow: var(--shadow-md);
}

.model-item--added {
  border-color: var(--success);
  background: var(--success-light);
}

.model-item--enabled {
  border-color: var(--info);
  background: var(--info-light);
}

.model-item__info {
  flex: 1;
}

.model-item__name {
  display: block;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
  font-size: 14px;
}

.model-item__status {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.model-item__actions {
  margin-left: 16px;
}

.add-button,
.remove-button {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.add-button {
  background: var(--info);
  color: white;
}

.add-button:hover {
  background: var(--info-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.remove-button {
  background: var(--error);
  color: white;
}

.remove-button:hover {
  background: var(--error-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.loading-placeholder {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-primary);
  border-top: 3px solid var(--info);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
  font-size: 14px;
}

.custom-model {
  margin-top: 32px;
  padding-top: 32px;
  border-top: 1px solid var(--border-primary);
}

.custom-model h4 {
  margin: 0 0 16px 0;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
}

.custom-model__form {
  display: flex;
  gap: 12px;
  align-items: end;
}

.form-field {
  flex: 1;
}

.form-field label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-weight: 500;
  font-size: 14px;
}

.form-field input {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.form-field input:focus {
  outline: none;
  border-color: var(--info);
  box-shadow: 0 0 0 3px var(--info-light);
}

.add-custom-button {
  background: var(--success);
  color: white;
  border: none;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.add-custom-button:hover:not(:disabled) {
  background: var(--success-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.add-custom-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>