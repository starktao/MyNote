<template>
  <div class="settings-container">
    <div class="settings-header">
      <button class="retro-button ghost" type="button" @click="$router.push('/')">
        ← 返回主页
      </button>
      <h2>AI模型配置</h2>
    </div>

    <div class="settings-content">
      <!-- 左侧模型列表 -->
      <div class="model-sidebar">
        <!-- <div class="sidebar-header">
          <h3>支持的AI模型</h3>
        </div> -->

        <div class="model-list">
          <ModelSelection
            @modelConfigured="handleModelConfigured"
            @modelDetailView="handleModelDetailView"
          />
        </div>
      </div>

      <!-- 右侧详情区域 -->
      <div class="detail-panel">
        <ModelDetail
          :model="selectedModelForDetail"
          :testing="testingDetailModel"
          :deleting="deletingDetailModel"
          @close="handleModelDetailView(null)"
          @test="handleDetailTest"
          @reconfig="handleDetailReconfig"
          @delete="handleDetailDelete"
        />
      </div>
    </div>

    <!-- 自定义提供商模态框 -->
    <div v-if="showCustomProvider" class="modal-overlay" @click="showCustomProvider = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>添加自定义提供商</h3>
          <button class="retro-button ghost" @click="showCustomProvider = false">×</button>
        </div>
        <div class="modal-body">
          <ProviderForm @success="handleCustomProviderAdded" @cancel="showCustomProvider = false" />
        </div>
      </div>
    </div>

    <!-- Model Reconfiguration Modal -->
    <ModelReconfigModal
      :visible="showReconfigModal"
      :model-id="reconfigModelId"
      @close="handleReconfigClose"
      @success="handleReconfigSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ModelSelection from '../components/settings/ModelSelection.vue'
import ModelDetail from '../components/settings/ModelDetail.vue'
import ProviderForm from '../components/settings/ProviderForm.vue'
import ModelReconfigModal from '../components/settings/ModelReconfigModal.vue'

interface ConfiguredModel {
  id: string
  name: string
  provider: string
  provider_id: string
  model_name: string
  base_url: string
}

interface SupportedModel {
  id: string
  name: string
  provider: string
  provider_id: string
  model_name: string
  description: string
  base_url: string
}

const configuredModels = ref<ConfiguredModel[]>([])
const showCustomProvider = ref(false)
const testingModel = ref<string | null>(null)
const selectedModelForDetail = ref<SupportedModel | null>(null)
const testingDetailModel = ref(false)
const deletingDetailModel = ref(false)

// Reconfiguration modal state
const showReconfigModal = ref(false)
const reconfigModelId = ref<string>('')

const fetchConfiguredModels = async () => {
  try {
    const response = await fetch('/api/model_list')
    const data = await response.json()
    if (data.code === 0) {
      // 将模型数据转换为所需的格式
      configuredModels.value = data.data.map((model: any) => ({
        id: `${model.provider_id}-${model.model_name}`,
        name: model.alias || model.model_name,
        provider: getProviderName(model.provider_id),
        provider_id: model.provider_id,
        model_name: model.model_name,
        base_url: ''
      }))
    }
  } catch (error) {
    console.error('获取已配置模型失败:', error)
  }
}

const getProviderName = (providerId: string): string => {
  const providerNames: Record<string, string> = {
    'openai': 'OpenAI',
    'deepseek': 'DeepSeek',
    'qwen': '阿里云百炼',
    'moonshot': 'Moonshot',
    'zhipu': 'Zhipu AI'
  }
  return providerNames[providerId] || providerId
}

const handleModelConfigured = (model: any) => {
  // 模型配置成功后，刷新已配置的模型列表
  fetchConfiguredModels()
}

const handleCustomProviderAdded = () => {
  showCustomProvider.value = false
  // 刷新已配置的模型列表
  fetchConfiguredModels()
}

const testModel = async (model: ConfiguredModel) => {
  testingModel.value = model.id
  try {
    const response = await fetch('/api/connect_test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_id: model.provider_id,
        model_name: model.model_name
      })
    })

    const data = await response.json()
    if (data.code === 0) {
      alert(`${model.name} 连接测试成功！`)
    } else {
      alert(`${model.name} 连接测试失败: ${data.message}`)
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    alert('测试连接失败，请检查配置')
  } finally {
    testingModel.value = null
  }
}

const handleModelDetailView = (model: SupportedModel | null) => {
  selectedModelForDetail.value = model
}

