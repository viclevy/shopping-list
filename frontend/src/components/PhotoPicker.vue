<template>
  <div class="photo-picker">
    <div class="picker-tabs">
      <button :class="{ active: tab === 'camera' }" @click="tab = 'camera'">{{ $t('photoPickerTab.camera') }}</button>
      <button :class="{ active: tab === 'upload' }" @click="tab = 'upload'">{{ $t('photoPickerTab.upload') }}</button>
    </div>

    <div v-if="tab === 'camera'" class="picker-content">
      <input type="file" accept="image/*" capture="environment" @change="handleFile" />
    </div>

    <div v-if="tab === 'upload'" class="picker-content">
      <input type="file" accept="image/*" @change="handleFile" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'

const { t } = useI18n()

const props = defineProps({
  productId: { type: Number, required: true },
  productName: { type: String, default: '' },
})

const emit = defineEmits(['photo-added'])

const tab = ref('camera')

async function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post(`/products/${props.productId}/photos`, formData)
    emit('photo-added')
  } catch {
    alert(t('errors.addFailed'))
  }
}
</script>

<style scoped>
.picker-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}

.picker-tabs button {
  flex: 1;
  padding: 8px;
  background: var(--border);
  color: var(--text);
  font-size: 13px;
}

.picker-tabs button.active {
  background: var(--primary);
  color: white;
}

.picker-content input[type="file"] {
  border: none;
  padding: 8px 0;
}
</style>
