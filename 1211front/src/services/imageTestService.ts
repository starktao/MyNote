import { apiClient, unwrap } from './api'

export interface ImageTestSession {
  session_id: string
  provider_id: string
  model_name: string
  status: string
  total_tests: number
  passed_tests: number
  failed_tests: number
  pass_rate: number
  start_time?: string
  end_time?: string
  created_at?: string
  results: ImageTestResult[]
}

export interface ImageTestResult {
  id: string
  session_id: string
  image_name: string
  image_uuid: string
  correct_answer: string
  ai_response: string
  is_correct: boolean
  response_time_ms?: number
  error_message?: string
  created_at?: string
}

export interface TestSessionSummary {
  session_id: string
  provider_id: string
  model_name: string
  total_tests: number
  passed_tests: number
  failed_tests: number
  pass_rate: number
  results: TestResult[]
}

export interface TestResult {
  image_name: string
  correct_answer: string
  ai_response: string
  is_correct: boolean
  response_time_ms: number
}

export interface TestImageStatus {
  test_images: {
    name: string
    exists: boolean
    path: string
  }[]
  all_images_exist: boolean
  statistics: {
    total_sessions: number
    completed_sessions: number
  }
  ready_to_test: boolean
}

/**
 * 创建图像识别测试会话
 */
export const createImageTestSession = (providerId: string, modelName: string) =>
  unwrap<{ session_id: string; message: string }>(
    apiClient.post('/image_test/create_session', {
      provider_id: providerId,
      model_name: modelName
    })
  )

/**
 * 运行图像识别测试
 */
export const runImageTest = (sessionId: string) =>
  unwrap<TestSessionSummary>(
    apiClient.post('/image_test/run_test', {
      session_id: sessionId
    })
  )

/**
 * 获取测试会话信息
 */
export const getImageTestSession = (sessionId: string) =>
  unwrap<ImageTestSession>(
    apiClient.get(`/image_test/session/${sessionId}`)
  )

/**
 * 获取所有测试会话列表
 */
export const getTestSessions = () =>
  unwrap<{
    sessions: ImageTestSession[]
    total: number
  }>(
    apiClient.get('/image_test/sessions')
  )

/**
 * 删除测试会话
 */
export const deleteTestSession = (sessionId: string) =>
  unwrap<{ session_id: string; message: string }>(
    apiClient.delete(`/image_test/session/${sessionId}`)
  )

/**
 * 获取图像测试功能状态
 */
export const getTestImageStatus = () =>
  unwrap<TestImageStatus>(
    apiClient.get('/image_test/status')
  )