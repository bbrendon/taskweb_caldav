import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, setUnauthorizedHandler } from '@/lib/api'

export const useSession = defineStore('session', () => {
  const authenticated = ref<boolean | null>(null)

  setUnauthorizedHandler(() => { authenticated.value = false })

  async function check() {
    try {
      authenticated.value = (await api.session()).authenticated
    } catch {
      authenticated.value = false
    }
  }

  async function login(password: string) {
    await api.login(password)
    authenticated.value = true
  }

  async function logout() {
    await api.logout()
    authenticated.value = false
  }

  return { authenticated, check, login, logout }
})
