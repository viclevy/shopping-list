<template>
  <div class="shopping-list-view">
    <AddItemBar @new-product="openSetupDialog" />
    <ListSortControls />
    <div v-if="list.loading && !list.items.length" class="loading">{{ $t('common.loading') }}</div>
    <div v-else-if="!list.items.length" class="empty">
      <p>{{ $t('shoppingList.empty') }}</p>
      <p class="empty-hint">{{ $t('shoppingList.emptyHint') }}</p>
    </div>
    <div v-else class="list">
      <!-- Grouped by category -->
      <template v-if="prefs.listGrouping === 'category'">
        <div v-for="group in groupedItems" :key="group.category" class="category-group">
          <div class="category-header-row">
            <div class="category-header">{{ group.category }}</div>
            <div v-if="prefs.categorySort === 'manual'" class="cat-move-btns">
              <button class="btn-move" :disabled="isFirstCategory(group.category)" @click="moveCategoryUp(group.category)" title="Move category up">▲</button>
              <button class="btn-move" :disabled="isLastCategory(group.category)" @click="moveCategoryDown(group.category)" title="Move category down">▼</button>
            </div>
          </div>
          <ListItem
            v-for="(item, idx) in group.items"
            :key="item.id"
            :item="item"
            :show-move-buttons="prefs.listItemSort === 'manual'"
            :is-first="idx === 0"
            :is-last="idx === group.items.length - 1"
            @check-off="openCheckOff(item)"
            @remove="handleRemove(item)"
            @move-up="moveItemUp(item, group.items)"
            @move-down="moveItemDown(item, group.items)"
          />
        </div>
      </template>

      <!-- Flat (no groups) -->
      <template v-else>
        <ListItem
          v-for="(item, idx) in flatItems"
          :key="item.id"
          :item="item"
          :show-move-buttons="prefs.listItemSort === 'manual'"
          :is-first="idx === 0"
          :is-last="idx === flatItems.length - 1"
          @check-off="openCheckOff(item)"
          @remove="handleRemove(item)"
          @move-up="moveItemUp(item, flatItems)"
          @move-down="moveItemDown(item, flatItems)"
        />
      </template>
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
import { useI18n } from 'vue-i18n'
import api from '../api.js'
import { useShoppingListStore } from '../stores/shoppingList.js'
import { usePreferencesStore } from '../stores/preferences.js'
import AddItemBar from '../components/AddItemBar.vue'
import ListItem from '../components/ListItem.vue'
import ListSortControls from '../components/ListSortControls.vue'
import BoughtBeforeSection from '../components/BoughtBeforeSection.vue'
import CheckOffDialog from '../components/CheckOffDialog.vue'
import NewItemSetupDialog from '../components/NewItemSetupDialog.vue'

const { t } = useI18n()

const list = useShoppingListStore()
const prefs = usePreferencesStore()

// ─── Sorting helpers ──────────────────────────────────────────────────────────

function sortItems(items) {
  const arr = [...items]
  if (prefs.listItemSort === 'alpha-asc') {
    arr.sort((a, b) => a.product.name.localeCompare(b.product.name))
  } else if (prefs.listItemSort === 'alpha-desc') {
    arr.sort((a, b) => b.product.name.localeCompare(a.product.name))
  } else {
    // manual — sort by sort_order (nulls last), fallback to added_at
    arr.sort((a, b) => {
      if (a.sort_order == null && b.sort_order == null) return new Date(a.added_at) - new Date(b.added_at)
      if (a.sort_order == null) return 1
      if (b.sort_order == null) return -1
      return a.sort_order - b.sort_order
    })
  }
  return arr
}

function categoryFrequency(category) {
  // Count total purchase_count from boughtBefore for items in this category
  // We approximate by counting items in the current list belonging to this category
  // against the boughtBefore analytics
  const bbMap = {}
  for (const bb of list.boughtBefore) {
    bbMap[bb.product_id] = bb.purchase_count || 0
  }
  let total = 0
  for (const item of list.items) {
    if ((item.product.category || 'Uncategorized') === category) {
      total += bbMap[item.product.id] || 0
    }
  }
  return total
}

