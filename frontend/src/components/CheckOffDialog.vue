<template>
  <div v-if="visible" class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog card">
      <h3>Check off: {{ item.product.name }}</h3>
      <div class="field">
        <label>Store</label>
        <div class="store-chips">
          <button
            v-for="store in stores"
            :key="store.id"
            class="chip"
            :class="{ active: storeId === store.id }"
            @click="storeId = storeId === store.id ? null : store.id"
          >{{ store.name }}</button>
        </div>
      </div>
      <div class="field">
        <label>Price</label>
        <input
          ref="priceInput"
          :value="priceDisplay"
          type="text"
          inputmode="numeric"
          placeholder="0.00"
          @input="onPriceInput"
          @keydown="onPriceKeydown"
        />
      </div>
      <div class="dialog-actions">
        <button class="btn-secondary" @click="$emit('close')">Cancel</button>
        <button class="btn-primary" @click="confirm">Confirm</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useSessionStore } from '../stores/session.js'
import api from '../api.js'

const props = defineProps({
  visible: Boolean,
  item: { type: Object, default: null },
})

const emit = defineEmits(['close', 'confirm'])

const session = useSessionStore()
const stores = ref([])
const storeId = ref(null)
const priceInput = ref(null)

// Implied-decimal: store raw digits as a string (e.g. "123" means $1.23)
const priceDigits = ref('')

const priceDisplay = computed(() => {
  if (!priceDigits.value) return ''
  const cents = parseInt(priceDigits.value, 10)
  return (cents / 100).toFixed(2)
})

const priceValue = computed(() => {
  if (!priceDigits.value) return null
  return parseInt(priceDigits.value, 10) / 100
})

function setPriceFromFloat(val) {
  if (val == null) {
    priceDigits.value = ''
  } else {
    priceDigits.value = String(Math.round(val * 100))
  }
}

function onPriceInput(e) {
  // Extract only digits from whatever was typed/pasted
  const digits = e.data?.replace(/\D/g, '') || ''
  if (digits) {
    priceDigits.value += digits
  }
  // Force the displayed value to our formatted version
  e.target.value = priceDisplay.value
}

function onPriceKeydown(e) {
  if (e.key === 'Backspace') {
    e.preventDefault()
    priceDigits.value = priceDigits.value.slice(0, -1)
    e.target.value = priceDisplay.value
  }
}

onMounted(async () => {
  const res = await api.get('/stores')
  stores.value = res.data
})

watch(() => props.visible, (val) => {
  if (val && props.item) {
    storeId.value = session.selectedStoreId || props.item.last_store_id || null
    fillPrice()
  }
})

watch(storeId, () => {
  fillPrice()
})

function fillPrice() {
  if (!props.item) return

  // Priority 1: ProductStore price for selected store
  if (storeId.value) {
    const ps = props.item.product.stores?.find(s => s.store_id === storeId.value)
    if (ps?.price != null) {
      setPriceFromFloat(ps.price)
      return
    }
  }

  // Priority 2: Last purchase price from history
  if (props.item.last_price != null) {
    setPriceFromFloat(props.item.last_price)
    return
  }

  // Priority 3: Best available ProductStore price (any store)
  const withPrice = (props.item.product.stores || []).filter(s => s.price != null)
  if (withPrice.length) {
    setPriceFromFloat(Math.min(...withPrice.map(s => s.price)))
    return
  }

  priceDigits.value = ''
}

function confirm() {
  if (storeId.value) {
    session.selectedStoreId = storeId.value
  }
  emit('confirm', {
    store_id: storeId.value,
    price: priceValue.value,
  })
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
  max-width: 400px;
  padding: 24px;
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

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.store-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 6px 14px;
  border-radius: 20px;
  border: 1.5px solid var(--border-color, #ccc);
  background: var(--bg-secondary, #f5f5f5);
  color: var(--text-primary, #333);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chip.active {
  background: var(--primary, #4a90d9);
  color: #fff;
  border-color: var(--primary, #4a90d9);
}
</style>
