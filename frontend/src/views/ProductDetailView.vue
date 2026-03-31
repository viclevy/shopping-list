<template>
  <div v-if="product" class="product-detail">
    <div class="card">
      <div class="detail-header">
        <button class="back-btn" @click="$router.back()" title="Back">&larr;</button>
        <h2>{{ product.name }}</h2>
        <span v-if="product.category" class="category-badge">{{ product.category }}</span>
      </div>

      <div class="section">
        <h3>Details</h3>
        <div class="edit-fields">
          <div class="field">
            <label>Name</label>
            <input v-model="editName" type="text" />
          </div>
          <div class="field">
            <label>Category</label>
            <input v-model="editCategory" type="text" placeholder="e.g. Dairy, Produce..." :class="{ suggesting: suggestingCategory }" />
            <span v-if="suggestingCategory" class="suggest-hint">Suggesting...</span>
          </div>
          <button class="btn-primary" @click="saveDetails" :disabled="saving">
            {{ saving === 'done' ? 'Saved!' : 'Save' }}
          </button>
        </div>
      </div>

      <div class="section">
        <h3>Photos</h3>
        <div v-if="product.photos?.length" class="photo-gallery">
          <div v-for="photo in product.photos" :key="photo.id" class="photo-wrap">
            <img :src="`/uploads/${photo.filename}`" class="photo-img" />
            <button
              class="photo-primary"
              :class="{ active: photo.is_primary }"
              title="Set as primary"
              @click="setPrimary(photo.id)"
            >&#9733;</button>
            <button class="photo-delete" @click="deletePhoto(photo.id)">&times;</button>
          </div>
        </div>
        <p v-else class="no-data">No photos yet.</p>
        <PhotoPicker
          :product-id="product.id"
          :product-name="product.name"
          @photo-added="reload"
        />
        <button class="btn-secondary find-images-btn" @click="showImageSearch = !showImageSearch">
          {{ showImageSearch ? 'Hide Image Search' : 'Find Images Online' }}
        </button>
        <ImageSearchPicker
          v-if="showImageSearch"
          :product-id="product.id"
          :query="product.name"
          @saved="onImageSaved"
        />
      </div>

      <div class="section">
        <h3>Store Availability & Prices</h3>
        <table v-if="product.stores?.length" class="store-table">
          <thead><tr><th>Store</th><th>Price</th></tr></thead>
          <tbody>
            <tr v-for="ps in product.stores" :key="ps.store_id">
              <td>{{ ps.store_name }}</td>
              <td>{{ ps.price != null ? `$${ps.price.toFixed(2)}` : '—' }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="no-data">No store info.</p>
      </div>

      <div class="section">
        <h3>Purchase History</h3>
        <div v-if="history.length" class="history-list">
          <div v-for="event in history" :key="event.id" class="history-row">
            <span class="history-date">{{ formatDate(event.timestamp) }}</span>
            <span class="history-action" :class="event.action">{{ event.action }}</span>
            <span class="history-user">{{ displayName(event.username) }}</span>
            <span v-if="event.price" class="history-price">${{ event.price.toFixed(2) }}</span>
          </div>
        </div>
        <p v-else class="no-data">No history yet.</p>
      </div>
    </div>
  </div>
  <div v-else class="loading">Loading...</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api.js'
import { normalizeCategory, displayName } from '../utils.js'
import PhotoPicker from '../components/PhotoPicker.vue'
import ImageSearchPicker from '../components/ImageSearchPicker.vue'

const route = useRoute()
const router = useRouter()
const product = ref(null)
const showImageSearch = ref(false)
const history = ref([])
const editName = ref('')
const editCategory = ref('')
const saving = ref(false)
const suggestingCategory = ref(false)

async function reload() {
  const res = await api.get(`/products/${route.params.id}`)
  product.value = res.data
  editName.value = product.value.name
  editCategory.value = product.value.category || ''
}

async function suggestCategory() {
  if (editCategory.value || !product.value) return
  suggestingCategory.value = true
  try {
    const res = await api.get('/search/suggest', { params: { q: product.value.name } })
    if (res.data.category && !editCategory.value) {
      editCategory.value = res.data.category
    }
  } catch {
    // ignore suggestion failures
  } finally {
    suggestingCategory.value = false
  }
}

async function loadHistory() {
  const res = await api.get('/history', { params: { product_id: route.params.id, limit: 20 } })
  history.value = res.data
}

onMounted(async () => {
  await reload()
  await suggestCategory()
  await loadHistory()
})

async function saveDetails() {
  saving.value = true
  try {
    await api.put(`/products/${product.value.id}`, {
      name: editName.value,
      category: normalizeCategory(editCategory.value) || null,
    })
    saving.value = 'done'
    setTimeout(() => router.back(), 400)
  } catch {
    saving.value = false
  }
}

async function deletePhoto(photoId) {
  if (!confirm('Delete this photo?')) return
  await api.delete(`/products/${product.value.id}/photos/${photoId}`)
  await reload()
}

async function setPrimary(photoId) {
  await api.put(`/products/${product.value.id}/photos/${photoId}/primary`)
  await reload()
}

async function onImageSaved() {
  showImageSearch.value = false
  await reload()
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}
</script>

<style scoped>
.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.back-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text);
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
  line-height: 1;
}

.back-btn:hover {
  background: var(--text-secondary);
  color: white;
}

.category-badge {
  background: var(--primary);
  color: white;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
}

.section {
  margin-bottom: 24px;
}

.section h3 {
  font-size: 15px;
  margin-bottom: 10px;
  color: var(--text-secondary);
}

.edit-fields {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.edit-fields .field {
  flex: 1;
  min-width: 150px;
}

.edit-fields .field label {
  display: block;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.photo-gallery {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.photo-wrap {
  position: relative;
}

.photo-img {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 6px;
}

.photo-delete {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: rgba(0,0,0,0.6);
  color: white;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.photo-primary {
  position: absolute;
  bottom: 2px;
  left: 2px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(0,0,0,0.5);
  color: rgba(255,255,255,0.5);
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
  border: none;
  line-height: 1;
}

.photo-primary.active {
  color: #FFD700;
  background: rgba(0,0,0,0.7);
}

.find-images-btn {
  margin-top: 8px;
  font-size: 13px;
}

.store-table {
  width: 100%;
  border-collapse: collapse;
}

.store-table th, .store-table td {
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-row {
  display: flex;
  gap: 12px;
  font-size: 13px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}

.history-date {
  color: var(--text-secondary);
  min-width: 140px;
}

.history-action {
  font-weight: 500;
  min-width: 80px;
}

.history-action.checked_off { color: var(--primary); }
.history-action.added { color: #2196F3; }
.history-action.removed { color: var(--danger); }
.history-action.modified { color: var(--warning); }

.no-data {
  color: var(--text-secondary);
  font-size: 13px;
}

.suggest-hint {
  font-size: 11px;
  color: var(--text-secondary);
  font-style: italic;
}

.suggesting {
  opacity: 0.6;
}

.loading {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
}
</style>
