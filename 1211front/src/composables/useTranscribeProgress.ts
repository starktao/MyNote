import { ref, onUnmounted } from 'vue'

export interface TranscribeProgress {
  status: 'started' | 'loading_model' | 'transcribing' | 'completed' | 'error'
  progress: number
  message?: string
}

export function useTranscribeProgress(taskId: string) {
  const progress = ref<TranscribeProgress>({
    status: 'started',
    progress: 0
  })
  const error = ref<string>('')
  const isConnected = ref(false)

  let eventSource: EventSource | null = null

  const connect = () => {
    if (!taskId || isConnected.value) return

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const url = `${baseUrl}/api/transcribe/progress/${taskId}`

    eventSource = new EventSource(url)
    isConnected.value = true

    eventSource.onopen = () => {
      console.log(`转写进度 SSE 已连接: ${taskId}`)
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as TranscribeProgress
        progress.value = data
        console.log('转写进度更新:', data)

        // 如果完成或出错，自动断开
        if (data.status === 'completed' || data.status === 'error') {
          disconnect()
        }
      } catch (err) {
        console.error('解析转写进度数据失败:', err)
      }
    }

    eventSource.onerror = (err) => {
      console.error('转写进度 SSE 错误:', err)
      error.value = '无法连接到转写进度服务'
      disconnect()
    }
  }

  const disconnect = () => {
    if (eventSource) {
      eventSource.close()
      eventSource = null
      isConnected.value = false
      console.log('转写进度 SSE 已断开')
    }
  }

  // 组件卸载时自动断开
  onUnmounted(() => {
    disconnect()
  })

  return {
    progress,
    error,
    isConnected,
    connect,
    disconnect
  }
}
