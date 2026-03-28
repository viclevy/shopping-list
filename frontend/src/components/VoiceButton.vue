<template>
  <div class="voice-btn-wrapper">
    <button
      class="voice-btn"
      :class="{ listening: isListening }"
      @click="toggleListening"
      :title="isListening ? 'Listening...' : 'Voice command'"
    >
      <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5z"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
      </svg>
    </button>
    <div v-if="transcript" class="transcript">{{ transcript }}</div>
  </div>
</template>

<script setup>
import { useVoice } from '../composables/useVoice.js'

const { isListening, transcript, toggleListening } = useVoice()
</script>

<style scoped>
.voice-btn-wrapper {
  position: relative;
}

.voice-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: all 0.2s;
}

.voice-btn:hover {
  background: rgba(255,255,255,0.3);
}

.voice-btn.listening {
  background: var(--danger);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.6); }
  70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
  100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
}

.transcript {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: var(--surface);
  color: var(--text);
  padding: 8px 12px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  font-size: 13px;
  white-space: nowrap;
  z-index: 50;
}
</style>
