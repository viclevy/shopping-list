<template>
  <div v-if="visible" class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog card">
      <h3>Set up: {{ product?.name }}</h3>

      <div v-if="loading" class="loading-section">
        <div class="spinner"></div>
        <div class="loading-text">Looking up product info...</div>
      </div>

      <div v-if="images.length || !loading" class="field">
        <label>Product Image</label>
        <ImageSearchPicker
          :product-id="product?.id"
          :query="product?.name || ''"
          :initial-images="images"
          @saved="onImageSaved"
          @select="onImageSelected"
        />
      </div>

      <div class="field">
        <label>Category</label>
        <input v-model="category" type="text" placeholder="e.g. Dairy, Produce..." />
        <div class="category-chips">
          <button
            v-for="cat in categories"
            :key="cat"
            :class="['chip', { active: category === cat }]"
            @click="category = cat"
          >{{ cat }}</button>
        </div>
      </div>

      <div v-if="storePrices.length" class="field">
        <label>Store Prices</label>
        <div class="store-price-list">
          <a
            v-for="sp in storePrices"
            :key="sp.store"
            :href="sp.url"
            target="_blank"
            rel="noopener"
            class="store-price-row"
          >
            <span class="sp-store">{{ sp.store }}</span>
            <span class="sp-name">{{ sp.name }}</span>
            <span class="sp-price">{{ sp.price_display || ('$' + sp.price?.toFixed(2)) }}</span>
          </a>
        </div>
      </div>

      <div v-else-if="suggestedPrice" class="field">
        <label>Typical Price</label>
        <div class="price-display">${{ suggestedPrice.toFixed(2) }}</div>
      </div>

      <div v-if="suggestedStores.length" class="field">
        <label>Available at</label>
        <div class="store-chips">
          <span v-for="store in suggestedStores" :key="store" class="store-chip">{{ store }}</span>
        </div>
      </div>

      <div class="dialog-actions">
        <button class="btn-secondary" @click="$emit('close')">Skip</button>
        <button class="btn-primary" @click="save" :disabled="saving">Save</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import api from '../api.js'
import ImageSearchPicker from './ImageSearchPicker.vue'

const props = defineProps({
  visible: Boolean,
  product: { type: Object, default: null },
})

const emit = defineEmits(['close', 'saved'])

const categories = [
  'Produce', 'Dairy', 'Meat', 'Seafood', 'Bakery', 'Frozen',
  'Snacks', 'Beverages', 'Household', 'Health', 'Personal Care',
  'Canned Goods', 'Condiments', 'Cereal', 'Pasta', 'Deli',
]

const category = ref('')
const suggestedPrice = ref(null)
const suggestedStores = ref([])
const storePrices = ref([])
const images = ref([])
const selectedImageUrl = ref(null)
const loading = ref(false)
const saving = ref(false)

watch(() => props.visible, async (val) => {
  if (val && props.product) {
    category.value = props.product.category || ''
    suggestedPrice.value = null
    suggestedStores.value = []
    storePrices.value = []
    images.value = []
    selectedImageUrl.value = null
    loading.value = true
    try {
      const res = await api.get('/search/suggest', { params: { q: props.product.name } })
      if (res.data.category && !category.value) {
        category.value = res.data.category
      }
      suggestedPrice.value = res.data.price || null
      suggestedStores.value = res.data.stores || []
      storePrices.value = res.data.store_prices || []
      images.value = res.data.images || []
    } catch {
      // ignore suggestion failures
    } finally {
      loading.value = false
    }
  }
})

function onImageSaved() {
  // Image was saved directly to the product by ImageSearchPicker
}

function onImageSelected(url) {
  selectedImageUrl.value = url
}

async function save() {
  if (!props.product) return
  saving.value = true
  try {
    const newCategory = category.value.trim() || null
    if (newCategory !== (props.product.category || null)) {
      await api.put(`/products/${props.product.id}`, { category: newCategory })
    }
    // If an image was selected but not yet saved (no productId at time of select)
    if (selectedImageUrl.value && props.product.id) {
      try {
        await api.post(`/products/${props.product.id}/photos/from-url`, {
          url: selectedImageUrl.value,
          set_primary: true,
        })
      } catch {
        // non-fatal — image save failure shouldn't block category save
      }
    }
    // Save store prices from scraper results
    if (storePrices.value.length && props.product.id) {
      try {
        await api.post(
          `/products/${props.product.id}/store-prices`,
          storePrices.value.map(sp => ({ store_name: sp.store, price: sp.price }))
        )
      } catch {
        // non-fatal
      }
    }
    emit('saved')
  } catch {
    alert('Failed to save. Please try again.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.dialog {
  width: 90%;
  max-width: 480px;
  padding: 24px;
  max-height: 90vh;
  overflow-y: auto;
}

.dialog h3 {
  margin-bottom: 16px;
}

.field {
  margin-bottom: 16px;
}

.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.category-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.chip {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: var(--border);
  color: var(--text);
  cursor: pointer;
  border: none;
}

.chip.active {
  background: var(--primary);
  color: white;
}

.price-display {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}

.store-price-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.store-price-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--border);
  border-radius: 8px;
  text-decoration: none;
  color: var(--text);
  font-size: 13px;
  transition: background 0.15s;
}

.store-price-row:hover {
  background: #e0e0e0;
}

.sp-store {
  font-weight: 600;
  min-width: 60px;
}

.sp-name {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-secondary);
}

.sp-price {
  font-weight: 600;
  color: var(--primary);
  white-space: nowrap;
}

.store-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}

.store-chip {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: var(--border);
  color: var(--text);
}

.loading-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  text-align: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
