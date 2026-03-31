<template>
  <div class="shopping-list-view">
    <AddItemBar @new-product="openSetupDialog" />
    <div v-if="list.loading && !list.items.length" class="loading">Loading...</div>
    <div v-else-if="!list.items.length" class="empty">
      <p>Your shopping list is empty.</p>
      <p class="empty-hint">Add items using the input above or the voice button.</p>
    </div>
    <div v-else class="list">
      <div v-for="group in groupedItems" :key="group.category" class="category-group">
        <div class="category-header">{{ group.category }}</div>
        <ListItem
          v-for="item in group.items"
          :key="item.id"
          :item="item"
          @check-off="openCheckOff(item)"
          @remove="handleRemove(item)"
        />
      </div>
    </div>
    <BoughtBeforeSection />
    <CheckOffDialog
      :visible="checkOffVisible"
      :item="checkOffItem"
      @close="checkOffVisible = false"
      @confirm="handleCheckOff"
    />
    <NewItemSetupDialog
      :visible="setupDialogVisible"
      :product="setupProduct"
      @close="setupDialogVisible = false"
      @saved="handleSetupSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useShoppingListStore } from '../stores/shoppingList.js'
import AddItemBar from '../components/AddItemBar.vue'
import ListItem from '../components/ListItem.vue'
import BoughtBeforeSection from '../components/BoughtBeforeSection.vue'
import CheckOffDialog from '../components/CheckOffDialog.vue'
import NewItemSetupDialog from '../components/NewItemSetupDialog.vue'

const list = useShoppingListStore()

const groupedItems = computed(() => {
  const groups = {}
  for (const item of list.items) {
    const cat = item.product.category || 'Uncategorized'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(item)
  }
  return Object.keys(groups)
    .sort((a, b) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      return a.localeCompare(b)
    })
    .map(cat => ({ category: cat, items: groups[cat] }))
})

const checkOffVisible = ref(false)
const checkOffItem = ref(null)
const setupDialogVisible = ref(false)
const setupProduct = ref(null)

onMounted(() => {
  list.fetchItems()
  list.fetchBoughtBefore()
})

// Watch for voice-added new products that need setup
watch(() => list.pendingSetupProduct, (product) => {
  if (product) {
    openSetupDialog(product)
    list.pendingSetupProduct = null
  }
})

function openCheckOff(item) {
  checkOffItem.value = item
  checkOffVisible.value = true
}

async function handleCheckOff(data) {
  await list.checkOff(checkOffItem.value.id, data)
  checkOffVisible.value = false
  checkOffItem.value = null
}

async function handleRemove(item) {
  if (confirm(`Remove "${item.product.name}" from the list?`)) {
    await list.removeItem(item.id)
  }
}

function openSetupDialog(product) {
  setupProduct.value = product
  setupDialogVisible.value = true
}

function handleSetupSaved() {
  setupDialogVisible.value = false
  setupProduct.value = null
  list.fetchItems()
}
</script>

<style scoped>
.shopping-list-view {
  padding-top: 8px;
}

.loading, .empty {
  text-align: center;
  padding: 48px 16px;
  color: var(--text-secondary);
}

.empty-hint {
  font-size: 13px;
  margin-top: 8px;
}

.list {
  margin-top: 16px;
}

.category-group {
  margin-bottom: 8px;
}

.category-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 12px 4px;
}
</style>
