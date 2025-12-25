import { defineStore } from 'pinia'
import { ref } from 'vue'

// 接口定义
export interface Provider {
  id: string
  name: string
  logo: string
  type: 'built-in' | 'custom'
  api_key: string
  base_url: string
  enabled: boolean
  created_at?: string
}

export interface Model {
  id: string
  provider_id: string
  model_name: string
  alias: string
  enabled: boolean
  created_at?: string
}

export interface ProviderModel {
  model_name: string
  added: boolean
  enabled: boolean
}

// API 服务函数
const API_BASE = '/api'

export async function getProviderList(): Promise<Provider[]> {
  const response = await fetch(`${API_BASE}/get_all_providers`)
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '获取提供商列表失败')
}

export async function getProviderById(providerId: string): Promise<Provider> {
  const response = await fetch(`${API_BASE}/get_provider_by_id/${providerId}`)
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '获取提供商信息失败')
}

export async function addNewProvider(provider: Partial<Provider>): Promise<Provider> {
  const response = await fetch(`${API_BASE}/add_provider`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(provider)
  })
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '添加提供商失败')
}

export async function updateProvider(provider: Partial<Provider>): Promise<Provider> {
  const response = await fetch(`${API_BASE}/update_provider`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(provider)
  })
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '更新提供商失败')
}

export async function testConnection(providerId: string, modelName: string = 'gpt-3.5-turbo'): Promise<{ message: string; ok: boolean }> {
  const response = await fetch(`${API_BASE}/connect_test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider_id: providerId,
      model_name: modelName
    })
  })
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '连接测试失败')
}

export async function getModelList(): Promise<Model[]> {
  const response = await fetch(`${API_BASE}/model_list`)
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '获取模型列表失败')
}

export async function getModelListByProvider(providerId: string): Promise<ProviderModel[]> {
  const response = await fetch(`${API_BASE}/model_list/${providerId}`)
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '获取提供商模型列表失败')
}

export async function getEnabledModels(providerId: string): Promise<Model[]> {
  const response = await fetch(`${API_BASE}/model_enable/${providerId}`)
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '获取启用模型失败')
}

export async function addModel(providerId: string, modelName: string): Promise<Model> {
  const response = await fetch(`${API_BASE}/models`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      provider_id: providerId,
      model_name: modelName
    })
  })
  const data = await response.json()
  if (data.code === 0) {
    return data.data
  }
  throw new Error(data.message || '添加模型失败')
}

export async function deleteModel(modelId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/models/delete/${modelId}`)
  const data = await response.json()
  if (data.code !== 0) {
    throw new Error(data.message || '删除模型失败')
  }
}

// Provider Store
export const useProviderStore = defineStore('provider', () => {
  const providers = ref<Provider[]>([])
  const loading = ref(false)

  const setProvider = (providerList: Provider[]) => {
    providers.value = providerList
  }

  const fetchProviderList = async () => {
    loading.value = true
    try {
      const providerList = await getProviderList()
      setProvider(providerList)
    } catch (error) {
      console.error('获取提供商列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const addNewProvider = async (provider: Partial<Provider>) => {
    try {
      const newProvider = await addNewProvider(provider)
      providers.value = [newProvider, ...providers.value]
      return newProvider
    } catch (error) {
      console.error('添加提供商失败:', error)
      throw error
    }
  }

  const updateProvider = async (provider: Partial<Provider>) => {
    try {
      const updatedProvider = await updateProvider(provider)
      const index = providers.value.findIndex(p => p.id === updatedProvider.id)
      if (index !== -1) {
        providers.value[index] = updatedProvider
      }
      return updatedProvider
    } catch (error) {
      console.error('更新提供商失败:', error)
      throw error
    }
  }

  // 兼容旧接口
  const bootstrap = fetchProviderList

  const addProvider = async (payload: Partial<Provider>) => {
    return addNewProvider(payload)
  }

  const toggle = async (id: string, enabled: boolean) => {
    return updateProvider({ id, enabled })
  }

  return {
    providers,
    loading,
    setProvider,
    fetchProviderList,
    addNewProvider,
    updateProvider,
    // 兼容旧接口
    bootstrap,
    addProvider,
    toggle,
  }
})
