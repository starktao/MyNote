<template>
  <section class="modern-card task-form-card">
    <div class="panel-header">
      <h3>生成参数</h3>
      <button class="modern-button modern-button--ghost" type="button" @click="$router.push('/settings')">
        模型设置
      </button>
    </div>

    <form class="form-grid" @submit.prevent="handleSubmit">
      <label class="form-field">
        <span>视频链接 / 本地路径</span>
        <input v-model="form.video_url" type="text" placeholder="https:// 或 C:\path\file.wav" class="modern-input" />
      </label>

      <!-- 模型选择卡片 -->
      <div class="model-selector-field">
        <label class="form-label">模型</label>
        <div v-if="modelStore.activeModel" class="model-card" @click="showModelSwitcher = true">
          <div class="model-card__info">
            <div class="model-card__logo">{{ modelStore.activeModel.provider_id.charAt(0).toUpperCase() }}</div>
            <div class="model-card__details">
              <h5>{{ modelStore.activeModel.alias }}</h5>
              <span>{{ modelStore.activeModel.provider_id }}</span>
            </div>
          </div>
          <button type="button" class="model-card__switch-btn">切换模型</button>
        </div>
        <div v-else class="model-card model-card--empty" @click="$router.push('/settings')">
          <span>未配置模型，点击前往配置</span>
        </div>
      </div>

      <label class="form-field">
        <span>视频类型</span>
        <select v-model="form.video_type" class="modern-select" title="根据视频内容选择类型，选择自动识别将使用AI判断">
          <option value="auto">自动识别</option>
          <option value="tech">技术/教程</option>
          <option value="dialogue">人物对话</option>
          <option value="science">科普/解读</option>
          <option value="review">测评/选型</option>
        </select>
      </label>

      <label class="form-field">
        <span>笔记风格</span>
        <select v-model="form.note_style" class="modern-select">
          <option value="concise">精简（要点）</option>
          <option value="detailed">详细（完整）</option>
          <option value="teaching">教学（讲义）</option>
          <option value="xiaohongshu">小红书（轻松）</option>
        </select>
      </label>

      <label class="form-field">
        <span>备注</span>
        <textarea
          v-model="form.extras"
          rows="3"
          placeholder="例如：在笔记结尾给我讲一个笑话；保留完整数据；给出公式推导；举一个具体案例"
          class="modern-textarea"
        />
      </label>

      <div class="toggle-row">
        <label class="checkbox-label">
          <input v-model="form.link" type="checkbox" />
          <span>附加原视频链接</span>
        </label>
        <label class="checkbox-label">
          <input v-model="form.screenshot" type="checkbox" />
          <span>导出截图</span>
        </label>
      </div>

      <!-- 截图密度控制（仅在导出截图勾选时显示） -->
      <div v-if="form.screenshot" class="screenshot-density-control">
        <label class="density-label">截图密度</label>
        <div class="slider-container">
          <input
            v-model.number="densityValue"
            type="range"
            min="0"
            max="2"
            step="1"
            class="density-slider"
            @input="updateDensity"
          />
          <div class="slider-labels">
            <span :class="{ active: form.screenshot_density === 'low' }">少 (1-3张)</span>
            <span :class="{ active: form.screenshot_density === 'medium' }">适中 (3-5张)</span>
            <span :class="{ active: form.screenshot_density === 'high' }">完整 (5-8张)</span>
          </div>
        </div>
        <p class="density-hint">截图越多，生成时间越长</p>
      </div>

      <button class="modern-button modern-button--primary" :disabled="loading">
        {{ loading ? '生成中...' : '生成笔记' }}
      </button>
    </form>
  </section>

  <!-- 模型切换弹窗 - 使用 Teleport 挂载到 body 避免层叠上下文问题 -->
  <Teleport to="body">
    <div v-if="showModelSwitcher" class="modal-overlay" @click="showModelSwitcher = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>切换模型</h3>
          <button class="modal-close" @click="showModelSwitcher = false">×</button>
        </div>
        <div class="modal-body">
          <div class="model-list">
            <div
              v-for="model in modelStore.configuredModels"
              :key="model.id"
              class="model-item"
              :class="{ active: model.id === modelStore.activeModel?.id }"
            >
              <div class="model-item__info">
                <div class="model-item__logo">{{ model.provider_id.charAt(0).toUpperCase() }}</div>
                <div class="model-item__details">
                  <h5>{{ model.alias }}</h5>
                  <span>{{ model.provider_id }}</span>
                </div>
              </div>
              <button
                v-if="model.id === modelStore.activeModel?.id"
                class="model-item__status-btn"
                disabled
              >
                正在使用
              </button>
              <button
                v-else
                class="model-item__switch-btn"
                @click="handleModelSwitch(model.id)"
                :disabled="switchingModelId === model.id"
              >
                {{ switchingModelId === model.id ? '切换中...' : '切换' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
  </template>

  <script setup lang="ts">
  import { reactive, ref, onMounted, watch } from 'vue'
  import type { TaskFormPayload } from '../../types/task'
  import { useTaskStore } from '../../stores/taskStore'
  import { useModelStore } from '../../stores/modelStore'

  const taskStore = useTaskStore()
  const modelStore = useModelStore()
  const loading = ref(false)

  // 模型切换弹窗状态
  const showModelSwitcher = ref(false)
  const switchingModelId = ref<string | null>(null)

  // 截图密度滑块值（0=low, 1=medium, 2=high）
  const densityValue = ref(1)

  const form = reactive<TaskFormPayload>({
    video_url: '',
    model_name: '',
    provider_id: '',
    style: 'concise',
    video_type: 'auto',  // 默认自动识别
    note_style: 'detailed',  // 默认详细风格
    extras: '',
    link: true,
    // 以下为隐藏字段的默认值
    platform: 'auto', // 由后端自动推断
    quality: 'fast',
    format: ['outline'],
    screenshot: false,
    screenshot_density: 'medium',  // 默认适中密度
  })

  // 监听 activeModel 变化，自动更新表单
  watch(() => modelStore.activeModel, (newModel) => {
    if (newModel) {
      form.model_name = newModel.model_name
      form.provider_id = newModel.provider_id
    }
  }, { immediate: true })

  // 从 localStorage 加载用户偏好
  const loadPreferences = () => {
    try {
      const saved = localStorage.getItem('screenshot_density')
      if (saved && ['low', 'medium', 'high'].includes(saved)) {
        form.screenshot_density = saved as 'low' | 'medium' | 'high'
        // 同步滑块值
        densityValue.value = saved === 'low' ? 0 : saved === 'high' ? 2 : 1
      }
    } catch (error) {
      console.warn('Failed to load screenshot density preference:', error)
    }
  }

  // 更新密度值
  const updateDensity = () => {
    const densityMap: Record<number, 'low' | 'medium' | 'high'> = {
      0: 'low',
      1: 'medium',
      2: 'high'
    }
    form.screenshot_density = densityMap[densityValue.value]

    // 保存到 localStorage
    try {
      localStorage.setItem('screenshot_density', form.screenshot_density)
    } catch (error) {
      console.warn('Failed to save screenshot density preference:', error)
    }
  }

  // 处理模型切换
  const handleModelSwitch = async (modelId: string) => {
    const targetModel = modelStore.configuredModels.find(m => m.id === modelId)
    if (!targetModel) return

    if (!confirm(`确认将当前任务默认模型切换为 ${targetModel.alias} 吗？`)) {
      return
    }

    switchingModelId.value = modelId

    const result = await modelStore.activateModel(modelId)

    if (result.success) {
      showModelSwitcher.value = false
      alert('模型切换成功！')
    } else {
      alert(`切换失败: ${result.message}`)
    }

    switchingModelId.value = null
  }

  const validateUrls = (urls: string[]): boolean => {
    return urls.every(url => {
      const trimmed = url.trim()
      if (!trimmed) return false

      // Check if it's a local file path
      if (trimmed.startsWith('C:') || trimmed.startsWith('D:') || trimmed.startsWith('/') ||
          trimmed.startsWith('./') || trimmed.startsWith('../')) {
        return true
      }

      // Check if it's a valid URL
      try {
        new URL(trimmed)
        return true
      } catch {
        return false
      }
    })
  }

  const handleSubmit = async () => {
    if (loading.value) return

    // 验证模型选择
    if (!form.model_name || !form.provider_id) {
      alert('请选择一个可用的模型')
      return
    }

    // 验证视频链接
    const url = form.video_url.trim()
    if (!url) {
      alert('请输入视频链接或本地路径')
      return
    }
    if (!validateUrls([url])) {
      alert('请输入有效的视频链接或本地文件路径')
      return
    }

    loading.value = true
    try {
      await taskStore.submitTask({ ...form })
    } finally {
      loading.value = false
    }
  }

  // 组件挂载时加载模型和用户偏好
  onMounted(async () => {
    await modelStore.initialize()
    loadPreferences()
  })
  </script>

<style scoped>
.task-form-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border-primary);
}

