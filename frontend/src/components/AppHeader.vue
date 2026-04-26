<template>
  <header class="app-header">
    <div class="header-left">
      <router-link to="/" class="logo">{{ $t('common.appTitle') }}</router-link>
    </div>

    <!-- Desktop nav -->
    <nav class="header-nav desktop-only">
      <router-link to="/">{{ $t('nav.list') }}</router-link>
      <router-link to="/history">{{ $t('nav.history') }}</router-link>
      <router-link to="/analytics">{{ $t('nav.analytics') }}</router-link>
      <router-link to="/stores">{{ $t('nav.stores') }}</router-link>
      <router-link to="/items">{{ $t('nav.items') }}</router-link>
      <router-link v-if="auth.isAdmin" to="/admin/users">{{ $t('nav.users') }}</router-link>
    </nav>

    <!-- Desktop right controls -->
    <div class="header-right desktop-only">
      <LanguageSwitcher />
      <VoiceButton />
      <div class="user-menu">
        <span class="username">{{ displayName(auth.user?.username) }}</span>
        <button class="btn-secondary btn-sm" @click="handleLogout">{{ $t('common.logout') }}</button>
      </div>
    </div>

    <!-- Mobile: voice + hamburger -->
    <div class="mobile-controls mobile-only">
      <VoiceButton />
      <button class="hamburger-btn" :aria-label="$t('nav.menu')" @click="menuOpen = !menuOpen">
        <span class="hamburger-bar"></span>
        <span class="hamburger-bar"></span>
        <span class="hamburger-bar"></span>
      </button>
    </div>

    <!-- Mobile dropdown menu -->
    <transition name="menu-slide">
      <div v-if="menuOpen" class="mobile-menu" @click.self="menuOpen = false">
        <div class="mobile-menu-inner">
          <nav class="mobile-nav">
            <router-link to="/" @click="menuOpen = false">{{ $t('nav.list') }}</router-link>
            <router-link to="/history" @click="menuOpen = false">{{ $t('nav.history') }}</router-link>
            <router-link to="/analytics" @click="menuOpen = false">{{ $t('nav.analytics') }}</router-link>
            <router-link to="/stores" @click="menuOpen = false">{{ $t('nav.stores') }}</router-link>
            <router-link to="/items" @click="menuOpen = false">{{ $t('nav.items') }}</router-link>
            <router-link v-if="auth.isAdmin" to="/admin/users" @click="menuOpen = false">{{ $t('nav.users') }}</router-link>
          </nav>
          <div class="mobile-menu-footer">
            <LanguageSwitcher />
            <div class="user-menu">
              <span class="username">{{ displayName(auth.user?.username) }}</span>
              <button class="btn-secondary btn-sm" @click="handleLogout">{{ $t('common.logout') }}</button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </header>

  <!-- Backdrop to close menu when clicking outside -->
  <div v-if="menuOpen" class="menu-backdrop" @click="menuOpen = false"></div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { displayName } from '../utils.js'
import VoiceButton from './VoiceButton.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)

function handleLogout() {
  menuOpen.value = false
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
  z-index: 200;
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
  margin-left: auto;
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

/* ── Mobile controls ──────────────────────────────── */

.mobile-controls {
  display: none;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.hamburger-btn {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  background: rgba(255,255,255,0.1);
  border: none;
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
}

.hamburger-bar {
  display: block;
  width: 100%;
  height: 2px;
  background: white;
  border-radius: 2px;
}

/* ── Mobile dropdown ──────────────────────────────── */

.mobile-menu {
  position: fixed;
  top: 56px;
  left: 0;
  right: 0;
  z-index: 199;
}

.mobile-menu-inner {
  background: var(--primary);
  border-top: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  padding: 8px 0 16px;
}

.mobile-nav {
  display: flex;
  flex-direction: column;
}

.mobile-nav a {
  color: rgba(255,255,255,0.9);
  text-decoration: none;
  font-size: 15px;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.mobile-nav a:hover,
.mobile-nav a.router-link-exact-active {
  background: rgba(255,255,255,0.12);
  color: white;
}

.mobile-menu-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px 0;
  gap: 12px;
}

.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 198;
}

/* ── Transition ───────────────────────────────────── */

.menu-slide-enter-active,
.menu-slide-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.menu-slide-enter-from,
.menu-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── Responsive ───────────────────────────────────── */

.desktop-only { display: flex; }
.mobile-only  { display: none; }

@media (max-width: 640px) {
  .desktop-only { display: none !important; }
  .mobile-only  { display: flex !important; }
}
</style>
