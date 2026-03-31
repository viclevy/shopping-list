import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const useShoppingListStore = defineStore('shoppingList', () => {
  const items = ref([])
  const loading = ref(false)
  const boughtBefore = ref([])
  const boughtBeforeLoading = ref(false)
  const pendingSetupProduct = ref(null)
  let bbTimer = null

  async function fetchItems() {
    loading.value = true
    try {
      const res = await api.get('/list')
      items.value = res.data
    } catch {
      // ignore
    } finally {
      loading.value = false
    }
  }

  async function fetchBoughtBefore() {
    boughtBeforeLoading.value = true
    try {
      const res = await api.get('/analytics/bought-before')
      boughtBefore.value = res.data
    } catch {
      boughtBefore.value = []
    } finally {
      boughtBeforeLoading.value = false
    }
  }

  async function addItem(data) {
    const res = await api.post('/list', data)
    // WebSocket will update the list
    return res.data
  }

  async function editItem(id, data) {
    await api.put(`/list/${id}`, data)
  }

  async function checkOff(id, data) {
    await api.post(`/list/${id}/check-off`, data)
  }

  async function removeItem(id) {
    await api.delete(`/list/${id}`)
  }

  function setItems(newItems) {
    items.value = newItems
    clearTimeout(bbTimer)
    bbTimer = setTimeout(fetchBoughtBefore, 500)
  }

  return {
    items, loading, fetchItems,
    boughtBefore, boughtBeforeLoading, fetchBoughtBefore,
    addItem, editItem, checkOff, removeItem, setItems,
    pendingSetupProduct,
  }
})
