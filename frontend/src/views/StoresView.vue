<template>
  <div class="stores-view">
    <h2>{{ $t('stores.title') }}</h2>

    <div class="card add-form">
      <form @submit.prevent="addStore" class="form-row">
        <input v-model="newName" type="text" :placeholder="$t('stores.placeholder')" required />
        <button type="submit" class="btn-primary" :disabled="adding">{{ $t('stores.addButton') }}</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
    <div v-else class="store-list">
      <div v-for="store in stores" :key="store.id" class="store-row card">
        <div class="store-main">
          <span class="store-name">{{ store.name }}</span>
          <div v-if="store.aliases?.length" class="alias-list">
            <span v-for="a in store.aliases" :key="a.id" class="alias-chip">
              {{ a.alias }}
              <button class="alias-remove" @click="removeAlias(store, a)" title="Remove alias">&times;</button>
            </span>
          </div>
          <div v-if="addingAliasFor === store.id" class="alias-add-row">
            <input
              v-model="newAlias"
              type="text"
              :placeholder="$t('stores.aliasName')"
              class="alias-input"
              @keydown.enter.prevent="saveAlias(store)"
              @keydown.escape="addingAliasFor = null"
              ref="aliasInput"
            />
            <button class="btn-primary btn-sm" @click="saveAlias(store)">{{ $t('stores.addAlias') }}</button>
            <button class="btn-secondary btn-sm" @click="addingAliasFor = null">{{ $t('common.cancel') }}</button>
          </div>
          <div class="store-actions-row">
            <button class="btn-secondary btn-sm" @click="startAddAlias(store)">+ Alias</button>
            <button class="btn-secondary btn-sm" @click="startMerge(store)">Merge</button>
          </div>
        </div>
        <label class="toggle" :title="store.include_in_image_search ? $t('stores.searchIncluded') : $t('stores.searchExcluded')">
          <input
            type="checkbox"
            :checked="store.include_in_image_search"
            @change="toggleImageSearch(store)"
          />
          <span class="toggle-slider"></span>
          <span class="toggle-label">Search</span>
        </label>
        <span class="store-date">{{ $t('stores.added') }} {{ formatDate(store.created_at) }}</span>
        <button
          class="btn-danger btn-sm"
          @click="deleteStore(store)"
        >{{ $t('common.delete') }}</button>
      </div>
    </div>

    <!-- Merge dialog -->
    <div v-if="mergeTarget" class="dialog-overlay" @click.self="mergeTarget = null">
      <div class="dialog card">
        <h3>{{ $t('stores.mergeTitle') }}</h3>
        <p class="merge-desc">{{ $t('stores.mergeDesc') }} {{ $t('stores.allProductLinksWillBeMoved') }}</p>
        <div class="merge-list">
          <button
            v-for="store in mergeOptions"
            :key="store.id"
            class="merge-option"
            @click="doMerge(store)"
          >{{ store.name }}</button>
        </div>
        <div class="dialog-actions">
          <button class="btn-secondary" @click="mergeTarget = null">{{ $t('common.cancel') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'

const { t } = useI18n()

const stores = ref([])
const loading = ref(false)
const adding = ref(false)
const newName = ref('')
const error = ref('')
const addingAliasFor = ref(null)
const newAlias = ref('')
const mergeTarget = ref(null)
const aliasInput = ref(null)

const mergeOptions = computed(() => {
  if (!mergeTarget.value) return []
  return stores.value.filter(s => s.id !== mergeTarget.value.id)
})

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
      warnings.push(`${preview.history_events} ${t(preview.history_events === 1 ? 'stores.historyEventSingular' : 'stores.historyEventPlural')}`)
    }
    if (preview.product_links > 0) {
      warnings.push(`${preview.product_links} ${t(preview.product_links === 1 ? 'stores.productLinkSingular' : 'stores.productLinkPlural')}`)
    }
    let msg = t('stores.confirmDelete', { name: store.name })
    if (warnings.length > 0) {
      msg += `\n\n${t('stores.willPermanentlyDelete')}\n- ${warnings.join('\n- ')}`
    }
    if (!confirm(msg)) return
    await api.delete(`/stores/${store.id}`)
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to delete store'
  }
}

function startAddAlias(store) {
  addingAliasFor.value = store.id
  newAlias.value = ''
  nextTick(() => {
    if (aliasInput.value) {
      const input = Array.isArray(aliasInput.value) ? aliasInput.value[0] : aliasInput.value
      input?.focus()
    }
  })
}

async function saveAlias(store) {
  if (!newAlias.value.trim()) return
  error.value = ''
  try {
    await api.post(`/stores/${store.id}/aliases`, { alias: newAlias.value.trim() })
    addingAliasFor.value = null
    newAlias.value = ''
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to add alias'
  }
}

async function removeAlias(store, alias) {
  if (!confirm(t('stores.confirmRemoveAlias', { alias: alias.alias }))) return
  error.value = ''
  try {
    await api.delete(`/stores/${store.id}/aliases/${alias.id}`)
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to remove alias'
  }
}

function startMerge(store) {
  mergeTarget.value = store
}

async function doMerge(otherStore) {
  if (!confirm(t('stores.confirmMerge', { sourceStore: otherStore.name, targetStore: mergeTarget.value.name }))) return
  error.value = ''
  try {
    await api.post(`/stores/${mergeTarget.value.id}/merge/${otherStore.id}`)
    mergeTarget.value = null
    await loadStores()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to merge stores'
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

.store-main {
  flex: 1;
  min-width: 0;
}

.store-name {
  font-weight: 500;
}

.alias-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.alias-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  background: var(--border);
  color: var(--text-secondary);
}

.alias-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  padding: 0 2px;
  line-height: 1;
}

.alias-remove:hover {
  color: var(--danger);
}

.alias-add-row {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  align-items: center;
}

.alias-input {
  flex: 1;
  font-size: 12px;
  padding: 4px 8px;
}

.store-actions-row {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}

.store-date {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
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

/* Merge dialog */
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
  max-width: 400px;
  padding: 24px;
  max-height: 80vh;
  overflow-y: auto;
}

.dialog h3 { margin-bottom: 8px; }

.merge-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.merge-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.merge-option {
  display: block;
  width: 100%;
  padding: 10px 12px;
  text-align: left;
  background: var(--border);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.15s;
}

.merge-option:hover {
  background: #e0e0e0;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