.panel-header h3 {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
  flex: 1;
  padding-right: var(--space-2);
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-field > span {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--surface-tertiary);
  border-radius: var(--radius-md);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  transition: color var(--duration-fast) var(--ease-out);
}

.checkbox-label:hover {
  color: var(--primary-500);
}

.checkbox-label input[type="checkbox"] {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;

  width: 18px;
  height: 18px;
  cursor: pointer;

  border: 2px solid var(--border-secondary);
  border-radius: 4px;
  background: var(--bg-tertiary);
  transition: all var(--duration-fast) var(--ease-out);

  position: relative;
  flex-shrink: 0;
}

.checkbox-label input[type="checkbox"]:hover {
  border-color: var(--primary-500);
  background: var(--surface-hover);
}

.checkbox-label input[type="checkbox"]:checked {
  background: var(--primary-500);
  border-color: var(--primary-500);
}

.checkbox-label input[type="checkbox"]:checked::after {
  content: '';
  position: absolute;
  left: 4px;
  top: 1px;
  width: 4px;
  height: 9px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.loading-text {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

/* 模型选择卡片样式 */
.model-selector-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.model-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--surface-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.model-card:hover {
  border-color: var(--primary-400);
  box-shadow: var(--shadow-md);
}

.model-card__info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.model-card__logo {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary-500);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
}

.model-card__details h5 {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

.model-card__details span {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.model-card__switch-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--primary-500);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.model-card__switch-btn:hover {
  background: var(--primary-600);
}

.model-card--empty {
  justify-content: center;
  color: var(--text-tertiary);
  font-size: var(--font-size-sm);
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-xl);
  max-width: 500px;
  width: 90%;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-2xl);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-primary);
}

