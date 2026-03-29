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
          {{ item.quantity }}{{ item.unit ? ' ' + item.unit : '' }}
          <span class="item-by"> &middot; {{ item.added_by }}</span>
        </span>
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
import { computed } from 'vue'

const props = defineProps({
  item: { type: Object, required: true },
})

defineEmits(['check-off', 'remove'])

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
}

.item-by {
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
