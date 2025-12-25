<template>
  <section class="retro-panel">
    <header class="panel-header">
      <h3>模型供应商</h3>
      <button class="retro-button ghost" @click="$emit('refresh')">刷新</button>
    </header>

    <ul class="provider-list">
      <li v-for="provider in providers" :key="provider.id">
        <div>
          <h4>{{ provider.name }}</h4>
          <p>{{ provider.type }} · {{ provider.base_url || '默认 API' }}</p>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="provider.enabled"
            @change="onToggle(provider.id, $event)"
          />
          <span></span>
        </label>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import type { Provider } from '../../services/providerService'

defineProps<{
  providers: Provider[]
}>()

const emit = defineEmits<{
  (e: 'toggle', id: string, enabled: boolean): void
  (e: 'refresh'): void
}>()

const onToggle = (id: string, event: Event) => {
  const target = event.target as HTMLInputElement
  emit('toggle', id, target.checked)
}
</script>
