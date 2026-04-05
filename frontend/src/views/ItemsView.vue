<template>
  <div class="items-view">
    <h2>{{ $t('items.title') }}</h2>

    <div class="search-bar card">
      <input
        v-model="searchQuery"
        type="text"
        :placeholder="$t('items.placeholder')"
        @input="onSearch"
      />
    </div>

    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
    <div v-else-if="!products.length" class="empty">{{ $t('items.noItems') }}</div>
    <div v-else class="item-list">
      <div v-for="product in products" :key="product.id" class="product-row card">
        <div class="product-left" @click="$router.push(`/product/${product.id}`)">
          <img v-if="thumbSrc(product)" :src="thumbSrc(product)" class="product-thumb" />
          <div v-else class="product-thumb-placeholder">?</div>
          <div class="product-info">
            <span class="product-name">{{ product.name }}</span>
            <span v-if="product.category" class="product-category">{{ product.category }}</span>
            <span class="product-date">Added {{ formatDate(product.created_at) }}</span>
          </div>
        </div>
        <button
          class="btn-danger btn-sm"
          @click="deleteProduct(product)"
        >{{ $t('common.delete') }}</button>
      </div>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'

const { t } = useI18n()

const products = ref([])
const loading = ref(false)
const error = ref('')
const searchQuery = ref('')
let searchTimeout = null

async function loadProducts(query) {
  loading.value = true
  error.value = ''
  try {
    const params = { sort: 'newest' }
    if (query) params.q = query
    const res = await api.get('/products', { params })
    products.value = res.data
  } catch {
    error.value = t('errors.loadFailed')
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    loadProducts(searchQuery.value)
  }, 300)
}

function thumbSrc(product) {
  const photos = product.photos || []
  const primary = photos.find(p => p.is_primary) || photos[0]
  if (primary) return `/uploads/${primary.filename}`
  if (product.image_url) return product.image_url
  return null
}

async function deleteProduct(product) {
  try {
    const { data: preview } = await api.get(`/products/${product.id}/delete-preview`)
    const warnings = []
    if (preview.history_events > 0) {
      warnings.push(`${preview.history_events} ${t(preview.history_events === 1 ? 'items.historyEventSingular' : 'items.historyEventPlural')}`)
    }
    if (preview.list_items > 0) {
      warnings.push(`${preview.list_items} ${t(preview.list_items === 1 ? 'items.listItemSingular' : 'items.listItemPlural')}`)
    }
    if (preview.photos > 0) {
      warnings.push(`${preview.photos} ${t(preview.photos === 1 ? 'items.photoSingular' : 'items.photoPlural')}`)
    }
    let msg = t('items.confirmDelete', { name: product.name })
    if (warnings.length > 0) {
      msg += `\n\n${t('items.willPermanentlyRemove')}\n- ${warnings.join('\n- ')}`
    }
    if (!confirm(msg)) return
    await api.delete(`/products/${product.id}`)
    products.value = products.value.filter(p => p.id !== product.id)
  } catch (e) {
    error.value = e.response?.data?.detail || t('errors.deleteFailed')
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}

onMounted(() => loadProducts())
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.search-bar {
  margin-bottom: 16px;
  padding: 8px 12px;
}

.search-bar input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 15px;
  background: transparent;
}

.product-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
}

.product-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  cursor: pointer;
  min-width: 0;
}

.product-thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.product-thumb-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 20px;
  flex-shrink: 0;
}

.product-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.product-name {
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-category {
  font-size: 13px;
  color: var(--text-secondary);
}

.product-date {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
}

.error {
  color: var(--danger);
  font-size: 13px;
  margin-top: 12px;
}

.empty,
.loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
  flex-shrink: 0;
}
</style>
