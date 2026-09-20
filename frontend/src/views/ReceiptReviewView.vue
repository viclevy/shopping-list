<template>
  <div class="receipt-view">
    <router-link to="/receipts" class="back">&larr; {{ $t('receipts.title') }}</router-link>

    <div v-if="loading" class="loading">{{ $t('common.loading') }}</div>
    <div v-else-if="loadError" class="card error">{{ loadError }}</div>

    <template v-else-if="receipt">
      <div v-if="images.length" class="card">
        <div class="thumbs">
          <button v-for="img in images" :key="img.id" class="thumb" @click="viewer = img.url">
            <img :src="img.url" alt="" />
          </button>
        </div>
      </div>

      <div v-if="summary.length" class="card success">
        <p v-for="line in summary" :key="line">{{ line }}</p>
      </div>
      <p v-if="actionError" class="card error">{{ actionError }}</p>

      <!-- Reading failed -->
      <div v-if="receipt.status === 'failed'" class="card">
        <h3>{{ $t('receipts.failedTitle') }}</h3>
        <p class="error">{{ receipt.error }}</p>
        <div class="actions">
          <button class="btn-primary" :disabled="working" @click="retry">
            {{ working ? $t('receipts.reading') : $t('receipts.tryAgain') }}
          </button>
          <button class="btn-danger" :disabled="working" @click="remove">{{ $t('receipts.deleteReceipt') }}</button>
        </div>
      </div>

      <!-- Waiting for review -->
      <template v-else-if="receipt.status === 'pending'">
        <div class="card">
          <div class="field">
            <label for="receipt-store">{{ $t('receipts.store') }}</label>
            <select id="receipt-store" v-model="storeId" @change="onStoreChange">
              <option :value="null">{{ $t('receipts.chooseStore') }}</option>
              <option v-for="s in stores" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
            <p v-if="!receipt.store_id && receipt.store_text" class="hint">
              {{ $t('receipts.printedAs', { name: receipt.store_text }) }}
              <button class="link" @click="addStore">{{ $t('receipts.addAsStore') }}</button>
            </p>
          </div>
          <div class="field">
            <label for="receipt-when">{{ $t('receipts.purchasedAt') }}</label>
            <input id="receipt-when" v-model="purchased" type="datetime-local" />
          </div>
          <div class="totals">
            <span>{{ $t('receipts.receiptTotal') }}: <strong>{{ formatMoney(receipt.total) }}</strong></span>
            <span v-if="receipt.tax">{{ $t('receipts.tax') }}: {{ formatMoney(receipt.tax) }}</span>
            <span>{{ $t('receipts.recording') }}: <strong>{{ formatMoney(recordingTotal) }}</strong></span>
          </div>
          <p v-if="!receipt.check" class="warn">&#9888; {{ $t('receipts.noTotal') }}</p>
          <p v-else-if="receipt.check.balanced" class="ok">&#10003; {{ $t('receipts.balanced') }}</p>
          <p v-else class="warn">
            &#9888;
            {{ $t('receipts.unbalanced', {
              lines: formatMoney(receipt.check.lines_sum),
              expected: formatMoney(receipt.check.expected_total),
              total: formatMoney(receipt.total),
            }) }}
          </p>
        </div>

        <div v-for="row in rows" :key="row.id" class="card line" :class="{ skipped: row.ignore }">
          <template v-if="row.ignore">
            <div class="line-head">
              <span class="raw" dir="ltr">{{ row.raw }}</span>
              <span class="badge">{{ row.type === 'fee' ? $t('receipts.fee') : $t('receipts.skipped') }}</span>
              <span class="static-amount">{{ formatMoney(parseAmount(row.amountText)) }}</span>
              <button class="btn-secondary btn-sm" @click="include(row)">{{ $t('receipts.include') }}</button>
            </div>
          </template>

          <template v-else>
            <div class="line-head">
              <span class="raw" dir="ltr">{{ row.raw }}</span>
              <span v-if="row.section" class="badge" dir="ltr">{{ row.section }}</span>
            </div>

            <div class="product-area">
              <div v-if="row.mode === 'existing'" class="chosen">
                <strong>{{ row.productName }}</strong>
                <span v-if="row.source" class="badge" :class="row.source">
                  {{ row.source === 'learned' ? $t('receipts.matchLearned') : $t('receipts.matchSuggested') }}
                </span>
                <button class="link" @click="startPick(row)">{{ $t('receipts.change') }}</button>
              </div>

              <div v-else-if="row.mode === 'pick'" class="picker">
                <input
                  v-model="row.query"
                  type="text"
                  autocomplete="off"
                  :placeholder="$t('receipts.searchProducts')"
                  @input="touch(row)"
                />
                <ul v-if="matches(row).length || row.query.trim()" class="suggestions">
                  <li v-for="p in matches(row)" :key="p.id" @mousedown.prevent="choose(row, p)">
                    {{ p.name }} <small v-if="p.category">{{ p.category }}</small>
                  </li>
                  <li v-if="row.query.trim()" class="create" @mousedown.prevent="createNew(row, row.query)">
                    {{ $t('receipts.createNew', { name: row.query.trim() }) }}
                  </li>
                </ul>
                <button class="link" @click="cancelPick(row)">{{ $t('common.cancel') }}</button>
              </div>

              <div v-else class="new-product">
                <input v-model="row.newName" type="text" :placeholder="$t('receipts.newProductName')" @input="touch(row)" />
                <input
                  v-model="row.category"
                  type="text"
                  list="receipt-categories"
                  :placeholder="$t('receipts.category')"
                  @input="touch(row)"
                />
                <button class="link" @click="startPick(row)">{{ $t('receipts.chooseExisting') }}</button>
              </div>
            </div>

            <div class="numbers">
              <label>
                <span>{{ $t('receipts.quantity') }}</span>
                <input v-model="row.quantity" type="number" min="0" step="any" inputmode="decimal" @input="touch(row)" />
              </label>
              <label>
                <span>{{ $t('receipts.amount') }}</span>
                <input v-model="row.amountText" type="text" inputmode="decimal" dir="ltr" @input="touch(row)" />
              </label>
              <button class="btn-secondary btn-sm skip" @click="skip(row)">{{ $t('common.skip') }}</button>
            </div>
            <p v-if="row.discounted" class="hint">{{ $t('receipts.afterDiscounts', { was: formatMoney(row.wasTotal) }) }}</p>
          </template>
        </div>

        <datalist id="receipt-categories">
          <option v-for="c in categories" :key="c" :value="c" />
        </datalist>

        <div class="confirm-bar">
          <p v-if="!canConfirm" class="hint">{{ $t('receipts.needsChoices') }}</p>
          <div class="actions">
            <button class="btn-primary" :disabled="working || !canConfirm" @click="confirmReceipt">
              {{ working ? $t('receipts.confirming') : $t('receipts.confirm') }}
            </button>
            <button class="btn-secondary" :disabled="working" @click="remove">{{ $t('receipts.deleteReceipt') }}</button>
          </div>
        </div>
      </template>

      <!-- Recorded -->
      <template v-else>
        <div class="card">
          <div class="line-head">
            <strong>{{ receipt.store_name || receipt.store_text }}</strong>
            <span class="status confirmed">{{ $t('receipts.status.confirmed') }}</span>
          </div>
          <p class="hint">
            {{ formatDateTime(serverDate(receipt.purchased_at), locale) }} &middot; {{ formatMoney(receipt.total) }}
          </p>
          <ul class="recorded-lines">
            <li v-for="l in recordedLines" :key="l.id" :class="{ skipped: l.ignored }">
              <router-link v-if="l.product_id" :to="`/product/${l.product_id}`">{{ l.product_name }}</router-link>
              <span v-else dir="ltr">{{ l.raw_text }}</span>
              <span class="qty">&times;{{ l.quantity }}</span>
              <span class="amt">{{ l.ignored ? $t('receipts.skipped') : formatMoney(l.net_amount) }}</span>
            </li>
          </ul>
        </div>
        <div class="actions">
          <router-link to="/receipts" class="btn-link btn-primary">{{ $t('receipts.title') }}</router-link>
          <button class="btn-danger" :disabled="working" @click="remove">{{ $t('receipts.deleteReceipt') }}</button>
        </div>
      </template>
    </template>

    <div v-if="viewer" class="viewer" @click="viewer = null"><img :src="viewer" alt="" /></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '../api.js'
