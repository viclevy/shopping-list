<template>
  <div class="history-view">
    <h2>History</h2>
    <div class="filters">
      <select v-model="filterAction">
        <option value="">All actions</option>
        <option value="added">Added</option>
        <option value="modified">Modified</option>
        <option value="checked_off">Checked off</option>
        <option value="removed">Removed</option>
      </select>
      <button class="btn-primary" @click="loadHistory">Refresh</button>
    </div>
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="!events.length" class="empty">No history events found.</div>
    <div v-else class="event-list">
      <div v-for="event in events" :key="event.id" class="event-row card">
        <div class="event-main">
          <span class="event-action" :class="event.action">{{ formatAction(event.action) }}</span>
          <router-link :to="`/product/${event.product_id}`" class="event-product">
            {{ event.product_name }}
          </router-link>
          <span v-if="event.quantity" class="event-qty">
            &times;{{ event.quantity }}{{ event.unit ? ' ' + event.unit : '' }}
          </span>
        </div>
        <div class="event-meta">
          <span>{{ displayName(event.username) }}</span>
          <span>{{ formatDate(event.timestamp) }}</span>
          <span v-if="event.store_name" class="event-store">@ {{ event.store_name }}</span>
          <span v-if="event.price" class="event-price">${{ event.price.toFixed(2) }}</span>
        </div>
        <div v-if="event.details" class="event-details">{{ event.details }}</div>
        <button class="btn-delete" @click="deleteEvent(event.id)">&times;</button>
      </div>
    </div>
    <button v-if="events.length >= limit" class="btn-secondary load-more" @click="loadMore">
      Load more
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import api from '../api.js'
import { displayName } from '../utils.js'

const events = ref([])
const loading = ref(false)
const filterAction = ref('')
const limit = ref(50)
const offset = ref(0)

async function loadHistory() {
  loading.value = true
  const params = { limit: limit.value, offset: 0 }
  if (filterAction.value) params.action = filterAction.value
  try {
    const res = await api.get('/history', { params })
    events.value = Array.isArray(res.data) ? res.data : []
    offset.value = events.value.length
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  const params = { limit: limit.value, offset: offset.value }
  if (filterAction.value) params.action = filterAction.value
  const res = await api.get('/history', { params })
  const newEvents = Array.isArray(res.data) ? res.data : []
  events.value.push(...newEvents)
  offset.value += newEvents.length
}

async function deleteEvent(id) {
  if (!confirm('Delete this history event?')) return
  await api.delete(`/history/${id}`)
  events.value = events.value.filter(e => e.id !== id)
}

watch(filterAction, () => loadHistory())
onMounted(loadHistory)

function formatAction(action) {
  return (action || '').replace('_', ' ')
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.filters select { width: auto; max-width: 200px; }

.event-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  position: relative;
}

.event-main {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.event-action {
  font-weight: 600;
  font-size: 13px;
  text-transform: capitalize;
  min-width: 80px;
}

.event-action.checked_off { color: var(--primary); }
.event-action.added { color: #2196F3; }
.event-action.removed { color: var(--danger); }
.event-action.modified { color: var(--warning); }

.event-product {
  color: var(--text);
  text-decoration: none;
  font-weight: 500;
}

.event-product:hover { text-decoration: underline; }

.event-qty { color: var(--text-secondary); font-size: 13px; }

.event-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  width: 100%;
}

.event-store { color: var(--primary); }
.event-price { font-weight: 500; color: var(--text); }

.event-details {
  width: 100%;
  font-size: 12px;
  color: var(--text-secondary);
  font-style: italic;
}

.btn-delete {
  position: absolute;
  right: 8px;
  top: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-delete:hover { background: #ffebee; color: var(--danger); }

.loading, .empty {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

.load-more {
  display: block;
  margin: 16px auto;
}
</style>
