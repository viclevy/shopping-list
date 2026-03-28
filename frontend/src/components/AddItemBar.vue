<template>
  <div class="add-item-bar">
    <div class="input-row">
      <div class="search-wrapper">
        <input
          ref="inputEl"
          v-model="query"
          type="text"
          placeholder="Add an item..."
          @input="handleInput"
          @keydown.enter.prevent="handleAdd"
          @keydown.escape="dropdownOpen = false"
        />
        <div v-if="dropdownOpen && results.length" class="dropdown">
          <div
            v-for="product in results"
            :key="product.id"
            class="dropdown-item"
            @click="selectProduct(product)"
          >
            <img
              v-if="product.photos?.length"
              :src="`/uploads/${product.photos[0].filename}`"
              class="dropdown-thumb"
            />
            <div class="dropdown-info">
              <span class="dropdown-name">{{ product.name }}</span>
              <span v-if="product.category" class="dropdown-cat">{{ product.category }}</span>
            </div>
          </div>
        </div>
      </div>
      <input v-model.number="quantity" type="number" min="0.1" step="any" placeholder="Qty" class="qty-input" />
      <input v-model="unit" type="text" placeholder="Unit" class="unit-input" />
      <button class="btn-primary" @click="handleAdd" :disabled="!query.trim()">Add</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useShoppingListStore } from '../stores/shoppingList.js'
import { useProductsStore } from '../stores/products.js'

const list = useShoppingListStore()
const products = useProductsStore()

const query = ref('')
const quantity = ref(1)
const unit = ref('')
const selectedProduct = ref(null)
const dropdownOpen = ref(false)
const inputEl = ref(null)

const results = ref([])

let searchTimeout = null

function handleInput() {
  selectedProduct.value = null
  clearTimeout(searchTimeout)
  if (query.value.length >= 2) {
    searchTimeout = setTimeout(async () => {
      await products.search(query.value)
      results.value = products.searchResults
      dropdownOpen.value = results.value.length > 0
    }, 300)
  } else {
    results.value = []
    dropdownOpen.value = false
  }
}

function selectProduct(product) {
  selectedProduct.value = product
  query.value = product.name
  dropdownOpen.value = false
}

async function handleAdd() {
  const name = query.value.trim()
  if (!name) return

  const data = {
    quantity: quantity.value || 1,
    unit: unit.value || null,
  }
  if (selectedProduct.value) {
    data.product_id = selectedProduct.value.id
  } else {
    data.product_name = name
  }

  await list.addItem(data)
  query.value = ''
  quantity.value = 1
  unit.value = ''
  selectedProduct.value = null
  results.value = []
  inputEl.value?.focus()
}
</script>

<style scoped>
.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.search-wrapper {
  flex: 1;
  position: relative;
}

.qty-input {
  width: 65px;
  flex-shrink: 0;
}

.unit-input {
  width: 75px;
  flex-shrink: 0;
}

.dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  max-height: 240px;
  overflow-y: auto;
  z-index: 50;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
}

.dropdown-item:hover {
  background: #f5f5f5;
}

.dropdown-thumb {
  width: 36px;
  height: 36px;
  border-radius: 4px;
  object-fit: cover;
}

.dropdown-info {
  display: flex;
  flex-direction: column;
}

.dropdown-name {
  font-size: 14px;
  font-weight: 500;
}

.dropdown-cat {
  font-size: 12px;
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .input-row {
    flex-wrap: wrap;
  }
  .search-wrapper {
    width: 100%;
  }
  .qty-input { width: 55px; }
  .unit-input { width: 65px; }
}
</style>
