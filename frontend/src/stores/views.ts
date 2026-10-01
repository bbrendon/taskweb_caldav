import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/lib/api'
import { DEFAULT_COLUMNS } from '@/lib/columns'
import { placeView, SMART_LISTS, tagView, type Sort, type View } from '@/lib/filters'

/** Settings document shared across devices (server JSON). */
interface SettingsDoc {
  saved?: View[]
  columns?: Record<string, string[]>
  sorts?: Record<string, Sort[]>
  sidebarLists?: string[]
}

export const useViews = defineStore('views', () => {
  const doc = ref<SettingsDoc>({})
  let saveTimer: number | undefined

  const saved = computed(() => doc.value.saved ?? [])

  function find(id: string): View {
    if (id.startsWith('tag:')) return tagView(id.slice(4))
    if (id.startsWith('place:')) return placeView(id.slice(6))
    return SMART_LISTS.find((v) => v.id === id) ?? saved.value.find((v) => v.id === id) ?? SMART_LISTS[0]
  }

  function columnsFor(view: View): string[] {
    return doc.value.columns?.[view.id] ?? view.columns ?? doc.value.columns?.default ?? DEFAULT_COLUMNS
  }

  function sortFor(view: View): Sort[] {
    return doc.value.sorts?.[view.id] ?? view.sort
  }

  function setSort(viewId: string, sort: Sort[]) {
    doc.value = { ...doc.value, sorts: { ...doc.value.sorts, [viewId]: sort } }
    persist()
  }

  function setColumns(viewId: string, cols: string[]) {
    doc.value = { ...doc.value, columns: { ...doc.value.columns, [viewId]: cols } }
    persist()
  }

  function saveView(view: View) {
    const list = saved.value.filter((v) => v.id !== view.id)
    doc.value = { ...doc.value, saved: [...list, { ...view, builtin: false }] }
    persist()
  }

  function deleteView(id: string) {
    doc.value = { ...doc.value, saved: saved.value.filter((v) => v.id !== id) }
    persist()
  }

  async function load() {
    doc.value = (await api.settings()) as SettingsDoc
  }

  function persist() {
    window.clearTimeout(saveTimer)
    saveTimer = window.setTimeout(() => api.saveSettings(doc.value as Record<string, unknown>), 400)
  }

  return { doc, saved, find, columnsFor, setColumns, sortFor, setSort, saveView, deleteView, load }
})