function sortedCategoryNames(categories) {
  const arr = [...categories]
  if (prefs.categorySort === 'alpha-asc') {
    arr.sort((a, b) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      return a.localeCompare(b)
    })
  } else if (prefs.categorySort === 'alpha-desc') {
    arr.sort((a, b) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      return b.localeCompare(a)
    })
  } else if (prefs.categorySort === 'frequency') {
    arr.sort((a, b) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      return categoryFrequency(b) - categoryFrequency(a)
    })
  } else {
    // manual — use stored categoryOrder, unknown categories go last
    const order = prefs.categoryOrder || []
    arr.sort((a, b) => {
      if (a === 'Uncategorized') return 1
      if (b === 'Uncategorized') return -1
      const ia = order.indexOf(a)
      const ib = order.indexOf(b)
      if (ia === -1 && ib === -1) return a.localeCompare(b)
      if (ia === -1) return 1
      if (ib === -1) return -1
      return ia - ib
    })
  }
  return arr
}

// ─── Computed ─────────────────────────────────────────────────────────────────

const groupedItems = computed(() => {
  const groups = {}
  for (const item of list.items) {
    const cat = item.product.category || 'Uncategorized'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(item)
  }
  const cats = sortedCategoryNames(Object.keys(groups))
  return cats.map(cat => ({ category: cat, items: sortItems(groups[cat]) }))
})

const flatItems = computed(() => sortItems(list.items))

// ─── Category manual sort ─────────────────────────────────────────────────────

function isFirstCategory(cat) {
  return groupedItems.value[0]?.category === cat
}

function isLastCategory(cat) {
  return groupedItems.value[groupedItems.value.length - 1]?.category === cat
}

function moveCategoryUp(cat) {
  const order = groupedItems.value.map(g => g.category)
  const idx = order.indexOf(cat)
  if (idx <= 0) return
  ;[order[idx - 1], order[idx]] = [order[idx], order[idx - 1]]
  prefs.categoryOrder = order
  prefs.savePreferences({ category_order: order })
}

function moveCategoryDown(cat) {
  const order = groupedItems.value.map(g => g.category)
  const idx = order.indexOf(cat)
  if (idx < 0 || idx >= order.length - 1) return
  ;[order[idx], order[idx + 1]] = [order[idx + 1], order[idx]]
  prefs.categoryOrder = order
  prefs.savePreferences({ category_order: order })
}

// ─── Item manual sort ─────────────────────────────────────────────────────────

async function moveItemUp(item, items) {
  const idx = items.findIndex(i => i.id === item.id)
  if (idx <= 0) return
  const reordered = [...items]
  ;[reordered[idx - 1], reordered[idx]] = [reordered[idx], reordered[idx - 1]]
  await applyItemOrder(reordered)
}

async function moveItemDown(item, items) {
  const idx = items.findIndex(i => i.id === item.id)
  if (idx < 0 || idx >= items.length - 1) return
  const reordered = [...items]
  ;[reordered[idx], reordered[idx + 1]] = [reordered[idx + 1], reordered[idx]]
  await applyItemOrder(reordered)
}

async function applyItemOrder(orderedItems) {
  const payload = orderedItems.map((item, idx) => ({ id: item.id, sort_order: idx }))
  // optimistic update
  for (const entry of payload) {
    const item = list.items.find(i => i.id === entry.id)
    if (item) item.sort_order = entry.sort_order
  }
  await api.put('/list/reorder', payload)
}

// ─── Dialogs ──────────────────────────────────────────────────────────────────

const checkOffVisible = ref(false)
const checkOffItem = ref(null)
const setupDialogVisible = ref(false)
const setupProduct = ref(null)

onMounted(() => {
  list.fetchItems()
  list.fetchBoughtBefore()
  prefs.fetchPreferences()
})

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
  if (confirm(t('common.confirmRemoveItem', { name: item.product.name }))) {
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
  margin-top: 8px;
}

.category-group {
  margin-bottom: 8px;
}

.category-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 8px;
}

.category-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 12px 4px;
}

.cat-move-btns {
  display: flex;
  gap: 2px;
}

.btn-move {
  background: none;
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 5px;
  cursor: pointer;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1;
}

.btn-move:disabled {
  opacity: 0.3;
  cursor: default;
}

.btn-move:not(:disabled):hover {
  background: var(--border);
}
</style>
