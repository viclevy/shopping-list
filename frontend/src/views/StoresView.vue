<template>
  <div class="stores-view">
    <h2>Stores</h2>

    <div class="card add-form">
      <form @submit.prevent="addStore" class="form-row">
        <input v-model="newName" type="text" placeholder="New store name..." required />
        <button type="submit" class="btn-primary" :disabled="adding">Add Store</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else class="store-list">
      <div v-for="store in stores" :key="store.id" class="store-row card">
        <span class="store-name">{{ store.name }}</span>
        <label class="toggle" :title="store.include_in_image_search ? 'Included in image search' : 'Excluded from image search'">
          <input
            type="checkbox"
            :checked="store.include_in_image_search"
            @change="toggleImageSearch(store)"
          />
          <span class="toggle-slider"></span>
          <span class="toggle-label">Search</span>
        </label>
        <span class="store-date">Added {{ formatDate(store.created_at) }}</span>
        <button
          class="btn-danger btn-sm"
          @click="deleteStore(store)"
        >Delete</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const stores = ref([])
const loading = ref(false)
const adding = ref(false)
const newName = ref('')
const error = ref('')

async function loadStores() {
  loading.value = true
  try {
    const res = await api.get('/stores')
    stores.value = res.data
  } finally {
    loading.value = false
  }
}

async function addStore() {
  adding.value = true
  error.value = ''
  try {
    await api.post('/stores', { name: newName.value })
    newName.value = ''
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to add store'
  } finally {
    adding.value = false
  }
}

async function toggleImageSearch(store) {
  try {
    const { data } = await api.patch(`/stores/${store.id}`, {
      include_in_image_search: !store.include_in_image_search,
    })
    store.include_in_image_search = data.include_in_image_search
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to update store'
  }
}

async function deleteStore(store) {
  try {
    const { data: preview } = await api.get(`/stores/${store.id}/delete-preview`)
    const warnings = []
    if (preview.history_events > 0) {
      warnings.push(`${preview.history_events} history event${preview.history_events === 1 ? '' : 's'}`)
    }
    if (preview.product_links > 0) {
      warnings.push(`${preview.product_links} product-store link${preview.product_links === 1 ? '' : 's'}`)
    }
    let msg = `Delete store "${store.name}"?`
    if (warnings.length > 0) {
      msg += `\n\nThis will permanently delete:\n- ${warnings.join('\n- ')}`
    }
    if (!confirm(msg)) return
    await api.delete(`/stores/${store.id}`)
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to delete store'
  }
}

onMounted(loadStores)

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.add-form { margin-bottom: 20px; }

.form-row {
  display: flex;
  gap: 8px;
}

.form-row input { flex: 1; }

.error {
  color: var(--danger);
  font-size: 13px;
  margin-top: 8px;
}

.store-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.store-name {
  font-weight: 500;
  flex: 1;
}

.store-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}

.toggle input { display: none; }

.toggle-slider {
  position: relative;
  width: 36px;
  height: 20px;
  background: #ccc;
  border-radius: 10px;
  transition: background 0.2s;
}

.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.toggle input:checked + .toggle-slider {
  background: var(--primary);
}

.toggle input:checked + .toggle-slider::after {
  transform: translateX(16px);
}

.toggle-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}
</style>