import { serverDate, formatDateTime, formatMoney } from '../utils.js'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const receiptId = Number(route.params.id)

const receipt = ref(null)
const loading = ref(true)
const loadError = ref('')
const stores = ref([])
const products = ref([])
const storeId = ref(null)
const purchased = ref('') // datetime-local value, the store's local time
const rows = ref([]) // one review row per receipt line that is not a discount
const images = ref([])
const viewer = ref(null)
const working = ref(false)
const actionError = ref('')
const result = ref(null)

const categories = computed(() => [...new Set(products.value.map(p => p.category).filter(Boolean))].sort())
const recordedLines = computed(() => (receipt.value?.lines || []).filter(l => l.line_type !== 'discount'))

const summary = computed(() => {
  const r = result.value
  if (!r) return []
  const out = []
  if (r.recorded) out.push(t('receipts.summaryRecorded', { count: r.recorded }, r.recorded))
  if (r.updated) out.push(t('receipts.summaryUpdated', { count: r.updated }, r.updated))
  if (r.newProducts) out.push(t('receipts.summaryNewProducts', { count: r.newProducts }, r.newProducts))
  if (r.removed) out.push(t('receipts.summaryRemoved', { count: r.removed }, r.removed))
  return out
})

function parseAmount(text) {
  const cleaned = String(text ?? '').trim().replace(/^\$/, '').replace(',', '.')
  return cleaned === '' ? NaN : Number(cleaned)
}

