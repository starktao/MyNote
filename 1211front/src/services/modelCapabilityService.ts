import { apiClient, unwrap } from './api'

export interface CapabilityCheckRequest {
  provider_id: string
  model_name: string
}

export interface CapabilityCheckResponse {
  provider_id: string
  model_name: string
  has_vision_capability: boolean
  confidence: 'high' | 'medium' | 'low'
  model_answer: string
  interpretation: string
  response_time_ms: number
  detection_method: string
}

export async function checkModelCapability(request: CapabilityCheckRequest): Promise<CapabilityCheckResponse> {
  try {
    return await unwrap(apiClient.post('/check', request))
  } catch (error) {
    throw new Error(`能力检测失败: ${error.message}`)
  }
}