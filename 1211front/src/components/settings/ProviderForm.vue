<template>
  <div class="provider-form">
    <form @submit.prevent="handleSubmit" class="form-content">
      <div class="form-group">
        <label class="form-label">
          提供商名称 <span class="required">*</span>
        </label>
        <input
          v-model="form.name"
          type="text"
          class="form-input"
          :class="{ 'form-input--error': errors.name }"
          placeholder="例如：OpenAI、DeepSeek、自定义AI"
          required
        />
        <span v-if="errors.name" class="form-error">{{ errors.name }}</span>
      </div>

      <div class="form-group">
        <label class="form-label">
          类型 <span class="required">*</span>
        </label>
        <select
          v-model="form.type"
          class="form-select"
          :class="{ 'form-select--error': errors.type }"
        >
          <option value="custom">自定义</option>
          <option value="built-in">内置提供商</option>
        </select>
        <span v-if="errors.type" class="form-error">{{ errors.type }}</span>
        <small class="form-help">
          内置提供商支持常见AI服务，自定义提供商需要兼容OpenAI协议
        </small>
      </div>

      <div class="form-group">
        <label class="form-label">
          API Key <span class="required">*</span>
        </label>
        <div class="input-group">
          <input
            v-model="form.api_key"
            :type="showApiKey ? 'text' : 'password'"
            class="form-input"
            :class="{ 'form-input--error': errors.api_key }"
            placeholder="输入您的API密钥"
            required
          />
          <button
            type="button"
            class="toggle-password"
            @click="showApiKey = !showApiKey"
          >
            {{ showApiKey ? '隐藏' : '显示' }}
          </button>
        </div>
        <span v-if="errors.api_key" class="form-error">{{ errors.api_key }}</span>
      </div>

      <div class="form-group">
        <label class="form-label">
          Base URL <span class="required">*</span>
        </label>
        <input
          v-model="form.base_url"
          type="url"
          class="form-input"
          :class="{ 'form-input--error': errors.base_url }"
          placeholder="https://api.openai.com/v1"
          required
        />
        <span v-if="errors.base_url" class="form-error">{{ errors.base_url }}</span>
        <small class="form-help">
          API服务的基础URL，确保以/v1结尾
        </small>
      </div>

      <div class="form-group">
        <label class="form-label">
          Logo (可选)
        </label>
        <input
          v-model="form.logo"
          type="text"
          class="form-input"
          placeholder="提供商标识，例如：OpenAI"
        />
        <small class="form-help">
          用于显示的图标，默认使用名称首字母
        </small>
      </div>

      <div class="form-actions">
        <button
          type="button"
          class="retro-button ghost"
          @click="$emit('cancel')"
        >
          取消
        </button>
        <button
          type="submit"
          class="retro-button primary"
          :disabled="submitting"
        >
          {{ submitting ? '保存中...' : '保存' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useProviderStore, type Provider } from '../../stores/providerStore'

const emit = defineEmits<{
  success: []
  cancel: []
}>()

const providerStore = useProviderStore()
const submitting = ref(false)
const showApiKey = ref(false)

const form = reactive({
  name: '',
  logo: '',
  type: 'custom',
  api_key: '',
  base_url: '',
})

const errors = reactive({
  name: '',
  logo: '',
  type: '',
  api_key: '',
  base_url: '',
})

const validateForm = (): boolean => {
  // 清空错误
  Object.keys(errors).forEach(key => {
    errors[key] = ''
  })

  let isValid = true

  // 验证名称
  if (!form.name.trim()) {
    errors.name = '请输入提供商名称'
    isValid = false
  } else if (form.name.length < 2) {
    errors.name = '名称至少需要2个字符'
    isValid = false
  }

  // 验证API Key
  if (!form.api_key.trim()) {
    errors.api_key = '请输入API密钥'
    isValid = false
  } else if (form.api_key.length < 8) {
    errors.api_key = 'API密钥长度不正确'
    isValid = false
  }

  // 验证Base URL
  if (!form.base_url.trim()) {
    errors.base_url = '请输入Base URL'
    isValid = false
  } else {
    try {
      new URL(form.base_url)
    } catch {
      errors.base_url = '请输入有效的URL格式'
      isValid = false
    }
  }

  return isValid
}

const handleSubmit = async () => {
  if (!validateForm()) return

  submitting.value = true
  try {
    const providerData = {
      name: form.name.trim(),
      logo: form.logo.trim() || form.name.charAt(0).toUpperCase(),
      type: form.type,
      api_key: form.api_key.trim(),
      base_url: form.base_url.trim(),
      enabled: true
    }

    await providerStore.addNewProvider(providerData)

    // 重置表单
    Object.keys(form).forEach(key => {
      if (typeof form[key] === 'string') {
        form[key] = ''
      }
    })
    form.type = 'custom'
    showApiKey.value = false

    emit('success')
  } catch (error) {
    console.error('添加提供商失败:', error)
    alert(error instanceof Error ? error.message : '添加提供商失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.provider-form {
  width: 100%;
}

.form-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-label {
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
}

.required {
  color: var(--error);
}

.form-input,
.form-select {
  padding: 12px;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s ease;
  box-shadow: var(--shadow-sm);
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: var(--info);
  box-shadow: 0 0 0 3px var(--info-light);
}

.form-input--error,
.form-select--error {
  border-color: var(--error);
  box-shadow: 0 0 0 3px var(--error-light);
}

.input-group {
  display: flex;
  gap: 8px;
}

.input-group .form-input {
  flex: 1;
}

.toggle-password {
  padding: 12px;
  border: 1px solid var(--border-primary);
  border-radius: 8px;
  background: var(--surface-tertiary);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  white-space: nowrap;
  min-width: 60px;
}

.toggle-password:hover {
  background: var(--surface-hover);
  border-color: var(--border-secondary);
  color: var(--text-primary);
}

.form-error {
  margin-top: 4px;
  color: var(--error);
  font-size: 13px;
  font-weight: 500;
}

.form-help {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.4;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-primary);
}
</style>