// Rows the user already edited survive a refresh of the draft (e.g. after choosing the store)
function buildRows(r, previous = []) {
  const edited = new Map(previous.filter(row => row.dirty).map(row => [row.id, row]))
  return r.lines
    .filter(l => l.line_type !== 'discount')
    .map(l => {
      if (edited.has(l.id)) return edited.get(l.id)
      const net = l.net_amount ?? l.line_total ?? 0
      return {
        id: l.id,
        raw: l.raw_text,
        section: l.section,
        type: l.line_type,
        suggestedName: l.suggested_name || '',
        source: l.match_source,
        ignore: l.ignored,
        mode: l.product_id ? 'existing' : 'new', // existing product, searching for one, or a new one
        productId: l.product_id,
        productName: l.product_name,
        newName: l.suggested_name || '',
        category: l.suggested_category || '',
        query: '',
        quantity: l.quantity,
        amountText: Number(net).toFixed(2),
        wasTotal: l.line_total,
        discounted: l.net_amount != null && l.line_total != null && Math.abs(l.net_amount - l.line_total) > 0.005,
        dirty: false,
      }
    })
}

function applyReceipt(r) {
  receipt.value = r
  storeId.value = r.store_id
  if (r.status === 'pending') {
    if (!purchased.value) purchased.value = r.purchased_local || ''
    rows.value = buildRows(r, rows.value)
  } else {
    rows.value = []
  }
}

async function loadProducts() {
  if (products.value.length) return
  try {
    products.value = (await api.get('/products')).data
  } catch {
    products.value = [] // the picker is empty, but new products can still be created
  }
}

async function loadImages(r) {
  if (images.value.length) return
  for (const id of r.image_ids) {
    try {
      const res = await api.get(`/receipts/${r.id}/images/${id}`, { responseType: 'blob' })
      images.value.push({ id, url: URL.createObjectURL(res.data) })
    } catch {
      // the photo just doesn't show
    }
  }
}

async function load() {
  try {
    const [rec, storeRes] = await Promise.all([api.get(`/receipts/${receiptId}`), api.get('/stores')])
    stores.value = storeRes.data
    applyReceipt(rec.data)
    loadImages(rec.data)
    if (rec.data.status === 'pending') await loadProducts()
  } catch (e) {
    loadError.value = e.response?.status === 404 ? t('receipts.notFound') : t('errors.loadFailed')
  } finally {
    loading.value = false
  }
}

