<template>
  <div class="admin-users-view">
    <h2>{{ $t('adminUsers.title') }}</h2>

    <div class="card create-form">
      <h3>{{ $t('adminUsers.createUser') }}</h3>
      <form @submit.prevent="createUser" class="form-row">
        <input v-model="newUsername" type="text" :placeholder="$t('adminUsers.username')" required />
        <input v-model="newPassword" type="password" :placeholder="$t('adminUsers.password')" required />
        <button type="submit" class="btn-primary" :disabled="creating">{{ $t('adminUsers.create') }}</button>
      </form>
      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <div v-if="loading" class="loading">{{ $t('adminUsers.loading') }}</div>
    <div v-else class="user-list">
      <div v-for="user in users" :key="user.id" class="user-row card">
        <div class="user-info">
          <span class="user-name">{{ displayName(user.username) }}</span>
          <span v-if="user.is_admin" class="admin-badge">{{ $t('adminUsers.admin') }}</span>
          <span class="user-date">{{ $t('adminUsers.created') }} {{ formatDate(user.created_at) }}</span>
        </div>
        <div class="user-actions">
          <button class="btn-secondary btn-sm" @click="resetPassword(user)">{{ $t('adminUsers.resetPassword') }}</button>
          <button
            v-if="!user.is_admin"
            class="btn-danger btn-sm"
            @click="deleteUser(user)"
          >{{ $t('adminUsers.deleteUser') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'
import { displayName } from '../utils.js'

const { t } = useI18n()

const users = ref([])
const loading = ref(false)
const creating = ref(false)
const newUsername = ref('')
const newPassword = ref('')
const error = ref('')

async function loadUsers() {
  loading.value = true
  try {
    const res = await api.get('/users')
    users.value = res.data
  } finally {
    loading.value = false
  }
}

async function createUser() {
  creating.value = true
  error.value = ''
  try {
    await api.post('/users', { username: newUsername.value, password: newPassword.value })
    newUsername.value = ''
    newPassword.value = ''
    await loadUsers()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to create user'
  } finally {
    creating.value = false
  }
}

async function deleteUser(user) {
  if (!confirm(t('adminUsers.confirmDelete', { name: displayName(user.username) }))) return
  await api.delete(`/users/${user.id}`)
  await loadUsers()
}

async function resetPassword(user) {
  const pwd = prompt(t('adminUsers.promptPassword', { name: displayName(user.username) }))
  if (!pwd) return
  await api.put(`/users/${user.id}/password`, { password: pwd })
  alert(t('adminUsers.passwordUpdated'))
}

onMounted(loadUsers)

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  })
}
</script>

<style scoped>
h2 { margin-bottom: 16px; }

.create-form {
  margin-bottom: 20px;
}

.create-form h3 {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.form-row {
  display: flex;
  gap: 8px;
}

.form-row input { flex: 1; }

.error {
  color: var(--danger);
  font-size: 13px;
  margin-top: 8px;
}

.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-name {
  font-weight: 600;
}

.admin-badge {
  background: var(--primary);
  color: white;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.user-date {
  font-size: 12px;
  color: var(--text-secondary);
}

.user-actions {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

.loading {
  text-align: center;
  padding: 32px;
  color: var(--text-secondary);
}

@media (max-width: 640px) {
  .form-row { flex-wrap: wrap; }
  .user-row { flex-direction: column; align-items: flex-start; gap: 8px; }
}
</style>
