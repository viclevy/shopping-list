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

async function deleteStore(store) {
  if (!confirm(`Delete store "${store.name}"?`)) return
  await api.delete(`/stores/${store.id}`)
  await loadStores()
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

.loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}
</style>
