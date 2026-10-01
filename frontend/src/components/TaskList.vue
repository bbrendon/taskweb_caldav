<script setup lang="ts">
import { computed, ref } from 'vue'
import { columnById } from '@/lib/columns'
import { dueLabel } from '@/lib/dates'
import type { Row, Sort, View } from '@/lib/filters'
import { toast } from '@/lib/toast'
import { useTasks } from '@/stores/tasks'
import ColumnMenu from './ColumnMenu.vue'
import Icon from './Icon.vue'
import QuickAdd from './QuickAdd.vue'
import TaskRow from './TaskRow.vue'

const props = defineProps<{
  view: View
  rows: Row[]
  columns: string[]
  sort: Sort[]
  selectedUid: string | null
  cursorUid: string | null
  collapsed: Set<string>
}>()
const emit = defineEmits<{
  open: [uid: string]
  created: [uid: string]
  toggle: [uid: string]
  menu: []
  columns: [cols: string[]]
  sort: [sort: Sort[]]
}>()

const search = defineModel<string>('search', { required: true })
const tasks = useTasks()
const quick = ref<InstanceType<typeof QuickAdd>>()
const searchInput = ref<HTMLInputElement>()

const grid = computed(() =>
  ['44px', ...props.columns.map((id) => columnById(id)?.width ?? '100px')].join(' '))

function sortBy(id: string) {
  const key = columnById(id)?.sortKey
  if (!key) return
  const cur = props.sort[0]
  const dir = cur?.key === key && cur.dir === 'asc' ? 'desc' : 'asc'
  emit('sort', [{ key, dir }, ...props.sort.filter((s) => s.key !== key).slice(0, 1)])
}

function ariaSort(id: string) {
  const key = columnById(id)?.sortKey
  const cur = props.sort[0]
  if (!key || cur?.key !== key) return undefined
  return cur.dir === 'asc' ? 'ascending' : 'descending'
}

async function check(uid: string) {
  const t = tasks.byUid.get(uid)
  if (!t) return
  try {
    if (t.status === 'COMPLETED' || t.status === 'CANCELLED') {
      await tasks.reopen(uid)
      return
    }
    const openKids = tasks.all.filter((x) => x.parent_uid === uid && x.status !== 'COMPLETED' && x.status !== 'CANCELLED')
    if (openKids.length && !t.recur_after && !t.rrule &&
        !window.confirm(`“${t.title}” has ${openKids.length} open subtask${openKids.length > 1 ? 's' : ''}. Complete it anyway?`)) {
      return
    }
    const res = await tasks.complete(uid)
    if (res.status === 'COMPLETED') {
      toast(`Completed “${res.title}”`, { label: 'Undo', run: () => tasks.reopen(uid) })
    } else if (res.due) {
      const when = dueLabel(res, tasks.tz).replace(/^(Today|Tomorrow)/, (w) => w.toLowerCase())
      toast(`Done. Next due ${when}`)
    }
  } catch {
    /* error surfaced by the store */
  }
}

function star(uid: string) {
  const t = tasks.byUid.get(uid)
  if (t) tasks.update(uid, { starred: !t.starred }).catch(() => {})
}

defineExpose({
  focusQuickAdd: () => quick.value?.focus(),
  focusSearch: () => searchInput.value?.focus(),
  check,
  star,
})
</script>

<template>
  <section class="list" :style="{ '--grid': grid }" aria-labelledby="list-title">
    <header class="top">
      <button class="icon-btn menu" aria-label="Open lists" @click="emit('menu')"><Icon name="menu" /></button>
      <h1 id="list-title">{{ view.name }}</h1>
      <span class="n">{{ rows.length }}</span>
      <div class="search">
        <Icon name="search" :size="16" class="glass" />
        <label for="search" class="sr-only">Search tasks</label>
        <input id="search" ref="searchInput" v-model="search" class="field" type="search"
               placeholder="Search" autocomplete="off" @keydown.esc="search = ''; searchInput?.blur()" />
      </div>
      <span class="cols"><ColumnMenu :columns="columns" @change="emit('columns', $event)" /></span>
    </header>

    <QuickAdd ref="quick" :view="view" @created="emit('created', $event)" />

    <div class="grid" role="grid" :aria-rowcount="rows.length">
      <div class="row-head" role="row">
        <span role="columnheader"><span class="sr-only">Done</span></span>
        <span
          v-for="id in columns"
          :key="id"
          role="columnheader"
          :aria-sort="ariaSort(id)"
          :class="{ end: columnById(id)?.align === 'end' }"
        >
          <button v-if="columnById(id)?.sortKey" class="sort" @click="sortBy(id)">
            {{ columnById(id)?.label }}
            <span v-if="sort[0]?.key === columnById(id)?.sortKey" class="arrow">{{ sort[0].dir === 'asc' ? '↑' : '↓' }}</span>
          </button>
          <template v-else>{{ columnById(id)?.label }}</template>
        </span>
      </div>

      <TaskRow
        v-for="row in rows"
        :key="row.task.uid"
        :row="row"
        :columns="columns"
        :selected="row.task.uid === selectedUid"
        :cursor="row.task.uid === cursorUid"
        :collapsed="collapsed.has(row.task.uid)"
        @open="emit('open', row.task.uid)"
        @toggle="emit('toggle', row.task.uid)"
        @check="check(row.task.uid)"
        @star="star(row.task.uid)"
      />

      <div v-if="!rows.length && !tasks.loading" class="empty">
        <template v-if="search">
          <p>No tasks match “{{ search }}”.</p>
          <button class="btn" @click="search = ''">Clear search</button>
        </template>
        <template v-else-if="view.id === 'overdue' || view.id === 'today'">
          <p>Nothing overdue or due today.</p>
        </template>
        <template v-else>
          <p>No tasks here. Add one above.</p>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.list {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--surface);
}
.top {
  position: sticky;
  top: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: calc(12px + var(--safe-t)) 12px 12px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
}
.menu { display: none; margin-left: -8px; }
h1 {
  margin: 0;
  font-size: var(--step-2);
  font-weight: 700;
  letter-spacing: -0.015em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.n { color: var(--muted); font-size: var(--step-1); }
.search { position: relative; margin-left: auto; width: min(260px, 40vw); }
.search .field { padding-left: 32px; background: var(--ground); border-color: transparent; }
.search .field:focus { background: var(--raised); }
.glass { position: absolute; left: 10px; top: 50%; translate: 0 -50%; color: var(--muted); pointer-events: none; }

.row-head {
  display: grid;
  grid-template-columns: var(--grid);
  align-items: center;
  height: 30px;
  border-bottom: 1px solid var(--line);
  color: var(--muted);
  font-size: var(--step--1);
}
.row-head > span { padding: 0 10px; white-space: nowrap; overflow: hidden; }
.row-head > .end { text-align: right; }
.sort {
  display: inline-flex; gap: 4px; padding: 0; border: 0; background: none; color: inherit; font-size: inherit;
}
.sort:hover { color: var(--ink); }
.arrow { color: var(--accent); }

.empty {
  display: grid;
  justify-items: start;
  gap: 10px;
  padding: 28px 16px 28px 58px;
  color: var(--muted);
}
.empty p { margin: 0; }

@media (max-width: 759px) {
  .menu { display: inline-grid; }
  .top { flex-wrap: wrap; row-gap: 10px; padding-bottom: 10px; }
  .search { order: 10; flex-basis: 100%; width: auto; }
  .search .field { height: 40px; }
  .cols { display: none; }
  .row-head { display: none; }
  .empty { padding-left: 56px; }
}
</style>
