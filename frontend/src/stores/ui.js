import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const SAVED_VIEWS_KEY = 'taskweb2_saved_views'

export const useUiStore = defineStore('ui', () => {
  const activeTaskUid = ref(null)
  const sidebarCollapsed = ref(false)
  const showTaskForm = ref(false)
  const editingTask = ref(null) // task object being edited, null = create new

  // Saved views from localStorage
  const savedViews = ref(loadSavedViews())

  function loadSavedViews() {
    try {
      return JSON.parse(localStorage.getItem(SAVED_VIEWS_KEY) || '[]')
    } catch {
      return []
    }
  }

  function saveView(name, queryString) {
    const view = { name, query: queryString, id: Date.now() }
    savedViews.value.push(view)
    localStorage.setItem(SAVED_VIEWS_KEY, JSON.stringify(savedViews.value))
  }

  function deleteView(id) {
    savedViews.value = savedViews.value.filter(v => v.id !== id)
    localStorage.setItem(SAVED_VIEWS_KEY, JSON.stringify(savedViews.value))
  }

  function openTask(uid) {
    activeTaskUid.value = uid
    showTaskForm.value = false
    editingTask.value = null
  }

  function closeTask() {
    activeTaskUid.value = null
  }

  function openCreateForm(parentTask = null) {
    editingTask.value = parentTask ? { parent_uid: parentTask.uid } : null
    showTaskForm.value = true
    activeTaskUid.value = null
  }

  function openEditForm(task) {
    editingTask.value = { ...task }
    showTaskForm.value = true
  }

  function closeForm() {
    showTaskForm.value = false
    editingTask.value = null
  }

  return {
    activeTaskUid,
    sidebarCollapsed,
    showTaskForm,
    editingTask,
    savedViews,
    saveView,
    deleteView,
    openTask,
    closeTask,
    openCreateForm,
    openEditForm,
    closeForm,
  }
})
