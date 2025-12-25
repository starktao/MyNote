/**
 * Model Reconfiguration Service
 * Handles model reconfiguration API calls and related functionality
 */

// API Configuration
const API_BASE = '/api'

// Type definitions
export interface ModelConfiguration {
  model_id: string
  model_name: string
  provider_id: string
  provider_name: string
  provider_type: string
  api_key: string
  base_url: string
  enabled: boolean
  has_api_key: boolean
}

export interface ReconfigRequest {
  api_key: string
}

export interface ReconfigResponse {
  model_id: string
  model_name: string
  provider_id: string
  provider_name: string
  api_key: string
  base_url: string
  enabled: boolean
  message: string
}

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/**
 * Get model configuration with masked API key
 */
export async function getModelConfiguration(modelId: string): Promise<ModelConfiguration> {
  const response = await fetch(`${API_BASE}/models/${modelId}/configuration`)

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const result: ApiResponse<ModelConfiguration> = await response.json()

  if (result.code !== 0) {
    throw new Error(result.message || 'Failed to get model configuration')
  }

  return result.data
}

/**
 * Reconfigure model with new API key
 */
export async function reconfigureModel(modelId: string, apiKey: string): Promise<ReconfigResponse> {
  const response = await fetch(`${API_BASE}/models/${modelId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      api_key: apiKey
    } as ReconfigRequest)
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const result: ApiResponse<ReconfigResponse> = await response.json()

  if (result.code !== 0) {
    throw new Error(result.message || 'Failed to reconfigure model')
  }

  return result.data
}

/**
 * Test connection with API key (reusing existing connection test)
 */
export async function testModelConnection(providerId: string, modelName: string): Promise<{ message: string; ok: boolean }> {
  const response = await fetch(`${API_BASE}/connect_test`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      provider_id: providerId,
      model_name: modelName
    })
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  const result = await response.json()

  if (result.code === 0) {
    return result.data
  }

  throw new Error(result.message || 'Connection test failed')
}

/**
 * Utility function to mask API key for display
 */
export function maskApiKey(apiKey: string): string {
  if (!apiKey || apiKey.length < 8) {
    return apiKey
  }

  // Show first 3 and last 3 characters, mask the rest
  if (apiKey.length <= 10) {
    return apiKey.substring(0, 2) + '***' + apiKey.substring(apiKey.length - 2)
  } else {
    return apiKey.substring(0, 3) + '***' + apiKey.substring(apiKey.length - 3)
  }
}

/**
 * Utility function to validate API key format
 */
export function validateApiKey(apiKey: string): { isValid: boolean; error?: string } {
  if (!apiKey || apiKey.trim().length === 0) {
    return { isValid: false, error: 'API密钥不能为空' }
  }

  if (apiKey.trim().length < 5) {
    return { isValid: false, error: 'API密钥长度太短' }
  }

  return { isValid: true }
}