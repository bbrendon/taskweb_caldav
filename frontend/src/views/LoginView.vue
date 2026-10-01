<script setup lang="ts">
import { ref } from 'vue'
import { useSession } from '@/stores/session'

const session = useSession()
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  if (!password.value || busy.value) return
  busy.value = true
  error.value = ''
  try {
    await session.login(password.value)
  } catch (e) {
    error.value = (e as Error).message
    password.value = ''
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="login">
    <form class="card" @submit.prevent="submit">
      <img src="/favicon.svg" width="44" height="44" alt="" />
      <h1>TaskWeb</h1>
      <label for="pw" class="sr-only">Password</label>
      <input id="pw" v-model="password" class="field" type="password" autocomplete="current-password"
             placeholder="Password" autofocus />
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="btn btn-primary" type="submit" :disabled="busy">{{ busy ? 'Signing in…' : 'Sign in' }}</button>
    </form>
  </main>
</template>

<style scoped>
.login {
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: 24px 16px calc(24px + var(--safe-b));
}
.card {
  width: min(320px, 100%);
  display: grid;
  gap: 12px;
}
h1 {
  margin: 0 0 8px;
  font-size: var(--step-2);
  font-weight: 700;
  letter-spacing: -0.01em;
}
.field { height: 44px; }
.btn { height: 44px; justify-content: center; }
.error { margin: 0; color: var(--rail-late); font-size: var(--step--1); }
</style>
