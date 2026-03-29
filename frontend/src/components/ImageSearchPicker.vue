<template>
  <div class="image-search-picker">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search for images..."
        @keydown.enter.prevent="doSearch"
      />
      <button class="btn-secondary" @click="doSearch" :disabled="searching">
        {{ searching ? 'Searching...' : 'Search' }}
      </button>
    </div>

    <div v-if="images.length" class="image-grid">
      <div
        v-for="(img, i) in images"
        :key="i"
        :class="['image-option', { selected: selectedUrl === img.url, saving: savingUrl === img.url }]"
        @click="selectImage(img)"
      >
        <img :src="img.url" :alt="img.name" />
        <span class="image-store">{{ img.store }}</span>
      </div>
    </div>

    <div v-else-if="searched && !searching" class="no-results">
      No images found
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../api.js'

const props = defineProps({
  productId: { type: Number, default: null },
  query: { type: String, default: '' },
  initialImages: { type: Array, default: () => [] },
})

const emit = defineEmits(['select', 'saved'])

const searchQuery = ref(props.query)
const images = ref([...props.initialImages])
const searching = ref(false)
const searched = ref(props.initialImages.length > 0)
const selectedUrl = ref(null)
const savingUrl = ref(null)

watch(() => props.query, (val) => {
  if (val && val !== searchQuery.value) {
    searchQuery.value = val
  }
})

watch(() => props.initialImages, (val) => {
  if (val?.length && !images.value.length) {
    images.value = [...val]
    searched.value = true
  }
})

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q || searching.value) return
  searching.value = true
  searched.value = true
  try {
    const res = await api.get('/search/images', { params: { q } })
    images.value = res.data || []
  } catch {
    images.value = []
  } finally {
    searching.value = false
  }
}

async function selectImage(img) {
  selectedUrl.value = img.url

  if (props.productId) {
    // Save directly to the product
    savingUrl.value = img.url
    try {
      await api.post(`/products/${props.productId}/photos/from-url`, {
        url: img.url,
        set_primary: true,
      })
      emit('saved')
    } catch {
      alert('Failed to save image')
    } finally {
      savingUrl.value = null
    }
  } else {
    emit('select', img.url)
  }
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.search-bar input {
  flex: 1;
  min-width: 0;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.image-option {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 3px solid transparent;
  transition: border-color 0.15s, opacity 0.15s;
  background: #f5f5f5;
}

.image-option:hover {
  border-color: var(--primary);
}

.image-option.selected {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px var(--primary);
}

.image-option.saving {
  opacity: 0.5;
  pointer-events: none;
}

.image-option img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.image-store {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0,0,0,0.6);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  text-align: center;
}

.no-results {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 12px;
}
</style>
