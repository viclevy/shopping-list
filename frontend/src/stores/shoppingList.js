import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const useShoppingListStore = defineStore('shoppingList', () => {
  const items = ref([])
  const loading = ref(false)

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

  async function addItem(data) {
    await api.post('/list', data)
    // WebSocket will update the list
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
  }

  return { items, loading, fetchItems, addItem, editItem, checkOff, removeItem, setItems }
})
