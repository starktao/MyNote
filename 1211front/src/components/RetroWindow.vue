<template>
  <div class="modern-window">
    <header class="modern-titlebar">
      <div class="window-controls">
        <button class="window-control window-control--close" aria-label="Close"></button>
        <button class="window-control window-control--minimize" aria-label="Minimize"></button>
        <button class="window-control window-control--maximize" aria-label="Maximize"></button>
      </div>
      <slot name="title" />
      <button
        class="theme-toggle"
        @click="toggleTheme"
        :aria-label="isDark ? '切换到亮色模式' : '切换到暗色模式'"
        :title="isDark ? '切换到亮色模式' : '切换到暗色模式'"
      >
        <span class="theme-icon">{{ isDark ? '☀️' : '🌙' }}</span>
      </button>
    </header>
    <div class="modern-content">
      <slot />
    </div>
    <footer class="modern-statusbar">
      <slot name="status">
        <span>Ready</span>
      </slot>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const isDark = ref(false)

const toggleTheme = () => {
  isDark.value = !isDark.value
  const theme = isDark.value ? 'dark' : 'light'

  // 设置主题
  document.documentElement.setAttribute('data-theme', theme)
  // 保存到 localStorage
  localStorage.setItem('theme', theme)

  console.log(`切换到${isDark.value ? '暗' : '亮'}色模式`)
  console.log('当前 data-theme:', document.documentElement.getAttribute('data-theme'))
}

// 检查系统主题偏好
onMounted(() => {
  // 优先从 localStorage 读取用户手动设置的主题
  const savedTheme = localStorage.getItem('theme')

  if (savedTheme) {
    // 如果有保存的主题，直接使用
    isDark.value = savedTheme === 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
    console.log('从 localStorage 加载主题:', savedTheme)
  } else {
    // 没有保存的主题，才使用系统偏好
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark.value = prefersDark
    const theme = prefersDark ? 'dark' : 'light'
    document.documentElement.setAttribute('data-theme', theme)
    // 保存系统偏好到 localStorage
    localStorage.setItem('theme', theme)
    console.log('使用系统偏好主题:', theme)
  }
})
</script>

<style scoped>
.modern-window {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-2xl);
  box-shadow: var(--glass-shadow);
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
}

.modern-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  background: var(--surface-primary);
  border-bottom: 1px solid var(--border-primary);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  min-height: 60px;
}

/* macOS-style traffic lights */
.window-controls {
  display: flex;
  gap: var(--space-2);
  margin-right: var(--space-4);
}

.window-control {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  border: none;
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-out);
  padding: 0;
}

.window-control:hover {
  transform: scale(1.15);
}

.window-control--close {
  background: #ff5f57;
}

.window-control--minimize {
  background: #ffbd2e;
}

.window-control--maximize {
  background: #28c840;
}

/* 主题切换按钮 */
.theme-toggle {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-primary);
  background: var(--surface-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) var(--ease-out);
  margin-left: var(--space-4);
  padding: 0;
}

.theme-toggle:hover {
  background: var(--surface-hover);
  transform: scale(1.05);
  box-shadow: var(--shadow-sm);
}

.theme-toggle:active {
  transform: scale(0.95);
}

.theme-icon {
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--duration-normal) var(--ease-out);
}

.theme-toggle:hover .theme-icon {
  transform: rotate(15deg);
}

.modern-content {
  flex: 1;
  overflow: auto;
  padding: var(--space-6);
  background: var(--bg-secondary);
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
}

.modern-statusbar {
  padding: var(--space-3) var(--space-6);
  background: var(--surface-primary);
  border-top: 1px solid var(--border-primary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  min-height: 40px;
}

@media (max-width: 768px) {
  .modern-titlebar {
    padding: var(--space-3) var(--space-4);
  }

  .modern-content {
    padding: var(--space-4);
  }

  .modern-statusbar {
    padding: var(--space-2) var(--space-4);
  }

  .theme-toggle {
    width: 32px;
    height: 32px;
  }

  .theme-icon {
    font-size: 16px;
  }
}
</style>
