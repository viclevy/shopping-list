import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const useProductsStore = defineStore('products', () => {
  const searchResults = ref([])
  const loading = ref(false)

  async function search(query) {
    if (!query || query.length < 2) {
      searchResults.value = []
      return
    }
    loading.value = true
    try {
      const res = await api.get('/products', { params: { q: query } })
      searchResults.value = res.data
    } catch {
      searchResults.value = []
    } finally {
      loading.value = false
    }
  }

  function clear() {
    searchResults.value = []
  }

  return { searchResults, loading, search, clear }
})
