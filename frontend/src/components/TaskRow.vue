<script setup lang="ts">
import { computed, ref } from 'vue'
import { dayLabel, dayOf, dueLabel, repeatLabel, urgency } from '@/lib/dates'
import { placeOf, type Row } from '@/lib/filters'
import { useTasks } from '@/stores/tasks'
import Icon from './Icon.vue'

const props = defineProps<{
  row: Row
  columns: string[]
  selected: boolean
  cursor: boolean
  collapsed: boolean
}>()
const emit = defineEmits<{
  open: []; toggle: []; check: []; star: []
  dragstart: []; dragend: []; drop: []
}>()

const tasks = useTasks()
const t = computed(() => props.row.task)
const tz = computed(() => tasks.tz)
const done = computed(() => t.value.status === 'COMPLETED' || t.value.status === 'CANCELLED')
const level = computed(() => urgency(t.value, tz.value, tasks.config?.due_this_week_days))
const repeat = computed(() => repeatLabel(t.value))
const place = computed(() => placeOf(t.value))
const brokenPlace = computed(() => t.value.location_alarm && t.value.location_alarm.lon === null)
const PRIORITY_LABEL = { high: 'High', medium: 'Medium', low: 'Low', none: '' }
// ---- swipe (touch): right = complete, left = star
const SWIPE_AT = 80
const dx = ref(0)
const settling = ref(false)
let start: { x: number; y: number; id: number } | null = null
let mode: 'undecided' | 'swipe' | 'scroll' = 'undecided'
let suppressClick = false

function onPointerDown(e: PointerEvent) {
  if (e.pointerType !== 'touch') return
  start = { x: e.clientX, y: e.clientY, id: e.pointerId }
  mode = 'undecided'
}
function onPointerMove(e: PointerEvent) {
  if (!start || e.pointerId !== start.id) return
  const x = e.clientX - start.x
  const y = e.clientY - start.y
  if (mode === 'undecided') {
    if (Math.abs(x) > 10 && Math.abs(x) > Math.abs(y) * 1.5) {
      mode = 'swipe'
      try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId) } catch { /* not capturable */ }
    } else if (Math.abs(y) > 10) {
      mode = 'scroll'
    }
  }
  if (mode === 'swipe') dx.value = Math.max(-120, Math.min(120, x))
}
function onPointerUp() {
  if (mode === 'swipe') {
    suppressClick = true
    if (dx.value >= SWIPE_AT) emit('check')
    else if (dx.value <= -SWIPE_AT) emit('star')
  }
  start = null
  mode = 'undecided'
  settling.value = true
  dx.value = 0
  window.setTimeout(() => { settling.value = false }, 200)
}
function onClick() {
  if (suppressClick) { suppressClick = false; return }
  emit('open')
}

// ---- drag (mouse): drop a task onto this one to make it a subtask
const draggable = window.matchMedia('(pointer: fine)').matches
const dropping = ref(false)
function onDragStart(e: DragEvent) {
  e.dataTransfer?.setData('text/plain', t.value.uid)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
  emit('dragstart')
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  dropping.value = false
  emit('drop')
}

const shortDay = (v: string | null) => (v ? dayLabel(dayOf(v, tz.value), tz.value) : '')
</script>

