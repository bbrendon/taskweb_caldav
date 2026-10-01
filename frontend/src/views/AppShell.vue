<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '@/components/Icon.vue'
import SideNav from '@/components/SideNav.vue'
import TaskEditor from '@/components/TaskEditor.vue'
import FilterEditor from '@/components/FilterEditor.vue'
import TaskList from '@/components/TaskList.vue'
import { buildRows, cloneFilter, matches, sameFilter, type Filter } from '@/lib/filters'
import { dismiss, toasts } from '@/lib/toast'
import { useTasks } from '@/stores/tasks'
import { useViews } from '@/stores/views'

const route = useRoute()
const router = useRouter()
const tasks = useTasks()
const views = useViews()

const navOpen = ref(false)
const search = ref('')
const cursorUid = ref<string | null>(null)
const list = ref<InstanceType<typeof TaskList>>()

const COLLAPSE_KEY = 'taskweb.collapsed'
function readCollapsed(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(COLLAPSE_KEY) ?? '[]')) } catch { return new Set() }
}
const collapsed = ref(readCollapsed())
function toggleCollapsed(uid: string) {
  const next = new Set(collapsed.value)
  if (next.has(uid)) next.delete(uid)
  else next.add(uid)
  collapsed.value = next
  try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify([...next])) } catch { /* private mode */ }
}

const viewId = computed(() => decodeURIComponent(String(route.params.id ?? 'pending')))
const baseView = computed(() => views.find(viewId.value))

// Filter editing works on a draft; the list follows the draft live until it is saved or undone.
const filterOpen = ref(false)
const draft = ref<Filter | null>(null)
const view = computed(() => (draft.value ? { ...baseView.value, filter: draft.value } : baseView.value))
const dirty = computed(() => !!draft.value && !sameFilter(draft.value, baseView.value.filter))
const draftModel = computed({
  get: () => draft.value ?? baseView.value.filter,
  set: (f: Filter) => { draft.value = cloneFilter(f) },
})
const matchCount = computed(() => tasks.all.filter((t) => matches(t, view.value.filter, tasks.tz)).length)
watch(viewId, () => { draft.value = null })

function toggleFilter() {
  filterOpen.value = !filterOpen.value
  if (!filterOpen.value && !dirty.value) draft.value = null
}

function saveSearch(name: string) {
  views.saveView({ ...baseView.value, name, filter: cloneFilter(view.value.filter), builtin: false })
  draft.value = null
}

function saveAsNew(name: string) {
  const id = `saved-${Date.now().toString(36)}`
  views.saveView({ id, name, filter: cloneFilter(view.value.filter), sort: sort.value, builtin: false })
  views.setColumns(id, columns.value)
  draft.value = null
  router.push(`/list/${id}`)
}

function deleteSearch() {
  views.deleteView(baseView.value.id)
  draft.value = null
  filterOpen.value = false
  router.push('/list/pending')
}
const sort = computed(() => views.sortFor(view.value))
const columns = computed(() => views.columnsFor(view.value))
const rows = computed(() =>
  buildRows(tasks.all, { ...view.value, sort: sort.value }, tasks.tz, search.value, collapsed.value))

const selectedUid = computed(() => (typeof route.query.task === 'string' ? route.query.task : null))
const selected = computed(() => (selectedUid.value ? tasks.byUid.get(selectedUid.value) ?? null : null))

function open(uid: string) {
  cursorUid.value = uid
  router.push({ query: { ...route.query, task: uid } })
}
function highlight(uid: string) {
  cursorUid.value = uid
  nextTick(() => document.querySelector(`[data-uid="${CSS.escape(uid)}"]`)?.scrollIntoView({ block: 'nearest' }))
}
function close() {
  const { task: _, ...rest } = route.query
  router.replace({ query: rest })
}

watch(viewId, () => { cursorUid.value = null })

// ------------------------------------------------------------ keyboard
function typing(e: KeyboardEvent) {
  const el = e.target as HTMLElement
  return el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)
}

function moveCursor(by: number) {
  const ids = rows.value.map((r) => r.task.uid)
  if (!ids.length) return
  const i = cursorUid.value ? ids.indexOf(cursorUid.value) : -1
  const next = ids[Math.max(0, Math.min(ids.length - 1, i + by))]
  cursorUid.value = next
  document.querySelector(`[data-uid="${CSS.escape(next)}"]`)?.scrollIntoView({ block: 'nearest' })
  if (selected.value) open(next)
}

