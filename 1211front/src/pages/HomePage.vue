<template>
  <div class="desktop-grid home-grid">
    <div :class="['form-column', { 'form-hidden': !showForm }]">
      <!-- 左侧切换按钮 - 嵌入参数框内 -->
      <button
        v-if="showForm"
        class="form-toggle form-toggle-inside"
        @click="showForm = !showForm"
        :aria-label="'隐藏参数'"
        :title="'隐藏参数'"
      >
        <span class="form-toggle-icon">←</span>
      </button>
      <TaskForm />
    </div>

    <div class="workspace">
      <!-- 左侧切换按钮 - 独立在笔记内容框左侧外部 -->
      <button
        v-if="!showForm"
        class="form-toggle form-toggle-outside"
        @click="showForm = !showForm"
        :aria-label="'显示参数'"
        :title="'显示参数'"
      >
        <span class="form-toggle-icon">→</span>
      </button>

      <div :class="['preview-region', { 'history-hidden': !showHistory }]">
        <NotePreview :focus-mode="focusMode" @toggle-focus="toggleFocusMode" />

        <div class="history-column">
          <!-- 右侧切换按钮 - 嵌入历史框内 -->
          <button
            v-if="showHistory"
            class="sidebar-toggle sidebar-toggle-inside"
            @click="showHistory = !showHistory"
            :aria-label="'隐藏历史'"
            :title="'隐藏历史'"
          >
            <span class="sidebar-toggle-icon">→</span>
          </button>
          <HistoryList />
        </div>
      </div>

      <!-- 右侧切换按钮 - 独立在笔记内容框右侧外部 -->
      <button
        v-if="!showHistory"
        class="sidebar-toggle sidebar-toggle-outside"
        @click="showHistory = !showHistory"
        :aria-label="'显示历史'"
        :title="'显示历史'"
      >
        <span class="sidebar-toggle-icon">←</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import TaskForm from '../components/home/TaskForm.vue'
import HistoryList from '../components/home/HistoryList.vue'
import NotePreview from '../components/home/NotePreview.vue'

const showHistory = ref(false)
const showForm = ref(true)

// 专注模式相关状态
const focusMode = ref(false)
const previousLayout = ref({ form: true, history: false })

/**
 * 切换专注模式
 * 专注模式：隐藏左右侧栏，只显示笔记内容
 */
const toggleFocusMode = () => {
  if (!focusMode.value) {
    // 进入专注模式：保存当前布局并隐藏侧栏
    previousLayout.value = {
      form: showForm.value,
      history: showHistory.value,
    }
    showForm.value = false
    showHistory.value = false
    focusMode.value = true
    console.log('[HomePage] 进入专注模式')
  } else {
    // 退出专注模式：恢复之前的布局
    showForm.value = previousLayout.value.form
    showHistory.value = previousLayout.value.history
    focusMode.value = false
    console.log('[HomePage] 退出专注模式，恢复布局:', previousLayout.value)
  }
}
</script>

<style scoped>
.desktop-grid {
  display: grid;
  gap: var(--space-6);
  height: 100%;
  overflow: hidden;
}

.home-grid {
  grid-template-columns: 400px 1fr;
  grid-template-rows: 1fr;
  transition: grid-template-columns var(--duration-slower) var(--ease-smooth);
}

.home-grid:has(.form-hidden) {
  grid-template-columns: 0px 1fr;
}

.form-column {
  position: relative;
  overflow: hidden;
  transition: all var(--duration-slower) var(--ease-smooth);
}

.form-column.form-hidden {
  opacity: 0;
  transform: translateX(-20px);
  pointer-events: none;
}

.workspace {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100%;
  overflow: hidden;
  padding: 0 12px;
}

/* Left Toggle Button - 嵌入参数框内 */
.form-toggle.form-toggle-inside {
  position: absolute;
  right: 12px;
  top: 60px;
  width: 32px;
  height: 60px;
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 100;
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-base);
}

/* Left Toggle Button - 独立在笔记内容框左侧外部 */
.form-toggle.form-toggle-outside {
  position: absolute;
  left: 0;
  top: 60px;
  width: 32px;
  height: 60px;
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 100;
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-base);
}

.form-toggle:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  box-shadow: var(--shadow-lg);
  transform: scale(1.05);
}

.form-toggle:active {
  transform: scale(0.95);
}

.form-toggle-icon {
  transition: transform var(--duration-normal) var(--ease-out);
  display: inline-block;
  font-weight: var(--font-weight-bold);
}

.preview-region {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-4);
  flex: 1;
  overflow: hidden;
  transition: grid-template-columns var(--duration-slower) var(--ease-smooth);
}

.preview-region.history-hidden {
  grid-template-columns: 1fr 0px;
}

.history-column {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
  overflow: hidden;
  transition: all var(--duration-slower) var(--ease-smooth);
}

.history-hidden .history-column {
  opacity: 0;
  transform: translateX(20px);
  pointer-events: none;
}

/* Right Toggle Button - 嵌入历史框内 */
.sidebar-toggle.sidebar-toggle-inside {
  position: absolute;
  left: 12px;
  top: 60px;
  width: 32px;
  height: 60px;
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 100;
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-base);
}

/* Right Toggle Button - 独立在笔记内容框右侧外部 */
.sidebar-toggle.sidebar-toggle-outside {
  position: absolute;
  right: 12px;
  top: 60px;
  width: 32px;
  height: 60px;
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: all var(--duration-fast) var(--ease-out);
  z-index: 100;
  padding: 0;
  color: var(--text-secondary);
  font-size: var(--font-size-base);
}

.sidebar-toggle:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  box-shadow: var(--shadow-lg);
  transform: scale(1.05);
}

.sidebar-toggle:active {
  transform: scale(0.95);
}

.sidebar-toggle-icon {
  transition: transform var(--duration-normal) var(--ease-out);
  display: inline-block;
  font-weight: var(--font-weight-bold);
}

@media (max-width: 1200px) {
  .home-grid {
    grid-template-columns: 350px 1fr;
  }

  .preview-region {
    grid-template-columns: 1fr 280px;
  }
}

@media (max-width: 968px) {
  .home-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .preview-region {
    grid-template-columns: 1fr;
  }

  .history-column {
    display: none;
  }
}
</style>
