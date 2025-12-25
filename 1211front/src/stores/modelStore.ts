import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface ModelInfo {
  id: string
  model_name: string
  provider_id: string
  alias: string
  is_active: boolean
}

export interface SupportedModel {
  id: string
  name: string
  provider: string
  provider_id: string
  model_name: string
  description: string
  base_url: string
}

export const useModelStore = defineStore('model', () => {
  // State
  const activeModel = ref<ModelInfo | null>(null)
  const configuredModels = ref<ModelInfo[]>([])
  const availableModels = ref<SupportedModel[]>([])
  const loading = ref(false)

  // Computed
  const hasActiveModel = computed(() => activeModel.value !== null)
  const activeModelDisplay = computed(() => {
    if (!activeModel.value) return null
    return {
      id: activeModel.value.id,
      name: activeModel.value.alias || activeModel.value.model_name,
      provider: activeModel.value.provider_id,
      model_name: activeModel.value.model_name,
      provider_id: activeModel.value.provider_id
    }
  })

  // Actions

  /**
   * 获取当前激活的模型
   */
  async function fetchActiveModel() {
    try {
      const response = await fetch('/api/models/active')
      const data = await response.json()

      if (data.code === 0 && data.data && data.data.length > 0) {
        const firstActive = data.data[0]
        activeModel.value = {
          id: firstActive.id,
          model_name: firstActive.model_name,
          provider_id: firstActive.provider_id,
          alias: firstActive.alias || firstActive.model_name,
          is_active: true
        }
      } else {
        activeModel.value = null
      }
    } catch (error) {
      console.error('[ModelStore] 获取激活模型失败:', error)
      activeModel.value = null
    }
  }

  /**
   * 获取所有已配置的模型列表
   */
  async function fetchConfiguredModels() {
    try {
      const response = await fetch('/api/model_list')
      const data = await response.json()

      if (data.code === 0) {
        configuredModels.value = data.data.map((model: any) => ({
          id: model.id,
          model_name: model.model_name,
          provider_id: model.provider_id,
          alias: model.alias || model.model_name,
          is_active: model.is_active || false
        }))
      }
    } catch (error) {
      console.error('[ModelStore] 获取已配置模型失败:', error)
    }
  }

  /**
   * 获取支持的模型列表
   */
  async function fetchAvailableModels() {
    try {
      const response = await fetch('/api/supported_models')
      const data = await response.json()

      if (data.code === 0) {
        availableModels.value = data.data
      }
    } catch (error) {
      console.error('[ModelStore] 获取支持的模型列表失败:', error)
    }
  }

  /**
   * 激活指定模型（统一切换入口）
   */
  async function activateModel(modelId: string) {
    loading.value = true
    try {
      const response = await fetch(`/api/models/${modelId}/activate`, {
        method: 'POST'
      })

      const data = await response.json()

      if (data.code === 0) {
        // 刷新激活模型状态
        await fetchActiveModel()
        // 刷新已配置模型列表（更新 is_active 状态）
        await fetchConfiguredModels()
        return { success: true, message: '切换成功' }
      } else {
        return { success: false, message: data.message || data.msg || '切换失败' }
      }
    } catch (error) {
      console.error('[ModelStore] 激活模型失败:', error)
      return { success: false, message: '网络错误，请重试' }
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除模型配置（统一删除入口）
   */
  async function deleteModel(modelId: string) {
    loading.value = true
    try {
      const response = await fetch(`/api/models/${modelId}`, {
        method: 'DELETE'
      })

      const data = await response.json()

      if (data.code === 0) {
        // 从列表中移除
        configuredModels.value = configuredModels.value.filter(m => m.id !== modelId)

        // 如果删除的是当前激活模型，重新获取激活模型
        if (activeModel.value?.id === modelId) {
          await fetchActiveModel()
        }

        return { success: true, message: '删除成功' }
      } else {
        return { success: false, message: data.message || '删除失败' }
      }
    } catch (error) {
      console.error('[ModelStore] 删除模型失败:', error)
      return { success: false, message: '网络错误，请重试' }
    } finally {
      loading.value = false
    }
  }

  /**
   * 配置新模型（统一配置入口）
   */
  async function configureModel(modelId: string, apiKey: string) {
    loading.value = true
    try {
      const response = await fetch('/api/configure_model', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: modelId,
          api_key: apiKey.trim()
        })
      })

      const data = await response.json()

      if (data.code === 0) {
        // 刷新已配置模型列表
        await fetchConfiguredModels()
        return { success: true, message: '配置成功' }
      } else {
        return { success: false, message: data.message || '配置失败' }
      }
    } catch (error) {
      console.error('[ModelStore] 配置模型失败:', error)
      return { success: false, message: '网络错误，请重试' }
    } finally {
      loading.value = false
    }
  }

  /**
   * 初始化 - 加载所有必要数据
   */
  async function initialize() {
    await Promise.all([
      fetchActiveModel(),
      fetchConfiguredModels(),
      fetchAvailableModels()
    ])
  }

  return {
    // State
    activeModel,
    configuredModels,
    availableModels,
    loading,

    // Computed
    hasActiveModel,
    activeModelDisplay,

    // Actions
    fetchActiveModel,
    fetchConfiguredModels,
    fetchAvailableModels,
    activateModel,
    deleteModel,
    configureModel,
    initialize
  }
})