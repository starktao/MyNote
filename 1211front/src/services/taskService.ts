import { apiClient, unwrap } from './api'
import type { TaskFormPayload, TaskResponse, TaskStatusResponse } from '../types/task'

interface CreateTaskResponse {
  task_id: string
}

export const createNoteTask = (payload: TaskFormPayload) =>
  unwrap<CreateTaskResponse>(apiClient.post('/generate_note', payload))

export const fetchTaskStatus = (taskId: string) =>
  unwrap<TaskStatusResponse>(apiClient.get('/task_status/' + taskId))

export const cancelTaskOnServer = (task: TaskResponse) =>
  unwrap(
    apiClient.post('/delete_task', {
      video_id: task.audioMeta.video_id,
      platform: task.audioMeta.platform,
    }),
  )

// ---------- History ----------
interface HistoryResponse {
  items: TaskResponse[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

interface HistoryQueryParams {
  page?: number
  page_size?: number
  status?: string
  provider_id?: string
  model_name?: string
  platform?: string
}

export const fetchTaskHistory = (params: HistoryQueryParams = {}) =>
  unwrap<HistoryResponse>(
    apiClient.get('/tasks/history', {
      params: {
        page: params.page || 1,
        page_size: params.page_size || 20,
        ...(params.status && { status: params.status }),
        ...(params.provider_id && { provider_id: params.provider_id }),
        ...(params.model_name && { model_name: params.model_name }),
        ...(params.platform && { platform: params.platform }),
      },
    }),
  )

// ---------- Batch ----------
interface BatchCreateRequest {
  items: (TaskFormPayload & { task_id?: string })[]
  max_concurrency?: number
}
interface BatchCreateResponse {
  batch_id: string
  task_ids: string[]
}
export const createNoteBatch = (payload: BatchCreateRequest) =>
  unwrap<BatchCreateResponse>(apiClient.post('/generate_notes', payload))

export const fetchBatchStatus = (batchId: string) =>
  unwrap<{ batch_id: string; total: number; finished: number; failed: number }>(
    apiClient.get('/batch_status/' + batchId),
  )
