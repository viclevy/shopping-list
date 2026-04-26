<template>
  <teleport to="body">
    <transition name="sheet">
      <div v-if="modelValue" class="sheet-overlay" @click.self="close">
        <div class="sheet-panel">
          <div class="sheet-handle-bar"></div>
          <div class="sheet-header">
            <span class="sheet-title">{{ $t('listPreferences.sortAndGroup') }}</span>
            <button class="sheet-close-btn" @click="close">✕</button>
          </div>
          <div class="sheet-body">
            <ListSortControls />
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import ListSortControls from './ListSortControls.vue'

defineProps({ modelValue: Boolean })
const emit = defineEmits(['update:modelValue'])
function close() { emit('update:modelValue', false) }
</script>

<style scoped>
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 500;
  display: flex;
  align-items: flex-end;
}

.sheet-panel {
  width: 100%;
  background: var(--surface);
  border-radius: 16px 16px 0 0;
  padding-bottom: max(env(safe-area-inset-bottom), 12px);
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.2);
}

.sheet-handle-bar {
  width: 40px;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  margin: 10px auto 4px;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 16px 4px;
}

.sheet-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--text-primary);
}

.sheet-close-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 4px;
  line-height: 1;
}

.sheet-close-btn:hover {
  background: var(--border);
}

.sheet-body :deep(.sort-controls) {
  border-bottom: none;
  padding: 8px 12px 8px;
}

/* Transition: overlay fades, panel slides up */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.2s ease;
}
.sheet-enter-from,
.sheet-leave-to {
  opacity: 0;
}
.sheet-enter-active .sheet-panel,
.sheet-leave-active .sheet-panel {
  transition: transform 0.25s ease;
}
.sheet-enter-from .sheet-panel,
.sheet-leave-to .sheet-panel {
  transform: translateY(100%);
}
</style>
