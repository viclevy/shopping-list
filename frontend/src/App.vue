<template>
  <div id="app-root">
    <AppHeader v-if="auth.isLoggedIn" />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import { useAuthStore } from './stores/auth.js'
import { connectWebSocket, disconnectWebSocket } from './websocket.js'
import AppHeader from './components/AppHeader.vue'

const auth = useAuthStore()

watch(() => auth.isLoggedIn, (loggedIn) => {
  if (loggedIn) connectWebSocket()
  else disconnectWebSocket()
}, { immediate: true })
</script>

<style>
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

:root {
  --primary: #4CAF50;
  --primary-dark: #388E3C;
  --danger: #f44336;
  --warning: #FF9800;
  --bg: #f5f5f5;
  --surface: #ffffff;
  --text: #212121;
  --text-secondary: #757575;
  --border: #e0e0e0;
  --radius: 8px;
  --shadow: 0 2px 4px rgba(0,0,0,0.1);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

#app-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 16px;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
}

button {
  cursor: pointer;
  border: none;
  border-radius: var(--radius);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
}

.btn-danger {
  background: var(--danger);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #d32f2f;
}

.btn-secondary {
  background: var(--border);
  color: var(--text);
}

.btn-secondary:hover:not(:disabled) {
  background: #bdbdbd;
}

input, select {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 12px;
  font-size: 14px;
  width: 100%;
  outline: none;
  transition: border-color 0.2s;
}

input:focus, select:focus {
  border-color: var(--primary);
}

.card {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
  margin-bottom: 12px;
}
</style>
