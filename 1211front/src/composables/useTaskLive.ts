import { onMounted, onUnmounted, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { fetchTaskStatus } from '../services/taskService'

/**
 * Pure SSE-based task status monitoring.
 * No polling fallback - if SSE fails, error will be thrown.
 */
export function useTaskLive() {
  const store = useTaskStore()
  const sources = new Map<string, EventSource>()
  const base =
    String(import.meta.env.VITE_API_BASE_URL || '')
      .replace(/\/$/, '')
      .replace(/\/api$/, '') || ''

  const isTerminal = (s?: string) => s === 'SUCCESS' || s === 'FAILED'

  const createSSEConnection = (taskId: string): EventSource => {
    const url = `${base}/api/task_events/${taskId}`  // 修复URL：保留/api前缀
    const es = new EventSource(url)

    es.onmessage = async ev => {
      try {
        const data = JSON.parse(ev.data)
        const status = data?.status
        if (!status) return

        if (status === 'SUCCESS') {
          const res = await fetchTaskStatus(taskId)
          store.applyStatus(taskId, {
            status: 'SUCCESS' as any,
            result: res.result
          } as any)
          closeSSE(taskId)
        } else if (status === 'FAILED') {
          store.applyStatus(taskId, { status: 'FAILED' as any } as any)
          closeSSE(taskId)
        } else {
          store.applyStatus(taskId, { status } as any)
        }
      } catch (error) {
        console.error('SSE消息解析错误:', error)
      }
    }

    es.onerror = (error) => {
      console.error(`SSE连接失败 (任务 ${taskId}):`, error)
      es.close()
      sources.delete(taskId)

      // 记录错误但不抛出异常，避免影响其他任务
      console.warn(`任务 ${taskId} SSE连接失败，请检查网络连接`)
    }

    es.onopen = async () => {
      console.log(`SSE连接已建立 (任务 ${taskId})`)
      // 立即获取当前状态，避免错过早期事件
      try {
        const currentStatus = await fetchTaskStatus(taskId)
        if (currentStatus && currentStatus.status) {
          // 只在非终态时更新状态
          if (!isTerminal(currentStatus.status)) {
            store.applyStatus(taskId, currentStatus as any)
            console.log(`已同步任务 ${taskId} 的当前状态: ${currentStatus.status}`)
          }
        }
      } catch (error) {
        console.warn(`无法获取任务 ${taskId} 的初始状态:`, error)
      }
    }

    return es
  }

  const openSSE = (taskId: string) => {
    if (sources.has(taskId)) return

    try {
      const es = createSSEConnection(taskId)
      sources.set(taskId, es)
    } catch (error) {
      console.error(`任务 ${taskId} 无法创建SSE连接:`, error)
      // 不抛出错误，让其他任务继续工作
    }
  }

  const closeSSE = (taskId: string) => {
    const es = sources.get(taskId)
    if (es) {
      es.close()
      sources.delete(taskId)
    }
  }

  onMounted(() => {
    // 为所有非终态任务建立SSE连接
    store.tasks.forEach(t => {
      if (!isTerminal(t.status)) {
        try {
          openSSE(t.id)
        } catch (error) {
          console.error(`任务 ${t.id} SSE连接失败:`, error)
          // 可以抛出全局错误或者通过事件系统通知
        }
      }
    })

    // 监听新任务
    watch(
      () => store.tasks.map(t => ({ id: t.id, status: t.status })),
      list => {
        list.forEach(({ id, status }) => {
          if (!isTerminal(status)) {
            try {
              openSSE(id)
            } catch (error) {
              console.error(`任务 ${id} SSE连接失败:`, error)
              // 可以抛出全局错误或者通过事件系统通知
            }
          } else {
            closeSSE(id)
          }
        })
      },
      { deep: true }
    )
  })

  onUnmounted(() => {
    sources.forEach(es => es.close())
    sources.clear()
  })

  return {
    // 暴露连接状态供调试使用
    activeConnections: () => Array.from(sources.keys()),
    isConnectionActive: (taskId: string) => sources.has(taskId)
  }
}