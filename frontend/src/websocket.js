import { useShoppingListStore } from './stores/shoppingList.js'
import { useAuthStore } from './stores/auth.js'

let ws = null
let reconnectTimer = null
let reconnectDelay = 3000

export function connectWebSocket() {
  const auth = useAuthStore()
  const list = useShoppingListStore()

  if (!auth.token) return
  if (ws && ws.readyState === WebSocket.OPEN) return

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${location.host}/ws?token=${auth.token}`)

  ws.onopen = () => {
    reconnectDelay = 3000
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    if (msg.type === 'list_updated') {
      list.setItems(msg.data.items)
    }
  }

  ws.onclose = () => {
    ws = null
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 1.5, 30000)
      connectWebSocket()
    }, reconnectDelay)
  }

  ws.onerror = () => {
    ws?.close()
  }
}

export function disconnectWebSocket() {
  clearTimeout(reconnectTimer)
  if (ws) {
    ws.close()
    ws = null
  }
}
