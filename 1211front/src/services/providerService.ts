import { apiClient, unwrap } from './api'

export interface Provider {
  id: string
  name: string
  type: string
  api_key?: string
  base_url?: string
  enabled: boolean
}

export interface ModelOption {
  id: string
  label: string
}

export const fetchProviders = () => unwrap<Provider[]>(apiClient.get('/providers'))

export const createProvider = (payload: Partial<Provider>) =>
  unwrap<Provider>(apiClient.post('/providers', payload))

export const updateProvider = (id: string, payload: Partial<Provider>) =>
  unwrap<Provider>(apiClient.put(`/providers/${id}`, payload))

export const toggleProvider = (id: string, enabled: boolean) =>
  unwrap<Provider>(apiClient.patch(`/providers/${id}`, { enabled }))

export const fetchModels = () => unwrap<ModelOption[]>(apiClient.get('/models'))
