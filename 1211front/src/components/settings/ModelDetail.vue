<template>
  <div class="model-detail" v-if="model">
    <div class="model-detail-card">
      <div class="detail-header">
        <h3>{{ model.name }}</h3>
        <button class="close-detail" @click="$emit('close')">×</button>
      </div>

      <div class="detail-content">
        <div class="detail-info">
          <div class="info-item">
            <span class="info-label">提供商:</span>
            <span class="info-value">{{ model.provider }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">模型名称:</span>
            <span class="info-value">{{ model.name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">Base URL:</span>
            <span class="info-value">{{ model.base_url }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">描述:</span>
            <span class="info-value">{{ model.description }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 固定在底部的按钮区域 -->
    <div class="detail-actions-fixed">
      <button
        class="test-button-large"
        @click="$emit('test', model)"
        :disabled="testing"
      >
        {{ testing ? '测试中...' : '测试连接' }}
      </button>
      <button
        class="reconfig-button-large"
        @click="$emit('reconfig', model)"
      >
        重新配置
      </button>
      <button
        class="delete-button-large"
        @click="$emit('delete', model)"
        :disabled="deleting"
      >
        {{ deleting ? '删除中...' : '删除' }}
      </button>
    </div>

    <!-- AI图像识别测试功能 -->
    <ImageTestPanel :provider-id="model.provider_id" :model-name="model.model_name" />
  </div>
  <div v-else class="empty-detail">
    <h3>选择模型查看详情</h3>
    <p>点击左侧已配置模型列表中的"查看"按钮来查看模型详细信息</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import ImageTestPanel from './ImageTestPanel.vue'

interface SupportedModel {
  id: string
  name: string
  provider: string
  provider_id: string
  model_name: string
  description: string
  base_url: string
}

defineProps<{
  model: SupportedModel | null
  testing?: boolean
  deleting?: boolean
}>()

defineEmits<{
  close: []
  test: [model: SupportedModel]
  reconfig: [model: SupportedModel]
  delete: [model: SupportedModel]
}>()
</script>

<style scoped>
.model-detail {
  height: 100%;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  box-sizing: border-box;
  min-height: 0;
}

.empty-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  text-align: center;
  padding: var(--space-12);
}

.empty-detail h3 {
  margin: 0 0 var(--space-3) 0;
  color: var(--text-primary);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
}

.empty-detail p {
  margin: 0;
  color: var(--text-tertiary);
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  max-width: 400px;
}

.model-detail-card {
  background: var(--surface-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: calc(100% - 80px);
  min-height: 0;
  transition: all var(--duration-normal) var(--ease-out);
}

.model-detail-card:hover {
  box-shadow: var(--shadow-lg);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-5);
  border-bottom: 1px solid var(--border-primary);
  background: var(--surface-secondary);
}

.detail-header h3 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

.close-detail {
  background: transparent;
  border: none;
  font-size: 24px;
  color: var(--text-tertiary);
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.close-detail:hover {
  background: var(--surface-hover);
  color: var(--text-primary);
  transform: scale(1.1);
}

.detail-content {
  padding: var(--space-5);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
}

.detail-info {
  margin-bottom: var(--space-6);
}

.detail-info .info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--border-primary);
  transition: background var(--duration-fast) var(--ease-out);
}

.detail-info .info-item:last-child {
  border-bottom: none;
}

.detail-info .info-item:hover {
  background: var(--surface-hover);
  padding-left: var(--space-2);
  padding-right: var(--space-2);
  margin-left: calc(var(--space-2) * -1);
  margin-right: calc(var(--space-2) * -1);
  border-radius: var(--radius-sm);
}

.detail-info .info-label {
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: var(--font-size-sm);
}

.detail-info .info-value {
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-sm);
  text-align: right;
  max-width: 60%;
  word-break: break-word;
}

.detail-actions-fixed {
  display: flex;
  gap: var(--space-3);
  background: var(--surface-primary);
  padding: var(--space-4);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  border-top: 1px solid var(--border-primary);
  margin-top: auto;
  flex-shrink: 0;
  height: 80px;
  box-sizing: border-box;
}

.test-button-large,
.reconfig-button-large,
.delete-button-large {
  flex: 1;
  padding: var(--space-3) var(--space-6) !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  cursor: pointer !important;
  font-size: var(--font-size-sm) !important;
  font-weight: var(--font-weight-medium) !important;
  transition: all var(--duration-fast) var(--ease-out) !important;
  font-family: var(--font-sans) !important;
  text-decoration: none !important;
  outline: none !important;
}

.test-button-large {
  background: var(--success) !important;
  color: white !important;
}

.test-button-large:hover:not(:disabled) {
  background: var(--success-hover) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md) !important;
}

.test-button-large:disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
  transform: none !important;
}

.reconfig-button-large {
  background: var(--primary-500) !important;
  color: white !important;
}

.reconfig-button-large:hover {
  background: var(--primary-600) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md) !important;
}

.delete-button-large {
  background: var(--error) !important;
  color: white !important;
}

.delete-button-large:hover:not(:disabled) {
  background: var(--error-hover) !important;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md) !important;
}

.delete-button-large:disabled {
  opacity: 0.5 !important;
  cursor: not-allowed !important;
  transform: none !important;
}
</style>