.modal-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.modal-close:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--space-5);
  overflow-y: auto;
  flex: 1;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--surface-tertiary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) var(--ease-out);
}

.model-item:hover {
  border-color: var(--primary-400);
}

.model-item.active {
  border-color: var(--success);
  background: var(--success-light);
}

.model-item__info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex: 1;
}

.model-item__logo {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--primary-500);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
}

.model-item__details h5 {
  margin: 0 0 var(--space-1) 0;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
}

.model-item__details span {
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
}

.model-item__status-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--success);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: not-allowed;
}

.model-item__switch-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--primary-500);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.model-item__switch-btn:hover:not(:disabled) {
  background: var(--primary-600);
}

.model-item__switch-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 截图密度控制样式 */
.screenshot-density-control {
  padding: var(--space-4);
  background: var(--surface-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-primary);
}

.density-label {
  display: block;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}

.slider-container {
  margin-bottom: var(--space-2);
}

.density-slider {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--border-secondary);
  border-radius: 3px;
  outline: none;
  cursor: pointer;
}

.density-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: var(--primary-500);
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.density-slider::-webkit-slider-thumb:hover {
  background: var(--primary-600);
  transform: scale(1.1);
}

.density-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: var(--primary-500);
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.density-slider::-moz-range-thumb:hover {
  background: var(--primary-600);
  transform: scale(1.1);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

.slider-labels span {
  flex: 1;
  text-align: center;
  transition: color var(--duration-fast) var(--ease-out);
}

.slider-labels span:first-child {
  text-align: left;
}

.slider-labels span:last-child {
  text-align: right;
}

.slider-labels span.active {
  color: var(--primary-500);
  font-weight: var(--font-weight-semibold);
}

.density-hint {
  margin: 0;
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-align: center;
}

@media (max-width: 768px) {
  .toggle-row {
    flex-direction: column;
    gap: var(--space-3);
  }
}
</style>
