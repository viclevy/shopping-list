<template>
  <div class="login-view">
    <div class="login-card card">
      <h1>Shopping List</h1>
      <form @submit.prevent="handleLogin">
        <div class="field">
          <label for="username">Username</label>
          <input id="username" ref="usernameEl" v-model="username" type="text" autocomplete="username" required />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" ref="passwordEl" v-model="password" type="password" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="btn-primary btn-full" :disabled="loading">
          {{ loading ? 'Logging in...' : 'Log In' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const auth = useAuthStore()
const router = useRouter()

const usernameEl = ref(null)
const passwordEl = ref(null)
const username = ref(localStorage.getItem('lastLoginUsername') || '')
const password = ref('')
const error = ref('')
const loading = ref(false)

onMounted(() => {
  nextTick(() => {
    if (username.value) {
      passwordEl.value?.focus()
    } else {
      usernameEl.value?.focus()
    }
  })
})

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    localStorage.setItem('lastLoginUsername', username.value)
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-view {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.login-card {
  width: 100%;
  max-width: 380px;
  padding: 32px;
}

.login-card h1 {
  text-align: center;
  color: var(--primary);
  margin-bottom: 24px;
}

.field {
  margin-bottom: 16px;
}

.field label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.error {
  color: var(--danger);
  font-size: 13px;
  margin-bottom: 12px;
}

.btn-full {
  width: 100%;
  padding: 12px;
  font-size: 16px;
}
</style>
