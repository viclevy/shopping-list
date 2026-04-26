<template>
  <div class="sort-controls">
    <!-- Grouping toggle -->
    <div class="control-group">
      <span class="control-label">{{ $t('listPreferences.grouping') }}</span>
      <div class="btn-group">
        <button
          :class="['btn-toggle', prefs.listGrouping === 'category' ? 'active' : '']"
          @click="setGrouping('category')"
        >{{ $t('listPreferences.byCategory') }}</button>
        <button
          :class="['btn-toggle', prefs.listGrouping === 'flat' ? 'active' : '']"
          @click="setGrouping('flat')"
        >{{ $t('listPreferences.flat') }}</button>
      </div>
    </div>

    <!-- Item sort (always shown) -->
    <div class="control-group">
      <span class="control-label">{{ $t('listPreferences.itemOrder') }}</span>
      <div class="btn-group">
        <button
          :class="['btn-toggle', prefs.listItemSort === 'alpha-asc' ? 'active' : '']"
          :title="$t('listPreferences.alphaAsc')"
          @click="setItemSort('alpha-asc')"
        >A→Z</button>
        <button
          :class="['btn-toggle', prefs.listItemSort === 'alpha-desc' ? 'active' : '']"
          :title="$t('listPreferences.alphaDesc')"
          @click="setItemSort('alpha-desc')"
        >Z→A</button>
        <button
          :class="['btn-toggle', prefs.listItemSort === 'manual' ? 'active' : '']"
          :title="$t('listPreferences.manual')"
          @click="setItemSort('manual')"
        >&#8597;</button>
      </div>
    </div>

    <!-- Category sort (only when grouped) -->
    <div v-if="prefs.listGrouping === 'category'" class="control-group">
      <span class="control-label">{{ $t('listPreferences.categoryOrder') }}</span>
      <div class="btn-group">
        <button
          :class="['btn-toggle', prefs.categorySort === 'alpha-asc' ? 'active' : '']"
          :title="$t('listPreferences.alphaAsc')"
          @click="setCategorySort('alpha-asc')"
        >A→Z</button>
        <button
          :class="['btn-toggle', prefs.categorySort === 'alpha-desc' ? 'active' : '']"
          :title="$t('listPreferences.alphaDesc')"
          @click="setCategorySort('alpha-desc')"
        >Z→A</button>
        <button
          :class="['btn-toggle', prefs.categorySort === 'frequency' ? 'active' : '']"
          :title="$t('listPreferences.frequency')"
          @click="setCategorySort('frequency')"
        >★</button>
        <button
          :class="['btn-toggle', prefs.categorySort === 'manual' ? 'active' : '']"
          :title="$t('listPreferences.manual')"
          @click="setCategorySort('manual')"
        >&#8597;</button>
      </div>
    </div>

    <!-- Buy-again sort -->
    <div class="control-group">
      <span class="control-label">{{ $t('listPreferences.buyAgainOrder') }}</span>
      <div class="btn-group">
        <button
          :class="['btn-toggle', prefs.buyagainSort === 'frequency' ? 'active' : '']"
          :title="$t('listPreferences.frequency')"
          @click="setBuyagainSort('frequency')"
        >★</button>
        <button
          :class="['btn-toggle', prefs.buyagainSort === 'alpha-asc' ? 'active' : '']"
          :title="$t('listPreferences.alphaAsc')"
          @click="setBuyagainSort('alpha-asc')"
        >A→Z</button>
        <button
          :class="['btn-toggle', prefs.buyagainSort === 'alpha-desc' ? 'active' : '']"
          :title="$t('listPreferences.alphaDesc')"
          @click="setBuyagainSort('alpha-desc')"
        >Z→A</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { usePreferencesStore } from '../stores/preferences.js'

const prefs = usePreferencesStore()

function setGrouping(value) {
  prefs.listGrouping = value
  prefs.savePreferences({ list_grouping: value })
}

function setItemSort(value) {
  prefs.listItemSort = value
  prefs.savePreferences({ list_item_sort: value })
}

function setCategorySort(value) {
  prefs.categorySort = value
  prefs.savePreferences({ category_sort: value })
}

function setBuyagainSort(value) {
  prefs.buyagainSort = value
  prefs.savePreferences({ buyagain_sort: value })
}
</script>

<style scoped>
.sort-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  padding: 8px 12px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-label {
  color: var(--text-secondary);
  white-space: nowrap;
  font-size: 12px;
}

.btn-group {
  display: flex;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border);
}

.btn-toggle {
  background: var(--background);
  border: none;
  padding: 3px 8px;
  cursor: pointer;
  font-size: 12px;
  color: var(--text-secondary);
  transition: background 0.15s, color 0.15s;
}

.btn-toggle:not(:last-child) {
  border-right: 1px solid var(--border);
}

.btn-toggle:hover {
  background: var(--border);
}

.btn-toggle.active {
  background: var(--primary);
  color: white;
}
</style>
