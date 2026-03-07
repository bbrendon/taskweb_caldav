import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import LoginView from '@/views/LoginView.vue'
import { authApi } from '@/api/tasks.js'

const routes = [
  {
    path: '/login',
    component: LoginView,
    meta: { public: true },
  },
  {
    path: '/',
    redirect: '/tasks',
  },
  {
    path: '/tasks',
    component: AppShell,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Guard: check session before entering any protected route
router.beforeEach(async (to) => {
  if (to.meta.public) return true

  try {
    const res = await authApi.check()
    if (res.data.authenticated) return true
  } catch {
    // network error — let it through, the 401 interceptor will catch API calls
  }

  return '/login'
})

export default router
