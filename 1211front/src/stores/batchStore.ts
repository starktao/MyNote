import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchBatchStatus } from '../services/taskService'

export const useBatchStore = defineStore('batch-store', () => {
  const activeBatchId = ref<string | null>(null)
  const total = ref(0)
  const finished = ref(0)
  const failed = ref(0)
  let timer: number | null = null

  function start(batchId: string, interval = 4000) {
    activeBatchId.value = batchId
    if (timer) window.clearInterval(timer)
    const tick = async () => {
      if (!activeBatchId.value) return
      try {
        const s = await fetchBatchStatus(activeBatchId.value)
        total.value = s.total
        finished.value = s.finished
        failed.value = s.failed
        if (s.total > 0 && s.finished + s.failed >= s.total) {
          stop()
        }
      } catch {
        // ignore
      }
    }
    tick()
    timer = window.setInterval(tick, interval)
  }

  function stop() {
    if (timer) {
      window.clearInterval(timer)
      timer = null
    }
    activeBatchId.value = null
    total.value = finished.value = failed.value = 0
  }

  return { activeBatchId, total, finished, failed, start, stop }
})