<template>
  <div class="swipe" :class="{ armed: Math.abs(dx) >= SWIPE_AT }">
  <div class="behind" aria-hidden="true">
    <span v-if="dx > 0" class="act done-act"><Icon name="check" :size="18" />{{ done ? 'Reopen' : 'Complete' }}</span>
    <span v-else-if="dx < 0" class="act star-act">{{ t.starred ? 'Unstar' : 'Star' }}<Icon name="star" :size="18" /></span>
  </div>
  <div
    class="row"
    role="row"
    :data-uid="t.uid"
    :class="[`u-${level}`, { done, selected, cursor, settling, dropping }]"
    :style="dx ? { transform: `translateX(${dx}px)` } : undefined"
    :aria-selected="selected"
    :draggable="draggable"
    @click="onClick"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @dragstart="onDragStart"
    @dragend="emit('dragend')"
    @dragover.prevent="dropping = true"
    @dragleave="dropping = false"
    @drop="onDrop"
  >
    <div class="cell check-cell" role="gridcell">
      <button
        class="check"
        :class="{ on: done }"
        :aria-label="done ? `Reopen ${t.title}` : `Complete ${t.title}`"
        @click.stop="emit('check')"
      >
        <Icon v-if="done" name="check" :size="14" />
      </button>
    </div>

    <template v-for="col in columns" :key="col">
      <div v-if="col === 'title'" class="cell title-cell" role="gridcell" :style="{ paddingLeft: row.depth * 22 + 'px' }">
        <button
          v-if="row.childCount"
          class="twisty"
          :class="{ open: !collapsed }"
          :aria-label="collapsed ? 'Show subtasks' : 'Hide subtasks'"
          :aria-expanded="!collapsed"
          @click.stop="emit('toggle')"
        >
          <Icon name="chevron" :size="14" />
        </button>
        <span class="title">{{ t.title || 'Untitled' }}</span>
        <button
          class="star"
          :class="{ on: t.starred }"
          :aria-label="t.starred ? 'Unstar' : 'Star'"
          :aria-pressed="t.starred"
          @click.stop="emit('star')"
        >
          <Icon name="star" :size="15" />
        </button>
        <!-- phone layout: meta under the title -->
        <span class="meta">
          <span v-if="t.due" class="due">{{ dueLabel(t, tz) }}</span>
          <span v-if="repeat" class="m"><Icon name="repeat" :size="13" />{{ repeat }}</span>
          <span v-if="place" class="m"><Icon name="pin" :size="13" />{{ place }}</span>
          <span v-for="tag in t.tags" :key="tag" class="m">#{{ tag }}</span>
          <span v-if="row.childCount" class="m"><Icon name="sub" :size="13" />{{ row.childCount }}</span>
        </span>
      </div>
      <div v-else-if="col === 'due'" class="cell due" role="gridcell">{{ dueLabel(t, tz) }}</div>
      <div v-else-if="col === 'start'" class="cell muted" role="gridcell">{{ shortDay(t.start) }}</div>
      <div v-else-if="col === 'priority'" class="cell" :class="`p-${t.priority_band}`" role="gridcell">
        {{ PRIORITY_LABEL[t.priority_band] }}
      </div>
      <div v-else-if="col === 'tags'" class="cell tags" role="gridcell">
        <span v-for="tag in t.tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
      <div v-else-if="col === 'place'" class="cell muted" role="gridcell" :title="brokenPlace ? 'Location alert is missing coordinates' : ''">
        {{ place }}<span v-if="brokenPlace" class="warn"> !</span>
      </div>
      <div v-else-if="col === 'repeat'" class="cell muted" role="gridcell">{{ repeat }}</div>
      <div v-else-if="col === 'subtasks'" class="cell muted end" role="gridcell">{{ row.childCount || '' }}</div>
      <div v-else-if="col === 'notes'" class="cell muted clip" role="gridcell">{{ t.notes }}</div>
      <div v-else-if="col === 'created'" class="cell muted" role="gridcell">{{ shortDay(t.created) }}</div>
      <div v-else-if="col === 'modified'" class="cell muted" role="gridcell">{{ shortDay(t.last_modified) }}</div>
      <div v-else-if="col === 'completed'" class="cell muted" role="gridcell">{{ shortDay(t.completed_at) }}</div>
    </template>
  </div>
  </div>
</template>

