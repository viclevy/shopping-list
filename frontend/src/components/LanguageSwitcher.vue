<template>
  <div class="language-switcher">
    <select v-model="currentLang" @change="handleLanguageChange" class="lang-select">
      <option value="en">English</option>
      <option value="es">Español</option>
      <option value="de">Deutsch</option>
      <option value="ja">日本語</option>
      <option value="he">עברית</option>
    </select>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLanguage } from '../i18n.js'

const { locale } = useI18n()

const currentLang = computed({
  get() {
    return locale.value
  },
  set(value) {
    locale.value = value
  }
})

function handleLanguageChange() {
  setLanguage(currentLang.value)
  // Apply RTL for Hebrew
  if (currentLang.value === 'he') {
    document.documentElement.dir = 'rtl'
    document.documentElement.lang = 'he'
  } else {
    document.documentElement.dir = 'ltr'
    document.documentElement.lang = currentLang.value
  }
}

// Initialize direction on mount
document.documentElement.dir = locale.value === 'he' ? 'rtl' : 'ltr'
document.documentElement.lang = locale.value
</script>

<style scoped>
.language-switcher {
  display: flex;
  align-items: center;
}

.lang-select {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.3);
  background: rgba(255,255,255,0.1);
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.lang-select:hover {
  background: rgba(255,255,255,0.2);
}

.lang-select:focus {
  outline: none;
  border-color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.15);
}

.lang-select option {
  background: white;
  color: #212121;
}
</style>
