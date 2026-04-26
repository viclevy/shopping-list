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
        <!-- Category groups themselves are draggable when categorySort === 'manual' -->
        <draggable
          v-model="draggableGroups"
          item-key="category"
          handle=".cat-drag-handle"
          :disabled="prefs.categorySort !== 'manual'"
          ghost-class="drag-ghost"
          @end="onCategoryDragEnd"
        >
          <template #item="{ element: group, index: groupIndex }">
            <div class="category-group">
              <div class="category-header-row">
                <div
                  v-if="prefs.categorySort === 'manual'"
                  class="cat-drag-handle"
                  :title="$t('listPreferences.dragToReorder')"
                >&#9776;</div>
                <div class="category-header">{{ group.category }}</div>
              </div>
              <!-- Items within the group are draggable when listItemSort === 'manual' -->
              <draggable
                v-model="draggableGroups[groupIndex].items"
                item-key="id"
                handle=".drag-handle"
                :disabled="prefs.listItemSort !== 'manual'"
                ghost-class="drag-ghost"
                @end="() => onItemDragEnd(groupIndex)"
              >
                <template #item="{ element: item }">
                  <ListItem
                    :item="item"
                    :show-move-buttons="prefs.listItemSort === 'manual'"
                    @check-off="openCheckOff(item)"
                    @remove="handleRemove(item)"
                  />
                </template>
              </draggable>
            </div>
          </template>
        </draggable>
      </template>

      <!-- Flat (no groups) -->
      <template v-else>
        <draggable
          v-model="draggableFlat"
          item-key="id"
          handle=".drag-handle"
          :disabled="prefs.listItemSort !== 'manual'"
          ghost-class="drag-ghost"
          @end="onFlatDragEnd"
        >
          <template #item="{ element: item }">
            <ListItem
              :item="item"
              :show-move-buttons="prefs.listItemSort === 'manual'"
              @check-off="openCheckOff(item)"
              @remove="handleRemove(item)"
            />
          </template>
        </draggable>
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
import draggable from 'vuedraggable'
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

// vuedraggable needs a writable array — we keep local copies that mirror
// the computed values and only update when the source data changes.
const draggableGroups = ref([])
const draggableFlat = ref([])

watch(groupedItems, (val) => { draggableGroups.value = val.map(g => ({ ...g, items: [...g.items] })) }, { immediate: true, deep: true })
watch(flatItems, (val) => { draggableFlat.value = [...val] }, { immediate: true, deep: true })

// ─── Drag handlers ────────────────────────────────────────────────────────────

function onCategoryDragEnd() {
  const order = draggableGroups.value.map(g => g.category)
  prefs.categoryOrder = order
  prefs.savePreferences({ category_sort: 'manual', category_order: order })
}

function onItemDragEnd(groupIndex) {
  applyItemOrder(draggableGroups.value[groupIndex].items)
}

function onFlatDragEnd() {
  applyItemOrder(draggableFlat.value)
}

async function applyItemOrder(orderedItems) {
  const payload = orderedItems.map((item, idx) => ({ id: item.id, sort_order: idx }))
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
  padding-right: 8px;
}

.category-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 10px 12px 4px;
  flex: 1;
}

.cat-drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  padding: 10px 4px 4px;
  cursor: grab;
  color: var(--text-secondary);
  opacity: 0.4;
  font-size: 15px;
  touch-action: none;
  user-select: none;
}

.cat-drag-handle:hover {
  opacity: 0.8;
}

.cat-drag-handle:active {
  cursor: grabbing;
}

.drag-ghost {
  opacity: 0.4;
  background: var(--primary-light, #e3f0ff);
  border-radius: 8px;
}
</style>
