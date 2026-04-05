<template>
  <div class="analytics-view">
    <h2>{{ $t('analytics.title') }}</h2>

    <div class="period-selector">
      <button :class="{ active: period === 'week' }" @click="period = 'week'">{{ $t('analytics.week') }}</button>
      <button :class="{ active: period === 'month' }" @click="period = 'month'">{{ $t('analytics.month') }}</button>
      <button :class="{ active: period === 'year' }" @click="period = 'year'">{{ $t('analytics.year') }}</button>
    </div>

    <div class="charts-grid">
      <div class="card chart-card">
        <h3>{{ $t('analytics.spendingOverTime') }}</h3>
        <Bar v-if="spendingData" :data="spendingData" :options="chartOptions" />
        <p v-else class="no-data">{{ $t('analytics.noSpendingData') }}</p>
      </div>

      <div class="card chart-card">
        <h3>{{ $t('analytics.byStore') }}</h3>
        <Pie v-if="storeData" :data="storeData" :options="pieOptions" />
        <p v-else class="no-data">{{ $t('analytics.noStoreData') }}</p>
      </div>

      <div class="card chart-card">
        <h3>{{ $t('analytics.byCategory') }}</h3>
        <Pie v-if="categoryData" :data="categoryData" :options="pieOptions" />
        <p v-else class="no-data">{{ $t('analytics.noCategoryData') }}</p>
      </div>

      <div class="card chart-card">
        <h3>{{ $t('analytics.familyContributions') }}</h3>
        <Bar v-if="contributionData" :data="contributionData" :options="chartOptions" />
        <p v-else class="no-data">{{ $t('analytics.noContributionData') }}</p>
      </div>

      <div class="card chart-card full-width">
        <h3>{{ $t('analytics.topItems') }}</h3>
        <div v-if="frequentItems.length" class="freq-table">
          <div v-for="item in frequentItems" :key="item.product_id" class="freq-row">
            <router-link :to="`/product/${item.product_id}`" class="freq-name">
              {{ item.product_name }}
            </router-link>
            <span class="freq-count">{{ item.count }} {{ $t('analytics.times') }}</span>
            <span v-if="item.last_purchased" class="freq-date">
              {{ $t('analytics.lastPurchased') }}: {{ formatDate(item.last_purchased) }}
            </span>
          </div>
        </div>
        <p v-else class="no-data">{{ $t('analytics.noPurchaseData') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Bar, Pie } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  Title, Tooltip, Legend,
} from 'chart.js'
import api from '../api.js'
import { displayName } from '../utils.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend)

const { t } = useI18n()

const period = ref('month')
const spending = ref([])
const byStore = ref([])
const byCategory = ref([])
const contributions = ref([])
const frequentItems = ref([])

const COLORS = ['#4CAF50','#2196F3','#FF9800','#f44336','#9C27B0','#00BCD4','#795548','#607D8B']

const chartOptions = { responsive: true, maintainAspectRatio: true, plugins: { legend: { display: false } } }
const pieOptions = { responsive: true, maintainAspectRatio: true }

const spendingData = computed(() => {
  if (!spending.value.length) return null
  return {
    labels: spending.value.map(s => s.period),
    datasets: [{ data: spending.value.map(s => s.total), backgroundColor: COLORS[0] }],
  }
})

const storeData = computed(() => {
  if (!byStore.value.length) return null
  return {
    labels: byStore.value.map(s => s.store_name),
    datasets: [{ data: byStore.value.map(s => s.total), backgroundColor: COLORS }],
  }
})

const categoryData = computed(() => {
  if (!byCategory.value.length) return null
  return {
    labels: byCategory.value.map(s => s.category),
    datasets: [{ data: byCategory.value.map(s => s.total), backgroundColor: COLORS }],
  }
})

const contributionData = computed(() => {
  if (!contributions.value.length) return null
  return {
    labels: contributions.value.map(c => displayName(c.username)),
    datasets: [
      { label: 'Added', data: contributions.value.map(c => c.items_added), backgroundColor: '#2196F3' },
      { label: 'Bought', data: contributions.value.map(c => c.items_bought), backgroundColor: '#4CAF50' },
    ],
  }
})

async function loadData() {
  const [s, st, cat, freq, cont] = await Promise.all([
    api.get('/analytics/spending', { params: { period: period.value } }),
    api.get('/analytics/by-store'),
    api.get('/analytics/by-category'),
    api.get('/analytics/frequent-items'),
    api.get('/analytics/contributions'),
  ])
  spending.value = s.data
  byStore.value = st.data
  byCategory.value = cat.data
  frequentItems.value = freq.data
  contributions.value = cont.data
}

watch(period, loadData)
onMounted(loadData)

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.period-selector {
  display: flex;
  gap: 4px;
  margin-bottom: 20px;
}

.period-selector button {
  padding: 6px 16px;
  background: var(--border);
  color: var(--text);
  font-size: 13px;
}

.period-selector button.active {
  background: var(--primary);
  color: white;
}

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.chart-card {
  min-height: 250px;
}

.chart-card h3 {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.full-width {
  grid-column: 1 / -1;
}

.freq-table {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.freq-row {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 14px;
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
}

.freq-name {
  flex: 1;
  color: var(--text);
  text-decoration: none;
  font-weight: 500;
}

.freq-name:hover { text-decoration: underline; }

.freq-count {
  color: var(--primary);
  font-weight: 500;
}

.freq-date {
  color: var(--text-secondary);
  font-size: 12px;
}

.no-data {
  text-align: center;
  color: var(--text-secondary);
  padding: 32px;
  font-size: 13px;
}

@media (max-width: 640px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