function errorText(e, fallback) {
  const detail = e.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(d => d.msg).join('; ')
  return fallback
}

// --- store and time ---

async function onStoreChange() {
  await nextTick() // let v-model store the selection first
  actionError.value = ''
  try {
    const res = await api.put(`/receipts/${receiptId}`, { store_id: storeId.value })
    applyReceipt(res.data)
  } catch (e) {
    actionError.value = errorText(e, t('errors.saveFailed'))
  }
}

async function addStore() {
  const name = window.prompt(t('receipts.newStorePrompt'), receipt.value.store_text || '')
  if (!name || !name.trim()) return
  actionError.value = ''
  try {
    const created = await api.post('/stores', { name: name.trim() })
    stores.value = [...stores.value, created.data].sort((a, b) => a.name.localeCompare(b.name))
    storeId.value = created.data.id
    await onStoreChange()
  } catch (e) {
    actionError.value = errorText(e, t('errors.addFailed'))
  }
}

// --- one line: which product, how many, how much ---

function matches(row) {
  const query = row.query.trim().toLowerCase()
  if (!query) return []
  return products.value.filter(p => p.name.toLowerCase().includes(query)).slice(0, 6)
}

function touch(row) { row.dirty = true }
function skip(row) { row.ignore = true; row.dirty = true }
function include(row) { row.ignore = false; row.dirty = true }

function startPick(row) {
  row.query = row.newName || row.suggestedName || ''
  row.mode = 'pick'
}

function cancelPick(row) {
  row.mode = row.productId ? 'existing' : 'new'
}

function choose(row, product) {
  row.productId = product.id
  row.productName = product.name
  row.source = null
  row.mode = 'existing'
  row.dirty = true
}

function createNew(row, name) {
  row.newName = name.trim()
  row.productId = null
  row.mode = 'new'
  row.dirty = true
}

function rowValid(row) {
  if (row.ignore) return true
  const amount = parseAmount(row.amountText)
  if (!(Number(row.quantity) > 0) || !Number.isFinite(amount) || amount < 0) return false
  if (row.mode === 'existing') return !!row.productId
  if (row.mode === 'new') return row.newName.trim().length > 0
  return false // still choosing a product
}

const canConfirm = computed(() =>
  !!storeId.value
  && !!purchased.value
  && !isNaN(new Date(purchased.value))
  && rows.value.every(rowValid)
)

const recordingTotal = computed(() =>
  rows.value
    .filter(row => !row.ignore)
    .reduce((sum, row) => {
      const amount = parseAmount(row.amountText)
      return sum + (Number.isFinite(amount) ? amount : 0)
    }, 0)
)

// --- actions ---

function payload() {
  return {
    store_id: storeId.value,
    purchased_at: new Date(purchased.value).toISOString(), // typed in local time, stored as UTC
    lines: rows.value.map(row => {
      if (row.ignore) return { id: row.id, ignore: true }
      const line = { id: row.id, quantity: Number(row.quantity), amount: parseAmount(row.amountText) }
      if (row.mode === 'existing') return { ...line, product_id: row.productId }
      return { ...line, new_product_name: row.newName.trim(), category: row.category.trim() || null }
    }),
  }
}

async function confirmReceipt() {
  working.value = true
  actionError.value = ''
  try {
    const res = await api.post(`/receipts/${receiptId}/confirm`, payload())
    result.value = {
      recorded: res.data.recorded,
      updated: res.data.updated,
      newProducts: res.data.new_products,
      removed: res.data.removed_from_list,
    }
    applyReceipt(res.data.receipt)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    actionError.value = errorText(e, t('receipts.confirmFailed'))
  } finally {
    working.value = false
  }
}

async function retry() {
  working.value = true
  actionError.value = ''
  try {
    const res = await api.post(`/receipts/${receiptId}/extract`, null, { timeout: 300000 })
    purchased.value = ''
    rows.value = []
    applyReceipt(res.data)
    if (res.data.status === 'pending') await loadProducts()
  } catch (e) {
    actionError.value = errorText(e, t('receipts.uploadFailed'))
  } finally {
    working.value = false
  }
}

