<template>
  <div v-if="list.boughtBefore.length" class="bought-before">
    <div class="section-header" @click="expanded = !expanded">
      <span class="section-title">{{ $t('shoppingList.boughtBefore') }} ({{ list.boughtBefore.length }})</span>
      <span class="toggle">{{ expanded ? '▾' : '▸' }}</span>
    </div>
    <div v-if="expanded" class="bought-list">
      <div
        v-for="item in list.boughtBefore"
        :key="item.product_id"
        class="bought-item card"
      >
        <img
          v-if="thumbSrc(item)"
          :src="thumbSrc(item)"
          class="bought-thumb"
        />
        <div v-else class="bought-thumb-placeholder">?</div>
        <div class="bought-info">
          <span class="bought-name">{{ item.product_name }}</span>
          <span class="bought-meta">{{ $t('shoppingList.boughtTimes', { count: item.purchase_count }) }}</span>
        </div>
        <button
          class="btn-readd"
          :title="$t('shoppingList.addToList')"
          :disabled="adding === item.product_id"
          @click="readd(item)"
        >+</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useShoppingListStore } from '../stores/shoppingList.js'

const { t } = useI18n()
const list = useShoppingListStore()
const expanded = ref(true)
const adding = ref(null)

function thumbSrc(item) {
  if (item.photo_filename) return `/uploads/${item.photo_filename}`
  if (item.image_url) return item.image_url
  return null
}

async function readd(item) {
  adding.value = item.product_id
  try {
    await list.addItem({ product_id: item.product_id })
  } finally {
    adding.value = null
  }
}
</script>

<style scoped>
.bought-before {
  margin-top: 24px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.toggle {
  font-size: 14px;
  color: var(--text-secondary);
}

.bought-list {
  display: flex;
  flex-direction: column;
}

.bought-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  gap: 10px;
}

.bought-thumb {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
}

.bought-thumb-placeholder {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 16px;
  flex-shrink: 0;
}

.bought-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.bought-name {
  font-weight: 500;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bought-meta {
  font-size: 12px;
  color: var(--text-secondary);
}

.btn-readd {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--primary);
  color: white;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  cursor: pointer;
  line-height: 1;
}

.btn-readd:hover {
  background: var(--primary-dark);
}

.btn-readd:disabled {
  opacity: 0.5;
  cursor: default;
}
</style>
