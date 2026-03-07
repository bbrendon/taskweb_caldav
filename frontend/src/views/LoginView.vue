<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-title">Tasks</div>
      <div class="login-sub">Enter your password to continue</div>

      <form @submit.prevent="submit" class="login-form">
        <input
          v-model="password"
          type="password"
          class="login-input"
          placeholder="Password"
          autocomplete="current-password"
          autofocus
        />
        <div v-if="error" class="login-error">{{ error }}</div>
        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/tasks.js'

const router = useRouter()
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  if (!password.value) return
  error.value = ''
  loading.value = true
  try {
    await authApi.login(password.value)
    router.push('/tasks')
  } catch {
    error.value = 'Incorrect password'
    password.value = ''
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #111318;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 360px;
  background: #0d0f14;
  border: 1px solid #1e2130;
  border-radius: 12px;
  padding: 40px 32px;
}

.login-title {
  font-size: 24px;
  font-weight: 700;
  color: #e5e7eb;
  text-align: center;
  margin-bottom: 6px;
  letter-spacing: 0.02em;
}

.login-sub {
  font-size: 13px;
  color: #6b7280;
  text-align: center;
  margin-bottom: 28px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.login-input {
  width: 100%;
  background: #1a1d27;
  border: 1px solid #2d3148;
  border-radius: 8px;
  color: #e5e7eb;
  font-size: 16px;
  padding: 12px 14px;
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.login-input:focus {
  border-color: #5c8df6;
}

.login-error {
  font-size: 13px;
  color: #f87171;
  text-align: center;
}

.login-btn {
  width: 100%;
  background: #5c8df6;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  padding: 12px;
  cursor: pointer;
  transition: background 0.15s;
}

.login-btn:hover:not(:disabled) {
  background: #7aa3f8;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
