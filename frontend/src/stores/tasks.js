import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tasksApi } from '@/api/tasks.js'

export const useTasksStore = defineStore('tasks', () => {
  // --- State ---
  const tasks = ref([])
  const allTags = ref([])
  const virtualTagCounts = ref({})
  const loading = ref(false)
  const error = ref(null)

  // --- Getters ---
  const pendingTasks = computed(() =>
    tasks.value.filter(t => ['NEEDS-ACTION', 'IN-PROCESS'].includes(t.status))
  )

  const completedTasks = computed(() =>
    tasks.value.filter(t => t.status === 'COMPLETED')
  )

  // --- Actions ---
  async function fetchTasks(params = {}) {
    loading.value = true
    error.value = null
    try {
      const res = await tasksApi.list(params)
      tasks.value = res.data.tasks || []
      return tasks.value
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTags() {
    try {
      const [tagsRes, vtRes] = await Promise.all([
        tasksApi.tags(),
        tasksApi.virtualTags(),
      ])
      allTags.value = tagsRes.data.tags || []
      virtualTagCounts.value = vtRes.data.virtual_tags || {}
    } catch (e) {
      console.error('Failed to fetch tags:', e)
    }
  }

  async function createTask(data) {
    loading.value = true
    error.value = null
    try {
      const res = await tasksApi.create(data)
      tasks.value.unshift(res.data)
      return res.data
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateTask(uid, data) {
    loading.value = true
    error.value = null
    try {
      const res = await tasksApi.update(uid, data)
      const idx = tasks.value.findIndex(t => t.uid === uid)
      if (idx !== -1) tasks.value[idx] = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function patchTask(uid, data) {
    try {
      const res = await tasksApi.patch(uid, data)
      const idx = tasks.value.findIndex(t => t.uid === uid)
      if (idx !== -1) tasks.value[idx] = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    }
  }

  async function deleteTask(uid) {
    loading.value = true
    error.value = null
    try {
      await tasksApi.delete(uid)
      tasks.value = tasks.value.filter(t => t.uid !== uid)
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function completeTask(uid) {
    try {
      const res = await tasksApi.complete(uid)
      const idx = tasks.value.findIndex(t => t.uid === uid)
      if (idx !== -1) tasks.value[idx] = res.data
      return res.data
    } catch (e) {
      error.value = e.response?.data?.error || e.message
      throw e
    }
  }

  function getTask(uid) {
    return tasks.value.find(t => t.uid === uid) || null
  }

  return {
    tasks,
    allTags,
    virtualTagCounts,
    loading,
    error,
    pendingTasks,
    completedTasks,
    fetchTasks,
    fetchTags,
    createTask,
    updateTask,
    patchTask,
    deleteTask,
    completeTask,
    getTask,
  }
})
