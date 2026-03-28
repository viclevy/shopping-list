<template>
  <div v-if="visible" class="dialog-overlay" @click.self="$emit('close')">
    <div class="dialog card">
      <h3>Check off: {{ item.product.name }}</h3>
      <div class="field">
        <label>Store</label>
        <select v-model="storeId">
          <option :value="null">-- No store --</option>
          <option v-for="store in stores" :key="store.id" :value="store.id">{{ store.name }}</option>
        </select>
      </div>
      <div class="field">
        <label>Price</label>
        <input v-model.number="price" type="number" min="0" step="0.01" placeholder="Price" />
      </div>
      <div class="dialog-actions">
        <button class="btn-secondary" @click="$emit('close')">Cancel</button>
        <button class="btn-primary" @click="confirm">Confirm</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
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
const price = ref(null)

onMounted(async () => {
  const res = await api.get('/stores')
  stores.value = res.data
})

watch(() => props.visible, (val) => {
  if (val && props.item) {
    storeId.value = session.selectedStoreId
    // Pre-fill price from product's store data
    const ps = props.item.product.stores?.find(s => s.store_id === storeId.value)
    price.value = ps?.price ?? null
  }
})

watch(storeId, (id) => {
  if (id && props.item) {
    const ps = props.item.product.stores?.find(s => s.store_id === id)
    if (ps?.price != null && price.value == null) {
      price.value = ps.price
    }
  }
})

function confirm() {
  if (storeId.value) {
    session.selectedStoreId = storeId.value
  }
  emit('confirm', {
    store_id: storeId.value,
    price: price.value,
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
</style>