<style scoped>
.swipe { position: relative; overflow: hidden; }
.behind {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 18px;
  background: var(--line);
  color: var(--muted);
  font-weight: 700;
}
.act { display: inline-flex; align-items: center; gap: 6px; }
.star-act { margin-left: auto; }
.armed .behind { color: var(--accent-ink); }
.armed .behind:has(.done-act) { background: var(--accent); }
.armed .behind:has(.star-act) { background: var(--star); }
.row.settling { transition: transform 0.2s ease; }
.row.dropping { box-shadow: inset 0 0 0 2px var(--accent); background: var(--accent-soft); }
.row {
  position: relative;
  background: var(--surface);
  touch-action: pan-y;
  display: grid;
  grid-template-columns: var(--grid);
  align-items: center;
  min-height: var(--row-h);
  border-bottom: 1px solid var(--line);
  cursor: default;
}
/* The urgency rail: one continuous strip down the list. */
.row::before {
  content: '';
  position: absolute;
  inset: -1px auto 0 0;
  width: 4px;
  background: var(--rail);
}
.u-none { --rail: var(--rail-none); }
.u-far { --rail: var(--rail-far); }
.u-week { --rail: var(--rail-week); }
.u-today { --rail: var(--rail-today); }
.u-late { --rail: var(--rail-late); }

.row:hover { background: color-mix(in srgb, var(--accent-soft) 45%, transparent); }
.row.cursor { background: color-mix(in srgb, var(--accent-soft) 70%, transparent); }
.row.selected { background: var(--accent-soft); }
.row.done .title { color: var(--muted); text-decoration: line-through; text-decoration-color: var(--faint); }

.cell {
  min-width: 0;
  padding: 0 10px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.check-cell { padding: 0 4px 0 14px; display: grid; place-items: center; }
.check {
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 1.5px solid var(--faint);
  border-radius: 5px;
  background: var(--raised);
  color: var(--accent-ink);
}
.check:hover { border-color: var(--accent); }
.check.on { background: var(--accent); border-color: var(--accent); }

.title-cell { display: flex; align-items: center; gap: 6px; }
.title { overflow: hidden; text-overflow: ellipsis; }
.twisty {
  display: grid; place-items: center; flex: none;
  width: 20px; height: 20px; padding: 0; margin-left: -4px;
  border: 0; border-radius: var(--radius-s); background: transparent; color: var(--muted);
  transition: transform 0.15s;
}
.twisty.open { transform: rotate(90deg); }
.star {
  display: grid; place-items: center; flex: none;
  width: 24px; height: 24px; padding: 0;
  border: 0; background: transparent; color: var(--faint);
  opacity: 0;
}
.row:hover .star, .star:focus-visible { opacity: 1; }
.star.on { opacity: 1; color: var(--star); }
.star.on :deep(path) { fill: currentColor; }
.meta { display: none; }

.due { color: var(--ink); }
.u-late .due { color: var(--rail-late); font-weight: 700; }
.u-today .due { color: var(--rail-today); font-weight: 700; }
.muted { color: var(--muted); }
.end { text-align: right; }
.p-high { color: var(--rail-late); font-weight: 700; }
.p-medium { color: var(--ink); }
.p-low { color: var(--muted); }
.tags { display: flex; gap: 4px; }
.tag {
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--ground);
  border: 1px solid var(--line);
  font-size: var(--step--1);
  color: var(--muted);
}
.warn { color: var(--rail-late); font-weight: 700; }

/* Phone: single column with the meta line under the title */
@media (max-width: 759px) {
  .row { grid-template-columns: 44px 1fr; padding: 8px 8px 8px 0; align-items: start; }
  .row > .cell:not(.check-cell):not(.title-cell) { display: none; }
  .check-cell { padding: 2px 0 0 12px; }
  .check { width: 22px; height: 22px; border-radius: 6px; }
  .title-cell { flex-wrap: wrap; white-space: normal; row-gap: 2px; padding-right: 4px; }
  .title { flex: 1 1 0; white-space: normal; line-height: 1.3; padding-top: 1px; }
  .star { opacity: 1; width: 32px; height: 28px; margin: -3px -4px 0 0; }
  .star:not(.on) { color: var(--line); }
  .meta {
    display: flex; flex-wrap: wrap; gap: 2px 10px; flex-basis: 100%;
    font-size: var(--step--1); color: var(--muted);
  }
  .meta .m { display: inline-flex; align-items: center; gap: 3px; }
}
</style>