const handleDetailTest = async (model: SupportedModel) => {
  testingDetailModel.value = true
  try {
    const response = await fetch('/api/connect_test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider_id: model.provider_id,
        model_name: model.model_name
      })
    })

    const data = await response.json()
    if (data.code === 0) {
      alert(`${model.name} 连接测试成功！`)
    } else {
      alert(`${model.name} 连接测试失败: ${data.message}`)
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    alert('测试连接失败，请检查配置')
  } finally {
    testingDetailModel.value = false
  }
}

const handleDetailReconfig = (model: SupportedModel) => {
  reconfigModelId.value = model.id
  showReconfigModal.value = true
}

const handleReconfigSuccess = () => {
  // Refresh configured models list
  fetchConfiguredModels()
  // Also refresh detail view if currently shown
  if (selectedModelForDetail.value) {
    handleModelDetailView(selectedModelForDetail.value)
  }
}

const handleReconfigClose = () => {
  showReconfigModal.value = false
  reconfigModelId.value = ''
}

const handleDetailDelete = async (model: SupportedModel) => {
  if (!confirm(`确定要删除 ${model.name} 模型配置吗？`)) return

  deletingDetailModel.value = true
  try {
    const response = await fetch(`/api/models/${model.id}`, {
      method: 'DELETE'
    })

    const data = await response.json()
    if (data.code === 0) {
      alert(`${model.name} 模型配置已删除`)
      // 关闭详情面板
      selectedModelForDetail.value = null
      // 刷新模型列表
      await fetchConfiguredModels()
      // 触发ModelSelection组件刷新
      window.location.reload()
    } else {
      alert(`删除失败: ${data.message}`)
    }
  } catch (error) {
    console.error('删除模型失败:', error)
    alert('删除失败，请重试')
  } finally {
    deletingDetailModel.value = false
  }
}

const removeModel = async (model: ConfiguredModel) => {
  if (!confirm(`确定要移除 ${model.name} 吗？`)) return

  try {
    // 这里需要调用删除模型的API
    // 由于我们没有直接根据provider_id和model_name删除的API，暂时只提示
    alert('移除功能正在开发中，请手动在数据库中删除')
    // 实际实现时需要调用相应的删除API
  } catch (error) {
    console.error('移除模型失败:', error)
    alert('移除失败，请重试')
  }
}

onMounted(() => {
  fetchConfiguredModels()
})
</script>

<style scoped>
.settings-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  overflow: hidden;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--border-primary);
  background: var(--surface-primary);
  box-shadow: var(--shadow-sm);
}

.settings-header h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.settings-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  transition: all var(--duration-slower) var(--ease-smooth);
}

.model-sidebar {
  width: 450px;
  background: var(--surface-primary);
  border-right: 1px solid var(--border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-primary);
}

.sidebar-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.model-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

.detail-panel {
  flex: 1;
  background: var(--bg-secondary);
  overflow: hidden;
  padding: 0;
}

.configured-models h3 {
  margin: 0 0 20px 0;
  color: var(--text-primary);
  font-size: 18px;
  font-weight: 600;
}

.configured-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.configured-item {
  border: 1px solid var(--border-primary);
  border-radius: 12px;
  padding: 16px;
  background: var(--bg-tertiary);
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.configured-item:hover {
  border-color: var(--info);
  box-shadow: var(--shadow-md);
}

.configured-item__info {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.configured-item__logo {
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

.configured-item__details {
  flex: 1;
}

.configured-item__details h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 600;
}

.configured-item__provider {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.configured-item__status {
  margin-left: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.status-badge--active {
  background: var(--success-light);
  color: var(--success);
}

.configured-item__actions {
  display: flex;
  gap: 8px;
}

.test-button-small,
.remove-button-small {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  flex: 1;
}

.test-button-small {
  background: var(--info);
  color: white;
}

.test-button-small:hover:not(:disabled) {
  background: var(--info-hover);
}

.test-button-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.remove-button-small {
  background: var(--error);
  color: white;
}

.remove-button-small:hover {
  background: var(--error-hover);
}

.empty-selection {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-selection h3 {
  margin: 0 0 12px 0;
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
}

.empty-selection p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 16px;
  line-height: 1.5;
  max-width: 400px;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
  animation: fadeIn var(--duration-normal) var(--ease-out);
}

.modal-content {
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-xl);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-2xl);
  animation: modalSlideUp var(--duration-slower) var(--ease-spring);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-6);
  border-bottom: 1px solid var(--border-primary);
}

.modal-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.modal-body {
  padding: var(--space-6);
}

@media (max-width: 768px) {
  .settings-content {
    flex-direction: column;
  }

  .model-sidebar {
    width: 100%;
    height: 50vh;
    border-right: none;
    border-bottom: 1px solid var(--border-primary);
  }

  .detail-panel {
    height: 50vh;
  }
}
</style>