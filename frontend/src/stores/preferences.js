import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const usePreferencesStore = defineStore('preferences', () => {
  const listGrouping = ref('category')   // 'category' | 'flat'
  const listItemSort = ref('alpha-asc')  // 'alpha-asc' | 'alpha-desc' | 'manual'
  const categorySort = ref('alpha-asc')  // 'alpha-asc' | 'alpha-desc' | 'manual' | 'frequency'
  const categoryOrder = ref(null)        // null | string[] — manual category order
  const buyagainSort = ref('frequency')  // 'frequency' | 'alpha-asc' | 'alpha-desc'
  const loaded = ref(false)

  async function fetchPreferences() {
    try {
      const res = await api.get('/auth/preferences')
      listGrouping.value = res.data.list_grouping ?? 'category'
      listItemSort.value = res.data.list_item_sort ?? 'alpha-asc'
      categorySort.value = res.data.category_sort ?? 'alpha-asc'
      categoryOrder.value = res.data.category_order ?? null
      buyagainSort.value = res.data.buyagain_sort ?? 'frequency'
    } catch {
      // keep defaults on error
    } finally {
      loaded.value = true
    }
  }

  async function savePreferences(updates) {
    try {
      const res = await api.put('/auth/preferences', updates)
      listGrouping.value = res.data.list_grouping
      listItemSort.value = res.data.list_item_sort
      categorySort.value = res.data.category_sort
      categoryOrder.value = res.data.category_order ?? null
      buyagainSort.value = res.data.buyagain_sort
    } catch {
      // ignore — UI reflects optimistic update already
    }
  }

  return {
    listGrouping,
    listItemSort,
    categorySort,
    categoryOrder,
    buyagainSort,
    loaded,
    fetchPreferences,
    savePreferences,
  }
})
