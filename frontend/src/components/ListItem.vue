<template>
  <div class="list-item card">
    <div class="item-left" @click="$router.push(`/product/${item.product.id}`)">
      <img
        v-if="thumbSrc"
        :src="thumbSrc"
        class="item-thumb"
      />
      <div v-else class="item-thumb-placeholder">?</div>
      <div class="item-info">
        <span class="item-name">{{ item.product.name }}</span>
        <span class="item-meta">
          <span class="qty-stepper" @click.stop>
            <button class="qty-btn" @click="decrement" :disabled="item.quantity <= 1 || updating">-</button>
            <span class="qty-value">{{ displayQty }}</span>
            <button class="qty-btn" @click="increment" :disabled="updating">+</button>
          </span>
          <span v-if="item.unit" class="qty-unit">{{ item.unit }}</span>
        </span>
        <span class="item-by">{{ item.added_by }}</span>
        <span v-if="bestPrice !== null" class="item-price">${{ bestPrice.toFixed(2) }}</span>
      </div>
    </div>
    <div class="item-actions">
      <button class="btn-check" title="Check off" @click="$emit('check-off', item)">&#10003;</button>
      <button class="btn-remove" title="Remove" @click="$emit('remove', item)">&#10005;</button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useShoppingListStore } from '../stores/shoppingList.js'

const props = defineProps({
  item: { type: Object, required: true },
})

defineEmits(['check-off', 'remove'])

const list = useShoppingListStore()
const updating = ref(false)

const thumbSrc = computed(() => {
  const photos = props.item.product.photos || []
  const primary = photos.find(p => p.is_primary) || photos[0]
  if (primary) return `/uploads/${primary.filename}`
  if (props.item.product.image_url) return props.item.product.image_url
  return null
})

const bestPrice = computed(() => {
  const stores = props.item.product.stores || []
  const withPrice = stores.filter(s => s.price != null)
  if (!withPrice.length) return null
  return Math.min(...withPrice.map(s => s.price))
})

const displayQty = computed(() => {
  const q = props.item.quantity
  return Number.isInteger(q) ? q : q.toFixed(1)
})

async function increment() {
  updating.value = true
  try {
    await list.editItem(props.item.id, { quantity: props.item.quantity + 1 })
  } finally {
    updating.value = false
  }
}

async function decrement() {
  if (props.item.quantity <= 1) return
  updating.value = true
  try {
    await list.editItem(props.item.id, { quantity: props.item.quantity - 1 })
  } finally {
    updating.value = false
  }
}
</script>

<style scoped>
.list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  transition: transform 0.1s;
}

.item-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  cursor: pointer;
  min-width: 0;
}

.item-thumb {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.item-thumb-placeholder {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  background: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 20px;
  flex-shrink: 0;
}

.item-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.item-name {
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.qty-stepper {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.qty-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--border);
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  cursor: pointer;
  line-height: 1;
}

.qty-btn:disabled {
  opacity: 0.3;
  cursor: default;
}

.qty-btn:not(:disabled):hover {
  background: var(--text-secondary);
  color: white;
}

.qty-value {
  min-width: 20px;
  text-align: center;
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
}

.qty-unit {
  margin-left: 2px;
}

.item-by {
  font-size: 12px;
  color: var(--text-secondary);
  opacity: 0.7;
}

.item-price {
  font-size: 13px;
  color: var(--primary);
  font-weight: 500;
}

.item-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.btn-check {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-check:hover {
  background: var(--primary-dark);
}

.btn-remove {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ffebee;
  color: var(--danger);
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-remove:hover {
  background: #ffcdd2;
}
</style>
