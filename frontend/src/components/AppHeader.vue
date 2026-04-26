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
      <button v-if="isListRoute" class="sort-btn" :title="$t('listPreferences.sortAndGroup')" @click="sortSheetOpen = true">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
          <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
          <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
        </svg>
      </button>
      <LanguageSwitcher />
      <VoiceButton />
      <div class="user-menu">
        <span class="username">{{ displayName(auth.user?.username) }}</span>
        <button class="btn-secondary btn-sm" @click="handleLogout">{{ $t('common.logout') }}</button>
      </div>
    </div>

    <!-- Mobile: voice + sort + hamburger -->
    <div class="mobile-controls mobile-only">
      <VoiceButton />
      <button v-if="isListRoute" class="sort-btn" :title="$t('listPreferences.sortAndGroup')" @click="sortSheetOpen = true">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>
          <line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>
          <line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/>
        </svg>
      </button>
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

  <SortSheet v-model="sortSheetOpen" />
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { displayName } from '../utils.js'
import VoiceButton from './VoiceButton.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'
import SortSheet from './SortSheet.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const menuOpen = ref(false)
const sortSheetOpen = ref(false)
const isListRoute = computed(() => route.path === '/')

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

.sort-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(255,255,255,0.1);
  border: none;
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
  color: white;
  flex-shrink: 0;
}

.sort-btn:hover {
  background: rgba(255,255,255,0.2);
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
