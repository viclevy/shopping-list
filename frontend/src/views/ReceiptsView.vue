<template>
  <div class="receipts-view">
    <h2>{{ $t('receipts.title') }}</h2>

    <div class="card upload-card">
      <p class="hint">{{ $t('receipts.uploadHint') }}</p>
      <div v-if="staged.length" class="thumbs">
        <div v-for="(photo, i) in staged" :key="photo.url" class="thumb">
          <img :src="photo.url" alt="" />
          <button class="thumb-remove" :aria-label="$t('common.delete')" :disabled="busy" @click="removeStaged(i)">&times;</button>
        </div>
      </div>
      <div class="upload-actions">
        <button class="btn-secondary" :disabled="busy || staged.length >= MAX_PHOTOS" @click="cameraInput.click()">
          {{ $t('receipts.takePhoto') }}
        </button>
        <button class="btn-secondary" :disabled="busy || staged.length >= MAX_PHOTOS" @click="galleryInput.click()">
          {{ $t('receipts.choosePhotos') }}
        </button>
        <button class="btn-primary" :disabled="busy || !staged.length" @click="upload">
          {{ busy ? $t('receipts.reading') : $t('receipts.readReceipt') }}
        </button>
      </div>
      <p v-if="busy" class="hint">{{ $t('receipts.readingHint') }}</p>
      <p v-if="uploadError" class="error">{{ uploadError }}</p>
      <!-- Android 14/15 Chrome drops the camera option for a plain accept="image/*" input;
           this non-standard MIME keeps it and is harmless on other browsers -->
      <input ref="cameraInput" type="file" accept="image/*,android/allowCamera" capture="environment" hidden @change="onPick" />
      <input ref="galleryInput" type="file" accept="image/*" multiple hidden @change="onPick" />
    </div>

    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
    <div v-else-if="loadError" class="loading error">{{ loadError }}</div>
    <div v-else-if="!receipts.length" class="empty">{{ $t('receipts.empty') }}</div>
    <router-link
      v-for="r in receipts"
      :key="r.id"
      :to="`/receipts/${r.id}`"
      class="card receipt-row"
    >
      <div class="row-main">
        <strong>{{ r.store_name || r.store_text || $t('receipts.unknownStore') }}</strong>
        <span class="status" :class="r.status">{{ $t(`receipts.status.${r.status}`) }}</span>
      </div>
      <div class="row-meta">
        <span>{{ rowDate(r) }}</span>
        <span v-if="r.line_count">{{ $t('receipts.itemCount', { count: r.line_count }, r.line_count) }}</span>
        <span>{{ displayName(r.uploaded_by) }}</span>
        <span v-if="r.total != null" class="row-total">{{ formatMoney(r.total) }}</span>
      </div>
    </router-link>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api.js'
import { displayName, serverDate, formatDateTime, formatMoney } from '../utils.js'

const MAX_PHOTOS = 3

const { t, locale } = useI18n()
const router = useRouter()

const receipts = ref([])
const loading = ref(true)
const loadError = ref('')
const staged = ref([]) // photos picked but not uploaded yet: { file, url }
const busy = ref(false)
const uploadError = ref('')
const cameraInput = ref(null)
const galleryInput = ref(null)

async function load() {
  try {
    const res = await api.get('/receipts')
    receipts.value = res.data
  } catch {
    loadError.value = t('errors.loadFailed')
  } finally {
    loading.value = false
  }
}

function onPick(event) {
  for (const file of event.target.files || []) {
    if (staged.value.length < MAX_PHOTOS) staged.value.push({ file, url: URL.createObjectURL(file) })
  }
  event.target.value = '' // so the same photo can be picked again
}

function removeStaged(index) {
  URL.revokeObjectURL(staged.value[index].url)
  staged.value.splice(index, 1)
}

async function upload() {
  busy.value = true
  uploadError.value = ''
  const form = new FormData()
  staged.value.forEach(photo => form.append('files', photo.file))
  try {
    // Reading can take a while when the AI service is busy and the server retries
    const res = await api.post('/receipts', form, { timeout: 300000 })
    staged.value.forEach(photo => URL.revokeObjectURL(photo.url))
    staged.value = []
    router.push(`/receipts/${res.data.id}`)
  } catch (e) {
    const detail = e.response?.data?.detail
    uploadError.value = typeof detail === 'string' ? detail : t('receipts.uploadFailed')
  } finally {
    busy.value = false
  }
}

function rowDate(receipt) {
  const date = receipt.purchased_at
    ? serverDate(receipt.purchased_at)
    : receipt.purchased_local
      ? new Date(receipt.purchased_local) // printed local time, no timezone
      : serverDate(receipt.created_at)
  return formatDateTime(date, locale.value)
}

onMounted(load)
onBeforeUnmount(() => staged.value.forEach(photo => URL.revokeObjectURL(photo.url)))
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.hint {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.error { color: var(--danger); font-size: 13px; margin-top: 8px; }

.thumbs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.thumb {
  position: relative;
  width: 72px;
  height: 96px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumb-remove {
  position: absolute;
  top: 2px;
  inset-inline-end: 2px;
  width: 20px;
  height: 20px;
  padding: 0;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 14px;
  line-height: 1;
}

.upload-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.upload-actions .btn-primary { margin-inline-start: auto; }

.receipt-row {
  display: block;
  color: var(--text);
  text-decoration: none;
}

.receipt-row:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18); }

.row-main {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
}

.row-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.row-total { font-weight: 600; color: var(--text); }

.status {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.status.pending { background: #fff3e0; color: #e65100; }
.status.failed { background: #ffebee; color: var(--danger); }
.status.confirmed { background: #e8f5e9; color: var(--primary-dark); }

.loading, .empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}
</style>