function onKey(e: KeyboardEvent) {
  if (e.metaKey || e.ctrlKey || e.altKey) return
  if (e.key === 'Escape' && !typing(e)) {
    if (selected.value) close()
    else cursorUid.value = null
    return
  }
  if (typing(e)) return
  const cur = cursorUid.value
  switch (e.key) {
    case 'n': e.preventDefault(); list.value?.focusQuickAdd(); break
    case '/': e.preventDefault(); list.value?.focusSearch(); break
    case 'j': case 'ArrowDown': e.preventDefault(); moveCursor(1); break
    case 'k': case 'ArrowUp': e.preventDefault(); moveCursor(-1); break
    case 'x': if (cur) list.value?.check(cur); break
    case 's': if (cur) list.value?.star(cur); break
    case 'e': case 'Enter': if (cur) { e.preventDefault(); open(cur) } break
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  await Promise.all([tasks.load(true), views.load().catch(() => {})])
  tasks.startPolling()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  tasks.stopPolling()
})
</script>

<template>
  <div class="shell" :class="{ 'has-editor': !!selected }">
    <SideNav class="side" :active="viewId" :open="navOpen" @close="navOpen = false" />

    <main class="main">
      <p v-if="tasks.offline" class="banner" role="status">Offline. You’re seeing tasks from the last sync, and changes need a connection.</p>
      <p v-else-if="tasks.error" class="banner error" role="alert">
        {{ tasks.error }}
        <button class="btn btn-ghost" @click="tasks.error = null; tasks.load(true)">Retry</button>
      </p>
      <TaskList
        ref="list"
        v-model:search="search"
        :view="view"
        :rows="rows"
        :columns="columns"
        :sort="sort"
        :selected-uid="selectedUid"
        :cursor-uid="cursorUid"
        :collapsed="collapsed"
        @open="open"
        @created="highlight"
        @toggle="toggleCollapsed"
        @menu="navOpen = true"
        @columns="views.setColumns(view.id, $event)"
        @sort="views.setSort(view.id, $event)"
        :filter-open="filterOpen"
        :filter-active="dirty || (!view.builtin && view.filter.conditions.length > 0)"
        @filter="toggleFilter"
      >
        <template #filters>
          <FilterEditor
            v-if="filterOpen"
            v-model="draftModel"
            :view="baseView"
            :dirty="dirty"
            :count="matchCount"
            @save="saveSearch"
            @save-as-new="saveAsNew"
            @remove="deleteSearch"
            @reset="draft = null"
            @close="toggleFilter"
          />
        </template>
      </TaskList>
    </main>

    <Transition name="slide">
      <TaskEditor v-if="selected" :key="selected.uid" class="panel" :task="selected" :view="view" @close="close" @open="open" />
    </Transition>
    <div v-if="selected" class="panel-scrim" @click="close" />

    <ol class="toasts" aria-live="polite">
      <li v-for="t in toasts" :key="t.id" class="toast">
        <span>{{ t.text }}</span>
        <button v-if="t.action" class="btn btn-ghost" @click="t.action.run(); dismiss(t.id)">{{ t.action.label }}</button>
        <button class="icon-btn" aria-label="Dismiss" @click="dismiss(t.id)"><Icon name="x" :size="14" /></button>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  height: 100%;
}
.side { border-right: 1px solid var(--line); }
.main { min-width: 0; overflow-y: auto; background: var(--surface); }
.banner {
  position: sticky; top: 0; z-index: 6;
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  margin: 0; padding: 8px 16px; background: var(--accent-soft); font-size: var(--step--1);
}
.banner.error { background: color-mix(in srgb, var(--rail-late) 16%, var(--surface)); }

/* Editor: a third column on wide screens, a slide-over below that, a full sheet on phones. */
.panel { position: fixed; z-index: 20; top: 0; right: 0; bottom: 0; width: var(--editor-w); box-shadow: var(--shadow-panel); }
.panel-scrim { display: none; }
@media (min-width: 1200px) {
  .shell.has-editor { grid-template-columns: var(--sidebar-w) minmax(0, 1fr) var(--editor-w); }
  .panel { position: static; box-shadow: none; width: auto; }
}
@media (max-width: 1199px) and (min-width: 760px) {
  .panel-scrim { display: block; position: fixed; inset: 0; z-index: 19; }
}
@media (max-width: 759px) {
  .shell { grid-template-columns: minmax(0, 1fr); }
  .side { border: 0; }
  .panel { width: 100%; }
}

.slide-enter-active, .slide-leave-active { transition: transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
@media (min-width: 1200px) {
  .slide-enter-active, .slide-leave-active { transition: none; }
}

.toasts {
  position: fixed;
  z-index: 40;
  left: 50%;
  bottom: calc(16px + var(--safe-b));
  translate: -50% 0;
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
  width: min(440px, calc(100vw - 32px));
}
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 8px 8px 14px;
  border-radius: var(--radius-m);
  background: var(--ink);
  color: var(--surface);
  box-shadow: var(--shadow-panel);
}
.toast span { flex: 1; }
.toast .btn { color: var(--accent-soft); height: 28px; }
.toast .icon-btn { color: inherit; width: 28px; height: 28px; }
</style>
