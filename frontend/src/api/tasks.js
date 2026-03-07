import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
  timeout: 20000,
})

// Redirect to /login on any 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401 && window.location.pathname !== '/login') {
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login(password) { return api.post('/auth/login/', { password }) },
  logout()        { return api.post('/auth/logout/') },
  check()         { return api.get('/auth/check/') },
}

export const tasksApi = {
  list(params = {}) {
    return api.get('/tasks/', { params })
  },
  get(uid) {
    return api.get(`/tasks/${uid}/`)
  },
  create(data) {
    return api.post('/tasks/', data)
  },
  update(uid, data) {
    return api.put(`/tasks/${uid}/`, data)
  },
  patch(uid, data) {
    return api.patch(`/tasks/${uid}/`, data)
  },
  delete(uid) {
    return api.delete(`/tasks/${uid}/`)
  },
  complete(uid) {
    return api.post(`/tasks/${uid}/complete/`)
  },
  tags() {
    return api.get('/tags/')
  },
  virtualTags() {
    return api.get('/virtual-tags/')
  },
}

export default api