async function remove() {
  const key = receipt.value.status === 'confirmed' ? 'receipts.confirmDeleteRecorded' : 'receipts.confirmDeletePending'
  if (!confirm(t(key))) return
  working.value = true
  actionError.value = ''
  try {
    await api.delete(`/receipts/${receiptId}`)
    router.push('/receipts')
  } catch (e) {
    actionError.value = errorText(e, t('errors.deleteFailed'))
    working.value = false
  }
}

onMounted(load)
onBeforeUnmount(() => images.value.forEach(img => URL.revokeObjectURL(img.url)))
</script>

<style scoped>
.back {
  display: inline-block;
  margin-bottom: 12px;
  color: var(--primary-dark);
  text-decoration: none;
  font-size: 14px;
}

h3 { margin-bottom: 8px; }

.hint { font-size: 13px; color: var(--text-secondary); margin-top: 6px; }
.error { color: var(--danger); font-size: 13px; }
.card.error { color: var(--danger); }
.ok { color: var(--primary-dark); font-size: 13px; margin-top: 8px; }
.warn { color: #e65100; font-size: 13px; margin-top: 8px; }
.success { background: #e8f5e9; color: var(--primary-dark); font-size: 14px; }

.thumbs { display: flex; gap: 8px; }

.thumb {
  width: 72px;
  height: 96px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
  background: var(--surface);
}

.thumb img { width: 100%; height: 100%; object-fit: cover; }

.field { margin-bottom: 12px; }
.field label { display: block; font-size: 12px; color: var(--text-secondary); margin-bottom: 4px; }

.totals {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  font-size: 14px;
}

.line-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.raw {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  word-break: break-word;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--border);
  color: var(--text-secondary);
}

.badge.learned { background: #e8f5e9; color: var(--primary-dark); }
.badge.suggested { background: #e3f2fd; color: #1565c0; }

.line.skipped { opacity: 0.6; padding: 10px 16px; }
.line.skipped .static-amount { margin-inline-start: auto; }

.product-area { margin: 10px 0; }

.chosen { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }

.picker { position: relative; }

.suggestions {
  position: absolute;
  inset-inline: 0;
  z-index: 20;
  margin-top: 2px;
  list-style: none;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 240px;
  overflow-y: auto;
}

.suggestions li { padding: 8px 12px; cursor: pointer; font-size: 14px; }
.suggestions li:hover { background: #f1f8e9; }
.suggestions li small { color: var(--text-secondary); margin-inline-start: 6px; }
.suggestions li.create { color: var(--primary-dark); font-weight: 600; border-top: 1px solid var(--border); }

.new-product { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }

.numbers {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.numbers label { display: block; font-size: 12px; color: var(--text-secondary); }
.numbers label span { display: block; margin-bottom: 4px; }
.numbers input { width: 96px; }
.numbers .skip { margin-inline-start: auto; }

.btn-sm { padding: 4px 10px; font-size: 12px; }

.link {
  background: none;
  color: var(--primary-dark);
  padding: 0;
  font-size: 13px;
  text-decoration: underline;
}

.confirm-bar {
  position: sticky;
  bottom: 0;
  padding: 12px 0;
  background: var(--bg);
}

.actions { display: flex; flex-wrap: wrap; gap: 8px; }

.btn-link {
  display: inline-block;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.status {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.status.confirmed { background: #e8f5e9; color: var(--primary-dark); }

.recorded-lines { list-style: none; margin-top: 8px; }

.recorded-lines li {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid var(--border);
  font-size: 14px;
}

.recorded-lines li.skipped { color: var(--text-secondary); }
.recorded-lines li > :first-child { flex: 1; color: var(--text); }
.recorded-lines .qty { color: var(--text-secondary); }
.recorded-lines .amt { min-width: 64px; text-align: end; font-weight: 500; }

.viewer {
  position: fixed;
  inset: 0;
  z-index: 400;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  overflow: auto;
}

.viewer img { max-width: 100%; max-height: 100%; object-fit: contain; }

.loading { text-align: center; padding: 32px; color: var(--text-secondary); }
</style>
