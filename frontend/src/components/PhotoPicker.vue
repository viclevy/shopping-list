<template>
  <div class="photo-picker">
    <div class="picker-tabs">
      <button :class="{ active: tab === 'camera' }" @click="tab = 'camera'">{{ $t('photoPickerTab.camera') }}</button>
      <button :class="{ active: tab === 'upload' }" @click="tab = 'upload'">{{ $t('photoPickerTab.upload') }}</button>
      <button :class="{ active: tab === 'url' }" @click="tab = 'url'">{{ $t('photoPickerTab.url') }}</button>
    </div>

    <div v-if="tab === 'camera'" class="picker-content">
      <!-- Android 14/15 Chrome drops the camera option for a plain accept="image/*" input;
           this non-standard MIME keeps it and is harmless on other browsers -->
      <input type="file" accept="image/*,android/allowCamera" capture="environment" @change="handleFile" />
    </div>

    <div v-if="tab === 'upload'" class="picker-content">
      <input type="file" accept="image/*" @change="handleFile" />
    </div>

    <div v-if="tab === 'url'" class="picker-content">
      <div class="url-row">
        <input
          v-model="imageUrl"
          type="url"
          dir="ltr"
          inputmode="url"
          autocapitalize="off"
          autocomplete="off"
          spellcheck="false"
          :placeholder="$t('photoPickerTab.urlPlaceholder')"
          @input="urlError = ''"
          @keydown.enter.prevent="addFromUrl"
        />
        <button class="btn-secondary" :disabled="!imageUrl.trim() || fetchingUrl" @click="addFromUrl">
          {{ fetchingUrl ? $t('common.loading') : $t('common.add') }}
        </button>
      </div>
      <p v-if="urlError" class="url-error">{{ urlError }}</p>
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
const imageUrl = ref('')
const fetchingUrl = ref(false)
const urlError = ref('')

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

async function addFromUrl() {
  let url = imageUrl.value.trim()
  if (!url || fetchingUrl.value) return
  // Allow pasting "example.com/photo.jpg" without the scheme
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(url)) url = `https://${url}`
  fetchingUrl.value = true
  urlError.value = ''
  try {
    await api.post(`/products/${props.productId}/photos/from-url`, { url })
    imageUrl.value = ''
    emit('photo-added')
  } catch {
    urlError.value = t('photoPickerTab.urlFailed')
  } finally {
    fetchingUrl.value = false
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

.url-row {
  display: flex;
  gap: 8px;
}

.url-row input {
  flex: 1;
  min-width: 0;
}

.url-error {
  color: var(--danger);
  font-size: 13px;
  margin: 8px 0 0;
}
</style>
