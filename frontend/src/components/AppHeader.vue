<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">Shopping List</router-link>
    </div>
    <nav class="header-nav">
      <router-link to="/">List</router-link>
      <router-link to="/history">History</router-link>
      <router-link to="/analytics">Analytics</router-link>
      <router-link to="/stores">Stores</router-link>
      <router-link v-if="auth.isAdmin" to="/admin/users">Users</router-link>
    </nav>
    <div class="header-right">
      <VoiceButton />
      <div class="user-menu">
        <span class="username">{{ displayName(auth.user?.username) }}</span>
        <button class="btn-secondary btn-sm" @click="handleLogout">Logout</button>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { displayName } from '../utils.js'
import VoiceButton from './VoiceButton.vue'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.app-header {
  background: var(--primary);
  color: white;
  padding: 0 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left .logo {
  color: white;
  text-decoration: none;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

.header-nav {
  display: flex;
  gap: 12px;
  flex: 1;
  overflow-x: auto;
}

.header-nav a {
  color: rgba(255,255,255,0.85);
  text-decoration: none;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.header-nav a:hover,
.header-nav a.router-link-exact-active {
  color: white;
  background: rgba(255,255,255,0.15);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 8px;
}

.username {
  font-size: 13px;
  opacity: 0.9;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

@media (max-width: 640px) {
  .app-header {
    flex-wrap: wrap;
    height: auto;
    padding: 8px 12px;
    gap: 8px;
  }
  .header-nav {
    order: 3;
    width: 100%;
    padding-bottom: 4px;
  }
  .username { display: none; }
}
</style>
