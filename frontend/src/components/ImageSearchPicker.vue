<template>
  <div class="image-search-picker">
    <div class="search-bar">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="$t('imageSearch.title')"
        @keydown.enter.prevent="doSearch"
      />
      <button class="btn-secondary" @click="doSearch" :disabled="searching">
        {{ searching ? $t('newItemSetup.searching') : $t('common.search') }}
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

    <div v-if="images.length && hasMore" class="load-more-wrap">
      <button class="btn-secondary load-more-btn" @click="loadMore" :disabled="loadingMore">
        {{ loadingMore ? $t('common.loading') : $t('imageSearch.loadMore') }}
      </button>
    </div>

    <div v-else-if="searched && !searching" class="no-results">
      {{ $t('imageSearch.noResults') }}
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'

const { t } = useI18n()

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
const nextStart = ref(10)
const hasMore = ref(true)
const loadingMore = ref(false)

watch(() => props.query, (val) => {
  if (val && val !== searchQuery.value) {
    searchQuery.value = val
  }
})

watch(() => props.initialImages, (val) => {
  if (val?.length && !images.value.length) {
    images.value = [...val]
    searched.value = true
    nextStart.value = 10
    hasMore.value = true
  }
})

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q || searching.value) return
  searching.value = true
  searched.value = true
  hasMore.value = true
  try {
    const res = await api.get('/search/images', { params: { q } })
    images.value = res.data || []
    nextStart.value = 10
    if (!images.value.length) hasMore.value = false
  } catch {
    images.value = []
    hasMore.value = false
  } finally {
    searching.value = false
  }
}

async function loadMore() {
  const q = searchQuery.value.trim()
  if (!q || loadingMore.value) return
  loadingMore.value = true
  try {
    const res = await api.get('/search/images', { params: { q, start: nextStart.value } })
    const newImages = res.data || []
    if (newImages.length) {
      const existingUrls = new Set(images.value.map(img => img.url))
      const unique = newImages.filter(img => !existingUrls.has(img.url))
      images.value = [...images.value, ...unique]
      nextStart.value += 10
    } else {
      hasMore.value = false
    }
  } catch {
    hasMore.value = false
  } finally {
    loadingMore.value = false
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
      alert(t('errors.addFailed'))
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

.load-more-wrap {
  text-align: center;
  margin-top: 12px;
}

.load-more-btn {
  font-size: 13px;
  width: 100%;
}

.no-results {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 12px;
}
</style>
