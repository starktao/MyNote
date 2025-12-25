import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { TaskFormPayload, TaskResponse, TaskStatusResponse } from '../types/task'
import {
  cancelTaskOnServer,
  createNoteTask,
  fetchTaskHistory,
  fetchTaskStatus,
} from '../services/taskService'

export const useTaskStore = defineStore('task-store', () => {
  const tasks = ref<TaskResponse[]>([])
  const currentTaskId = ref<string | null>(null)
  const historyPage = ref(1)
  const historyTotal = ref(0)
  const historyHasMore = ref(false)
  const isLoadingHistory = ref(false)

  const activeStatus = computed(() => {
    const current = tasks.value.find(task => task.id === currentTaskId.value)
    return current?.status ?? 'IDLE'
  })

  const currentTask = computed(() =>
    tasks.value.find(task => task.id === currentTaskId.value) ?? null,
  )

  function addTaskSkeleton(id: string, payload: TaskFormPayload) {
    const skeleton: TaskResponse = {
      id,
      status: 'PENDING',
      createdAt: new Date().toISOString(),
      markdown: '',
      transcript: '',
      audioMeta: {
        title: '等待生成...',
        cover_url: '',
        platform: payload.platform,
        video_id: '',
      },
      formData: payload,
    }
    tasks.value = [skeleton, ...tasks.value]
    currentTaskId.value = id
  }

  // Expose a friendlier API name for external callers (batch submit etc.)
  const addPendingTask = (id: string, platform: string, payload: TaskFormPayload) => {
    addTaskSkeleton(id, { ...payload, platform })
  }

  function applyStatus(id: string, payload: TaskStatusResponse) {
    tasks.value = tasks.value.map(task => {
      if (task.id !== id) return task
      const result = payload.result
      const updated: TaskResponse = {
        ...task,
        status: payload.status,
        markdown: result?.markdown ?? task.markdown,
        transcript: result?.transcript ?? task.transcript,
        audioMeta: result?.audio_meta ?? task.audioMeta,
      }
      // 如果 SSE 推送了新的类型/风格信息，更新 formData
      if (payload.video_type) {
        updated.formData = {
          ...task.formData,
          video_type: payload.video_type as any
        }
      }
      if (payload.note_style) {
        updated.formData = {
          ...updated.formData,
          note_style: payload.note_style as any
        }
      }
      return updated
    })
  }

  async function submitTask(payload: TaskFormPayload) {
    const response = await createNoteTask(payload)
    addTaskSkeleton(response.task_id, payload)
    return response.task_id
  }

  async function retryTask(id: string, override?: Partial<TaskFormPayload>) {
    const task = tasks.value.find(t => t.id === id)
    if (!task) return

    // Validate video_url before retry
    const payload = { ...task.formData, ...(override || {}), task_id: id } as any
    if (!payload.video_url || !payload.video_url.trim()) {
      console.error('Cannot retry task: video_url is empty')
      return
    }

    // direct call through createNoteTask is fine; backend will accept task_id
    await createNoteTask(payload as any)
    // mark as pending
    applyStatus(id, { status: 'PENDING' } as any)
  }

  function selectTask(id: string) {
    currentTaskId.value = id
  }

  async function removeTask(id: string) {
    const existing = tasks.value.find(task => task.id === id)
    tasks.value = tasks.value.filter(task => task.id !== id)
    if (currentTaskId.value === id) {
      currentTaskId.value = tasks.value.at(0)?.id ?? null
    }
    if (existing) {
      await cancelTaskOnServer(existing)
    }
  }

  /**
   * 从后端加载历史任务记录
   * @param options 加载选项
   */
  async function fetchHistory(options: { page?: number; pageSize?: number; append?: boolean } = {}) {
    const page = options.page || 1
    const pageSize = options.pageSize || 20
    const append = options.append || false

    try {
      isLoadingHistory.value = true
      const response = await fetchTaskHistory({ page, page_size: pageSize })

      if (append) {
        // 追加模式：加载更多
        tasks.value = [...tasks.value, ...response.items]
      } else {
        // 替换模式：初始加载
        tasks.value = response.items
        // 如果有任务且当前没有选中，选择第一个
        if (response.items.length > 0 && !currentTaskId.value) {
          currentTaskId.value = response.items[0].id
        }
      }

      historyPage.value = response.page
      historyTotal.value = response.total
      historyHasMore.value = response.has_more

      console.log(`[TaskStore] 已加载 ${response.items.length} 条历史记录 (第 ${page} 页，共 ${response.total} 条)`)

      return response
    } catch (error) {
      console.error('[TaskStore] 加载历史记录失败:', error)
      throw error
    } finally {
      isLoadingHistory.value = false
    }
  }

  /**
   * 加载更多历史记录
   */
  async function loadMoreHistory() {
    if (!historyHasMore.value || isLoadingHistory.value) {
      return
    }
    await fetchHistory({ page: historyPage.value + 1, append: true })
  }

  /**
   * 为历史任务加载完整结果（markdown、transcript等）
   * @param taskId 任务ID
   */
  async function loadTaskResult(taskId: string) {
    try {
      console.log(`[TaskStore] 正在加载任务 ${taskId} 的详细结果...`)
      const result = await fetchTaskStatus(taskId)

      // 更新任务数据
      tasks.value = tasks.value.map(task => {
        if (task.id !== taskId) return task
        return {
          ...task,
          status: result.status,
          markdown: result.result?.markdown ?? task.markdown,
          transcript: result.result?.transcript ?? task.transcript,
          audioMeta: result.result?.audio_meta ?? task.audioMeta,
        }
      })

      console.log(`[TaskStore] 任务 ${taskId} 的详细结果已加载`)
    } catch (error) {
      console.error(`[TaskStore] 加载任务 ${taskId} 详细结果失败:`, error)
      throw error
    }
  }

  return {
    tasks,
    currentTask,
    currentTaskId,
    activeStatus,
    historyPage,
    historyTotal,
    historyHasMore,
    isLoadingHistory,
    addPendingTask,
    submitTask,
    retryTask,
    selectTask,
    removeTask,
    applyStatus,
    fetchHistory,
    loadMoreHistory,
    loadTaskResult,
  }
})
