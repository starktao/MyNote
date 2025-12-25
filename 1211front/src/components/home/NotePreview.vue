<template>
  <section class="retro-panel preview-panel">
    <header class="panel-header preview-header">
      <div class="header-left">
        <h3>笔记内容</h3>
      </div>
      <!-- 操作按钮组 - 位于标题右侧 -->
      <div class="preview-actions" v-if="markdown || task">
        <button
          class="action-btn copy-btn"
          :class="{
            'copy-success': copyStatus === 'success',
            'copy-error': copyStatus === 'error',
            'copy-copying': copyStatus === 'copying'
          }"
          @click="copyContent"
          :disabled="!markdown || copyStatus === 'copying'"
          :title="getCopyTitle()"
        >
          <span class="action-text">{{ getCopyText() }}</span>
        </button>
        <button
          class="action-btn"
          @click="toggleView"
          :title="showTranscript ? '查看笔记内容' : '查看转写文本'"
        >
          <span class="action-text">{{ showTranscript ? '查看笔记' : '查看转写' }}</span>
        </button>
        <button
          class="action-btn focus-btn"
          :class="{ active: focusMode }"
          @click="$emit('toggle-focus')"
          :title="focusMode ? '退出专注模式' : '进入专注模式'"
        >
          <span class="action-text">{{ focusMode ? '退出专注' : '专注' }}</span>
        </button>
      </div>
    </header>

    <!-- 步骤条：只在任务进行中时显示，完成或失败后隐藏 -->
    <TaskStepIndicator
      v-if="task && !['IDLE', 'SUCCESS', 'FAILED'].includes(task.status)"
      :status="task.status"
      :task-id="task.id"
    />

    <div class="preview-body" ref="previewRef">
      <!-- 内容区域 -->
      <div class="content-wrapper">
        <article
          v-if="markdown && !showTranscript"
          class="markdown-body"
          v-html="renderedMarkdown"
        />
        <article v-else-if="showTranscript" class="transcript-view">
          <pre>{{ task?.transcript || '尚未生成转写' }}</pre>
        </article>
        <article v-else class="empty-state">
          <p>在左侧提交任务，生成的笔记会展示在这里。</p>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import texmath from 'markdown-it-texmath'
import katex from 'katex'
import { useTaskStore } from '../../stores/taskStore'
import TaskStepIndicator from './TaskStepIndicator.vue'

// 导入 KaTeX 样式
import 'katex/dist/katex.min.css'

// Props
defineProps<{
  focusMode: boolean
}>()

// Emits
defineEmits<{
  'toggle-focus': []
}>()

const md = new MarkdownIt({
  html: true,
  highlight(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(code, { language: lang }).value
      } catch (_) {
        // noop
      }
    }
    return hljs.highlightAuto(code).value
  },
}).use(texmath, {
  engine: katex,
  delimiters: 'dollars', // 支持 $ 和 $$ 语法
  katexOptions: {
    macros: { "\\RR": "\\mathbb{R}" },
    throwOnError: false // 防止公式错误导致整个页面崩溃
  }
})

const taskStore = useTaskStore()
const showTranscript = ref(false)
const previewRef = ref<HTMLElement | null>(null)
const copyStatus = ref<'idle' | 'copying' | 'success' | 'error'>('idle')

const task = computed(() => taskStore.currentTask)
const markdown = computed(() => {
  const content = task.value?.markdown
  if (Array.isArray(content)) return content[0] ?? ''
  return content
})

const renderedMarkdown = computed(() =>
  markdown.value ? md.render(String(markdown.value)) : '',
)

const copyContent = async () => {
  if (!markdown.value || copyStatus.value === 'copying') return

  try {
    copyStatus.value = 'copying'

    // 获取渲染后的 HTML 内容
    let htmlContent = renderedMarkdown.value
    const plainText = String(markdown.value)

    // 将 HTML 中的图片转换为 base64
    // 这样粘贴到微信等富文本编辑器时，图片能直接显示
    htmlContent = await convertImagesToBase64(htmlContent)

    // 使用 ClipboardItem API 同时复制多种格式
    if (navigator.clipboard && (window as any).ClipboardItem) {
      const clipboardItem = new (window as any).ClipboardItem({
        'text/html': new Blob([htmlContent], { type: 'text/html' }),
        'text/plain': new Blob([plainText], { type: 'text/plain' }),
      })
      await navigator.clipboard.write([clipboardItem])
    } else {
      // 降级方案：只复制纯文本
      await navigator.clipboard.writeText(plainText)
    }

    copyStatus.value = 'success'
    console.log('[NotePreview] 笔记内容已复制到剪贴板（包含内嵌图片的 HTML 格式）')

    // 2秒后重置状态
    setTimeout(() => {
      copyStatus.value = 'idle'
    }, 2000)
  } catch (error) {
    copyStatus.value = 'error'
    console.error('[NotePreview] 复制失败:', error)

    // 3秒后重置状态
    setTimeout(() => {
      copyStatus.value = 'idle'
    }, 3000)
  }
}

/**
 * 将 HTML 字符串中的图片 URL 转换为 base64
 * 这样粘贴到富文本编辑器时图片能直接显示
 */
const convertImagesToBase64 = async (html: string): Promise<string> => {
  // 创建一个临时 DOM 来解析 HTML
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')
  const images = doc.querySelectorAll('img')

  // 并行处理所有图片
  const promises = Array.from(images).map(async (img) => {
    const src = img.getAttribute('src')
    if (!src) return

    // 如果已经是 base64，跳过
    if (src.startsWith('data:')) return

    try {
      // 下载图片并转换为 base64
      const response = await fetch(src)
      const blob = await response.blob()
      const base64 = await blobToBase64(blob)
      img.setAttribute('src', base64)
    } catch (error) {
      console.warn(`[NotePreview] 无法转换图片 ${src}:`, error)
      // 转换失败时保持原 URL
    }
  })

  await Promise.all(promises)

  // 返回转换后的 HTML
  return doc.body.innerHTML
}

