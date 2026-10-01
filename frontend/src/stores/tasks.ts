import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, ApiError } from '@/lib/api'
import type { AppConfig, Task, TaskPatch } from '@/lib/types'

const POLL_MS = 30_000

export const useTasks = defineStore('tasks', () => {
  const byUid = ref(new Map<string, Task>())
  const version = ref<number | null>(null)
  const config = ref<AppConfig | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const offline = ref(!navigator.onLine)
  let timer: number | undefined

  const all = computed(() => [...byUid.value.values()])
  const tz = computed(() => config.value?.timezone ?? 'UTC')
  const allTags = computed(() => {
    const seen = new Map<string, string>()
    for (const t of [...(config.value?.tags ?? []), ...all.value.flatMap((x) => x.tags)]) {
      if (!seen.has(t.toLowerCase())) seen.set(t.toLowerCase(), t)
    }
    return [...seen.values()].sort((a, b) => a.localeCompare(b))
  })

  function put(task: Task) {
    byUid.value.set(task.uid, task)
  }

  async function load(force = false) {
    if (loading.value) return
    loading.value = true
    try {
      if (!config.value) config.value = await api.config()
      const res = await api.tasks(force || version.value === null ? undefined : version.value)
      if (!res.unchanged && res.tasks) byUid.value = new Map(res.tasks.map((t) => [t.uid, t]))
      version.value = res.version
      error.value = null
      offline.value = false
    } catch (e) {
      if (e instanceof ApiError && e.status === 0) offline.value = true
      else error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  function startPolling() {
    stopPolling()
    timer = window.setInterval(() => { if (document.visibilityState === 'visible') load() }, POLL_MS)
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
  }
  function stopPolling() {
    window.clearInterval(timer)
    document.removeEventListener('visibilitychange', onVisible)
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
  }
  const onVisible = () => { if (document.visibilityState === 'visible') load() }
  const onOnline = () => { offline.value = false; load() }
  const onOffline = () => { offline.value = true }

  /** Run a server call; on failure restore the previous task and surface the error. */
  async function mutate(uid: string | null, optimistic: ((t: Task) => Task) | null, call: () => Promise<Task>) {
    const before = uid ? byUid.value.get(uid) : undefined
    if (before && optimistic) put(optimistic({ ...before }))
    try {
      const fresh = await call()
      put(fresh)
      error.value = null
      return fresh
    } catch (e) {
      if (before) put(before)
      error.value = (e as Error).message
      if (e instanceof ApiError && e.status === 409) load(true)
      throw e
    }
  }

  const create = (patch: TaskPatch) => mutate(null, null, () => api.create(patch)).then((t) => { load(true); return t })
  const update = (uid: string, patch: TaskPatch) =>
    mutate(uid, (t) => ({ ...t, ...patch } as Task), () => api.update(uid, patch))
  const complete = (uid: string) =>
    mutate(uid, (t) => (t.recur_after || t.rrule ? t : { ...t, status: 'COMPLETED' }), () => api.complete(uid))
      .then((t) => { load(true); return t })
  const reopen = (uid: string) => mutate(uid, (t) => ({ ...t, status: 'NEEDS-ACTION' }), () => api.reopen(uid))
  const skip = (uid: string) => mutate(uid, null, () => api.skip(uid))

  async function remove(uid: string, children: 'orphan' | 'delete' = 'orphan') {
    try {
      const res = await api.remove(uid, children)
      for (const id of res.deleted) byUid.value.delete(id)
      load(true)
    } catch (e) {
      error.value = (e as Error).message
      throw e
    }
  }

  return {
    byUid, all, version, config, tz, allTags, loading, error, offline,
    load, startPolling, stopPolling, create, update, complete, reopen, skip, remove,
  }
})
