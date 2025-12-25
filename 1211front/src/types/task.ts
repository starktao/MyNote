export type TaskStatus =
  | 'IDLE'
  | 'PENDING'
  | 'DOWNLOADING'
  | 'DOWNLOADED'
  | 'TRANSCRIBING'
  | 'GENERATING'
  | 'SCREENSHOT'
  | 'SUCCESS'
  | 'FAILED'
  | 'RUNNING' // 保留兼容性

export interface TaskFormPayload {
  video_url: string
  model_name: string
  provider_id: string
  style?: string
  video_type?: 'auto' | 'tech' | 'dialogue' | 'science' | 'review'  // 视频类型
  note_style?: 'concise' | 'detailed' | 'teaching' | 'xiaohongshu'  // 笔记风格
  extras?: string
  link?: boolean

  // 以下字段为隐藏字段,前端使用默认值，不在UI展示
  platform: string // 默认: 'auto'，由后端自动推断
  quality: 'fast' | 'medium' | 'slow' // 默认: 'fast'
  format?: string[] // 默认: ['outline']，目前固定格式
  screenshot?: boolean // 默认: false，截图功能待开发
  screenshot_density?: 'low' | 'medium' | 'high' // 截图密度：少/适中/完整
}

export interface TaskResponse {
  id: string
  status: TaskStatus
  createdAt: string
  markdown: string | string[]
  transcript: string
  audioMeta: {
    title: string
    cover_url: string
    platform: string
    video_id: string
  }
  formData: TaskFormPayload
}

export interface TaskStatusResponse {
  status: TaskStatus
  message?: string
  task_id?: string
  video_type?: string  // 视频类型
  note_style?: string  // 笔记风格
  result?: {
    markdown: string | string[]
    transcript?: string
    audio_meta?: TaskResponse['audioMeta']
  }
}