/**
 * 将 Blob 转换为 base64 字符串
 */
const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

const toggleView = () => {
  showTranscript.value = !showTranscript.value
}

// 复制按钮状态相关的辅助函数
const getCopyText = () => {
  switch (copyStatus.value) {
    case 'copying':
      return '复制中...'
    case 'success':
      return '已复制'
    case 'error':
      return '复制失败'
    default:
      return '复制'
  }
}

const getCopyTitle = () => {
  if (!markdown.value) return '暂无内容可复制'

  switch (copyStatus.value) {
    case 'copying':
      return '正在复制...'
    case 'success':
      return '复制成功！'
    case 'error':
      return '复制失败，请重试'
    default:
      return '复制笔记内容'
  }
}
</script>

<style scoped>
.preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--surface-secondary) !important; /* 外层卡片使用较亮背景 */
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-shrink: 0;
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-primary);
}

.header-left {
  flex: 1;
  min-width: 0;
}

.panel-header h3 {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.preview-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg-primary); /* 内容区域使用更亮的背景 */
  padding: var(--space-4);
}

/* 操作按钮组 - 位于标题右侧 */
.preview-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--bg-primary); /* 使用亮色背景形成对比 */
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  box-shadow: var(--shadow-sm);
  white-space: nowrap;
}

.action-btn:hover:not(:disabled) {
  background: var(--surface-hover);
  border-color: var(--primary-400);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: var(--shadow-sm);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* 复制按钮状态样式 */
.action-btn.copy-btn.copy-success {
  background: var(--success);
  color: white;
  border-color: var(--success-hover);
}

.action-btn.copy-btn.copy-success:hover {
  background: var(--success-hover);
}

.action-btn.copy-btn.copy-error {
  background: var(--error);
  color: white;
  border-color: var(--error-hover);
}

.action-btn.copy-btn.copy-error:hover {
  background: var(--error-hover);
}

.action-btn.copy-btn.copy-copying {
  opacity: 0.7;
  cursor: wait;
}

.action-icon {
  font-size: 16px;
  line-height: 1;
}

.action-text {
  font-size: var(--font-size-sm);
}

/* 内容容器 - 可滚动区域 */
.content-wrapper {
  width: 100%;
  height: 100%;
}

/* 笔记内容样式 */
.markdown-body,
.transcript-view {
  min-height: 100%;
  background: var(--surface-primary); /* 内容卡片使用纯白/浅色背景 */
  padding: 32px 40px;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 15px;
}

/* Markdown笔记样式优化 */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.markdown-body :deep(h1) {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 0;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid var(--border-primary);
}

.markdown-body :deep(h2) {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 32px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-primary);
}

.markdown-body :deep(h3) {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-top: 24px;
  margin-bottom: 12px;
}

.markdown-body :deep(h4) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-top: 20px;
  margin-bottom: 10px;
}

.markdown-body :deep(p) {
  margin-bottom: 16px;
  color: var(--text-secondary);
  line-height: 1.8;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-left: 24px;
  margin-bottom: 16px;
  padding-left: 8px;
}

.markdown-body :deep(li) {
  margin-bottom: 8px;
  color: var(--text-secondary);
  line-height: 1.7;
}

.markdown-body :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-body :deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  background: var(--surface-tertiary);
  padding: 2px 6px;
  border-radius: 3px;
  color: var(--primary-500);
  border: 1px solid var(--border-primary);
}

.markdown-body :deep(pre) {
  background: var(--surface-secondary);
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 16px;
  border: 1px solid var(--border-primary);
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
  color: var(--text-primary);
  border: none;
  font-size: 14px;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--primary-500);
  padding-left: 16px;
  margin: 16px 0;
  color: var(--text-tertiary);
  font-style: italic;
  background: var(--surface-tertiary);
  padding: 12px 16px;
  border-radius: 0 4px 4px 0;
}

.markdown-body :deep(a) {
  color: var(--primary-500);
  text-decoration: none;
  font-weight: 500;
}

.markdown-body :deep(a:hover) {
  color: var(--primary-600);
  text-decoration: underline;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
  margin: 16px 0;
  box-shadow: var(--shadow-sm);
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  border: 1px solid var(--border-primary);
  border-radius: 6px;
  overflow: hidden;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  padding: 12px 16px;
  border: 1px solid var(--border-primary);
  text-align: left;
}

.markdown-body :deep(th) {
  background: var(--surface-tertiary);
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-body :deep(td) {
  color: var(--text-secondary);
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 2px solid var(--border-primary);
  margin: 24px 0;
}

/* 数学公式样式 */
.markdown-body :deep(.katex) {
  font-size: 1.05em;
}

.markdown-body :deep(.katex-display) {
  margin: 20px 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.markdown-body :deep(.katex-display > .katex) {
  text-align: center;
  padding: 12px 0;
}

/* 行内公式 */
.markdown-body :deep(p .katex) {
  padding: 0 2px;
}

/* 转写视图样式 */
.transcript-view {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
}

.transcript-view pre {
  margin: 0;
  font-family: inherit;
  white-space: pre-wrap;
  word-wrap: break-word;
  background: none;
  padding: 0;
  border: none;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-tertiary);
  padding: 48px 32px;
  background: var(--surface-primary); /* 与内容卡片保持一致 */
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  min-height: 300px;
}

.empty-state p {
  margin: 0;
  font-size: 15px;
  color: var(--text-tertiary);
}
</style>
