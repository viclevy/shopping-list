<template>
  <div class="photo-picker">
    <div class="picker-tabs">
      <button :class="{ active: tab === 'search' }" @click="tab = 'search'">Search</button>
      <button :class="{ active: tab === 'camera' }" @click="tab = 'camera'">Camera</button>
      <button :class="{ active: tab === 'upload' }" @click="tab = 'upload'">Upload</button>
    </div>

    <div v-if="tab === 'search'" class="picker-content">
      <div class="search-row">
        <input v-model="searchQuery" type="text" placeholder="Search for product image..." />
        <button class="btn-primary" @click="searchImages" :disabled="searching">Search</button>
      </div>
      <div v-if="imageResults.length" class="image-grid">
        <img
          v-for="(img, idx) in imageResults"
          :key="idx"
          :src="img.thumbnail"
          :title="img.title"
          @click="selectImage(img)"
          class="image-option"
        />
      </div>
      <p v-if="searched && !imageResults.length" class="no-results">No images found.</p>
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
import api from '../api.js'

const props = defineProps({
  productId: { type: Number, required: true },
  productName: { type: String, default: '' },
})

const emit = defineEmits(['photo-added'])

const tab = ref('search')
const searchQuery = ref(props.productName)
const imageResults = ref([])
const searching = ref(false)
const searched = ref(false)

async function searchImages() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searched.value = true
  try {
    const res = await api.get('/search/images', { params: { q: searchQuery.value } })
    imageResults.value = res.data.results || []
  } catch {
    imageResults.value = []
  } finally {
    searching.value = false
  }
}

async function selectImage(img) {
  try {
    await api.post('/search/images/download', {
      url: img.url,
      product_id: props.productId,
    })
    emit('photo-added')
  } catch {
    alert('Failed to download image')
  }
}

async function handleFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post(`/products/${props.productId}/photos`, formData)
    emit('photo-added')
  } catch {
    alert('Failed to upload photo')
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

.search-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-row input { flex: 1; }

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 8px;
}

.image-option {
  width: 100%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: 4px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.2s;
}

.image-option:hover {
  border-color: var(--primary);
}

.no-results {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 16px;
}

.picker-content input[type="file"] {
  border: none;
  padding: 8px 0;
}
</style>
