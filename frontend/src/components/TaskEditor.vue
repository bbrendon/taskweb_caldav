<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { dayLabel, dayOf, dueLabel, timeOf } from '@/lib/dates'
import type { View } from '@/lib/filters'
import { localDateTime } from '@/lib/quickadd'
import { toast } from '@/lib/toast'
import type { PriorityBand, Task, TaskPatch } from '@/lib/types'
import { useTasks } from '@/stores/tasks'
import Icon from './Icon.vue'
import QuickAdd from './QuickAdd.vue'
import RepeatEditor from './RepeatEditor.vue'

const props = defineProps<{ task: Task; view: View }>()
const emit = defineEmits<{ close: []; open: [uid: string] }>()

const tasks = useTasks()
const tz = computed(() => tasks.tz)
const t = computed(() => props.task)
const done = computed(() => t.value.status === 'COMPLETED' || t.value.status === 'CANCELLED')

// Text fields keep a local draft and save on blur, so typing never fights the poller.
const title = ref('')
const notes = ref('')
const url = ref('')
const tagDraft = ref('')
const titleEl = ref<HTMLTextAreaElement>()
const confirmingDelete = ref(false)

function syncDrafts(force = false) {
  const active = document.activeElement
  if (force || active?.id !== 'ed-title') title.value = t.value.title
  if (force || active?.id !== 'ed-notes') notes.value = t.value.notes
  if (force || active?.id !== 'ed-url') url.value = t.value.url
}
watch(() => t.value.uid, () => { syncDrafts(true); confirmingDelete.value = false; nextTick(autosize) }, { immediate: true })
watch(() => [t.value.title, t.value.notes, t.value.url], () => syncDrafts())

function save(patch: TaskPatch) {
  tasks.update(t.value.uid, patch).catch(() => {})
}

function saveText(field: 'title' | 'notes' | 'url', value: string) {
  const v = field === 'title' ? value.replace(/\s*\n\s*/g, ' ').trim() || 'Untitled' : value
  if (v !== t.value[field]) save({ [field]: v })
}

function autosize() {
  const el = titleEl.value
  if (el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' }
}

// ---- due / start / alarm
const dueDay = computed(() => (t.value.due ? dayOf(t.value.due, tz.value) : ''))
const dueTime = computed(() => (t.value.due ? timeOf(t.value.due, tz.value) ?? '' : ''))
const showTime = ref(false)
watch(() => t.value.uid, () => { showTime.value = !!dueTime.value }, { immediate: true })

function setDue(day: string, time: string) {
  if (!day) return save({ due: null })
  save({ due: time ? localDateTime(day, time, tz.value) : day })
}

const startDay = computed(() => (t.value.start ? dayOf(t.value.start, tz.value) : ''))

const absAlarm = computed(() => t.value.alarms.find((a) => a.at))
const relAlarms = computed(() => t.value.alarms.filter((a) => a.offset))
const alarmLocal = computed(() => {
  const at = absAlarm.value?.at
  return at ? `${dayOf(at, tz.value)}T${timeOf(at, tz.value) ?? '09:00'}` : ''
})
function setAlarm(v: string) {
  const others = relAlarms.value
  if (!v) return save({ alarms: others })
  const [day, time] = v.split('T')
  save({ alarms: [...others, { at: localDateTime(day, time.slice(0, 5), tz.value) }] })
}
function offsetLabel(offset: string, related?: string | null) {
  const m = /^(-)?P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?/.exec(offset)
  if (!m) return offset
  const parts = [m[2] && `${m[2]} d`, m[3] && `${m[3]} h`, m[4] && `${m[4]} min`].filter(Boolean).join(' ') || 'At the time'
  return `${parts} ${m[1] ? 'before' : 'after'} ${related === 'START' ? 'start' : 'due'}`
}

// ---- priority
const BANDS: [PriorityBand, string, number][] = [['none', 'None', 0], ['low', 'Low', 9], ['medium', 'Medium', 5], ['high', 'High', 1]]

// ---- tags
function addTag() {
  const v = tagDraft.value.trim().replace(/^#/, '')
  tagDraft.value = ''
  if (v && !t.value.tags.some((x) => x.toLowerCase() === v.toLowerCase())) save({ tags: [...t.value.tags, v] })
}
const removeTag = (tag: string) => save({ tags: t.value.tags.filter((x) => x !== tag) })

// ---- place
const places = computed(() => tasks.config?.places ?? [])
const placeName = computed(() => t.value.location_alarm?.title || t.value.location || '')
const brokenPlace = computed(() => !!t.value.location_alarm && t.value.location_alarm.lon === null)
function setPlace(name: string) {
  if (!name) return save({ location: '', location_alarm: null })
  const p = places.value.find((x) => x.name === name)
  if (!p) return
  save({
    location: p.name,
    location_alarm: {
      title: p.name, address: p.address, lat: p.lat, lon: p.lon, radius: p.radius,
      proximity: t.value.location_alarm?.proximity ?? 'ARRIVE',
    },
  })
}
function setProximity(proximity: 'ARRIVE' | 'DEPART') {
  const la = t.value.location_alarm
  if (la && la.lat !== null && la.lon !== null) save({ location_alarm: { ...la, proximity } })
}

// ---- hierarchy
const descendants = computed(() => {
  const out = new Set<string>()
  const walk = (uid: string) => tasks.all.filter((x) => x.parent_uid === uid).forEach((c) => { out.add(c.uid); walk(c.uid) })
  walk(t.value.uid)
  return out
})
const parentOptions = computed(() =>
  tasks.all
    .filter((x) => x.uid !== t.value.uid && !descendants.value.has(x.uid) &&
      (x.uid === t.value.parent_uid || (x.status !== 'COMPLETED' && x.status !== 'CANCELLED')))
    .sort((a, b) => a.title.localeCompare(b.title)))
const children = computed(() => tasks.all.filter((x) => x.parent_uid === t.value.uid)
  .sort((a, b) => Number(a.status === 'COMPLETED') - Number(b.status === 'COMPLETED') || a.title.localeCompare(b.title)))

// ---- actions
async function toggleDone() {
  try {
    if (done.value) await tasks.reopen(t.value.uid)
    else {
      const res = await tasks.complete(t.value.uid)
      if (res.status !== 'COMPLETED' && res.due) toast(`Done. Next due ${dueLabel(res, tz.value)}`)
    }
  } catch { /* surfaced by store */ }
}
async function skip() {
  try {
    const res = await tasks.skip(t.value.uid)
    toast(`Skipped. Next due ${dueLabel(res, tz.value)}`)
  } catch { /* surfaced by store */ }
}
async function remove(children: 'orphan' | 'delete') {
  const name = t.value.title
  try {
    await tasks.remove(t.value.uid, children)
    toast(`Deleted “${name}”`)
    emit('close')
  } catch { /* surfaced by store */ }
}

const history = computed(() => [...t.value.completions].reverse())
const fmtStamp = (iso: string) =>
  new Intl.DateTimeFormat('en-US', { timeZone: tz.value, month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' })
    .format(new Date(iso))
const shortDay = (v: string | null) => (v ? dayLabel(dayOf(v, tz.value), tz.value) : '')
</script>

<template>
  <aside class="editor" aria-label="Edit task" @keydown.esc.stop="emit('close')">
    <header class="bar">
      <button class="icon-btn" aria-label="Close" @click="emit('close')"><Icon name="x" /></button>
      <button class="btn" :class="done ? '' : 'btn-primary'" @click="toggleDone">
        <Icon :name="done ? 'undo' : 'check'" :size="16" />{{ done ? 'Reopen' : (t.recur_after || t.rrule ? 'Done for now' : 'Complete') }}
      </button>
      <button v-if="(t.recur_after || t.rrule) && !done" class="btn btn-ghost" @click="skip">
        <Icon name="skip" :size="16" />Skip
      </button>
      <button class="icon-btn star" :class="{ on: t.starred }" :aria-pressed="t.starred"
              :aria-label="t.starred ? 'Unstar' : 'Star'" @click="save({ starred: !t.starred })">
        <Icon name="star" />
      </button>
    </header>

    <div class="body">
      <label for="ed-title" class="sr-only">Title</label>
      <textarea id="ed-title" ref="titleEl" v-model="title" class="title" rows="1" placeholder="Untitled"
                @input="autosize" @blur="saveText('title', title)"
                @keydown.enter.prevent="($event.target as HTMLElement).blur()" />

      <dl class="fields">
        <dt><label for="ed-due">Due</label></dt>
        <dd class="inline">
          <input id="ed-due" class="field date" type="date" :value="dueDay"
                 @change="setDue(($event.target as HTMLInputElement).value, showTime ? dueTime : '')" />
          <input v-if="showTime" class="field time" type="time" :value="dueTime" aria-label="Due time"
                 @change="setDue(dueDay || '', ($event.target as HTMLInputElement).value)" />
          <button v-else-if="dueDay" class="btn btn-ghost" @click="showTime = true">Add time</button>
          <button v-if="showTime" class="icon-btn" aria-label="Remove time" @click="showTime = false; setDue(dueDay, '')"><Icon name="x" :size="15" /></button>
          <button v-if="dueDay && !showTime" class="icon-btn" aria-label="Clear due date" @click="setDue('', '')"><Icon name="x" :size="15" /></button>
        </dd>

        <dt>Repeat</dt>
        <dd>
          <RepeatEditor :recur-after="t.recur_after" :rrule="t.rrule" @change="save($event)" />
          <p v-if="t.rrule && !t.due" class="note">A schedule repeats from the due date. Set one so it knows where to start.</p>
        </dd>

        <dt><label for="ed-start">Starts</label></dt>
        <dd class="inline">
          <input id="ed-start" class="field date" type="date" :value="startDay"
                 @change="save({ start: ($event.target as HTMLInputElement).value || null })" />
          <button v-if="startDay" class="icon-btn" aria-label="Clear start date" @click="save({ start: null })"><Icon name="x" :size="15" /></button>
          <span class="note">Hidden from lists until then</span>
        </dd>

        <dt>Priority</dt>
        <dd>
          <div class="seg" role="radiogroup" aria-label="Priority">
            <button v-for="[band, label, value] in BANDS" :key="band" role="radio" :aria-checked="t.priority_band === band"
                    :class="[{ on: t.priority_band === band }, band]" @click="save({ priority: value })">{{ label }}</button>
          </div>
        </dd>

        <dt><label for="ed-tag">Tags</label></dt>
        <dd>
          <div class="tags">
            <span v-for="tag in t.tags" :key="tag" class="tag">
              {{ tag }}<button :aria-label="`Remove tag ${tag}`" @click="removeTag(tag)"><Icon name="x" :size="12" /></button>
            </span>
            <input id="ed-tag" v-model="tagDraft" class="tag-input" list="tag-suggestions" placeholder="Add tag"
                   @keydown.enter.prevent="addTag" @change="addTag" />
            <datalist id="tag-suggestions">
              <option v-for="tag in tasks.allTags.filter((x) => !t.tags.includes(x))" :key="tag" :value="tag" />
            </datalist>
          </div>
        </dd>

        <dt><label for="ed-place">Place</label></dt>
        <dd>
          <div class="inline">
            <select id="ed-place" class="field" :value="places.some((p) => p.name === placeName) ? placeName : (placeName ? '__other' : '')"
                    @change="setPlace(($event.target as HTMLSelectElement).value)">
              <option value="">None</option>
              <option v-for="p in places" :key="p.name" :value="p.name">{{ p.name }}</option>
              <option v-if="placeName && !places.some((p) => p.name === placeName)" value="__other" disabled>{{ placeName }}</option>
            </select>
            <select v-if="t.location_alarm && !brokenPlace" class="field" :value="t.location_alarm.proximity" aria-label="Alert when"
                    @change="setProximity(($event.target as HTMLSelectElement).value as 'ARRIVE' | 'DEPART')">
              <option value="ARRIVE">When arriving</option>
              <option value="DEPART">When leaving</option>
            </select>
          </div>
          <p v-if="brokenPlace" class="note warn">This location alert is missing coordinates, so iPhone can’t trigger it. Pick a place to fix it.</p>
          <p v-else-if="t.location_alarm" class="note">iPhone Reminders alerts you {{ t.location_alarm.proximity === 'ARRIVE' ? 'when you arrive' : 'when you leave' }}.</p>
        </dd>

        <dt><label for="ed-alarm">Remind me</label></dt>
        <dd>
          <div class="inline">
            <input id="ed-alarm" class="field" type="datetime-local" :value="alarmLocal"
                   @change="setAlarm(($event.target as HTMLInputElement).value)" />
            <button v-if="alarmLocal" class="icon-btn" aria-label="Remove reminder" @click="setAlarm('')"><Icon name="x" :size="15" /></button>
          </div>
          <p v-for="(a, i) in relAlarms" :key="i" class="note">
            <Icon name="bell" :size="13" /> {{ offsetLabel(a.offset!, a.related) }}
          </p>
        </dd>

        <dt><label for="ed-parent">Subtask of</label></dt>
        <dd>
          <select id="ed-parent" class="field" :value="t.parent_uid ?? ''"
                  @change="save({ parent_uid: ($event.target as HTMLSelectElement).value || null })">
            <option value="">Nothing (top level)</option>
            <option v-for="p in parentOptions" :key="p.uid" :value="p.uid">{{ p.title }}</option>
          </select>
        </dd>

        <dt><label for="ed-url">Link</label></dt>
        <dd class="inline">
          <input id="ed-url" v-model="url" class="field" type="url" inputmode="url" placeholder="https://"
                 @blur="saveText('url', url)" @keydown.enter.prevent="($event.target as HTMLElement).blur()" />
          <a v-if="t.url" :href="t.url" target="_blank" rel="noopener noreferrer" class="btn btn-ghost">Open</a>
        </dd>
      </dl>

      <label for="ed-notes" class="section-label">Notes</label>
      <textarea id="ed-notes" v-model="notes" class="field notes" placeholder="Add notes"
                @blur="saveText('notes', notes)" />

      <h3 class="section-label">Subtasks</h3>
      <ul class="kids">
        <li v-for="c in children" :key="c.uid" :class="{ done: c.status === 'COMPLETED' }">
          <button class="check" :class="{ on: c.status === 'COMPLETED' }"
                  :aria-label="c.status === 'COMPLETED' ? `Reopen ${c.title}` : `Complete ${c.title}`"
                  @click="c.status === 'COMPLETED' ? tasks.reopen(c.uid) : tasks.complete(c.uid)">
            <Icon v-if="c.status === 'COMPLETED'" name="check" :size="13" />
          </button>
          <button class="kid-title" @click="emit('open', c.uid)">{{ c.title }}</button>
        </li>
      </ul>
      <QuickAdd class="kid-add" :view="view" :parent-uid="t.uid" />

      <template v-if="history.length">
        <h3 class="section-label">Done {{ history.length }} {{ history.length === 1 ? 'time' : 'times' }}</h3>
        <ol class="history">
          <li v-for="h in history.slice(0, 12)" :key="h">{{ fmtStamp(h) }}</li>
        </ol>
      </template>

      <footer class="foot">
        <p class="meta">Created {{ shortDay(t.created) }}. Last edited {{ shortDay(t.last_modified).toLowerCase() === 'today' ? 'today' : shortDay(t.last_modified) }}.</p>
        <template v-if="!confirmingDelete">
          <button class="btn btn-ghost btn-danger" @click="confirmingDelete = true"><Icon name="trash" :size="16" />Delete</button>
        </template>
        <div v-else class="confirm">
          <p v-if="children.length">“{{ t.title }}” has {{ children.length }} subtask{{ children.length > 1 ? 's' : '' }}.</p>
          <p v-else>Delete “{{ t.title }}”?</p>
          <div class="inline">
            <template v-if="children.length">
              <button class="btn btn-danger" @click="remove('delete')">Delete with subtasks</button>
              <button class="btn" @click="remove('orphan')">Delete, keep subtasks</button>
            </template>
            <button v-else class="btn btn-danger" @click="remove('orphan')">Delete</button>
            <button class="btn btn-ghost" @click="confirmingDelete = false">Cancel</button>
          </div>
        </div>
      </footer>
    </div>
  </aside>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--raised);
  border-left: 1px solid var(--line);
}
.bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: calc(10px + var(--safe-t)) 12px 10px;
  border-bottom: 1px solid var(--line);
}
.bar .star { margin-left: auto; }
.star.on { color: var(--star); }
.star.on :deep(path) { fill: currentColor; }
.body { flex: 1; overflow-y: auto; padding: 16px 18px calc(32px + var(--safe-b)); }

.title {
  width: 100%;
  margin: 0 0 14px;
  padding: 2px 0;
  border: 0;
  background: transparent;
  font-size: var(--step-2);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.01em;
  resize: none;
  overflow: hidden;
  outline: none;
}

.fields {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 12px 12px;
  margin: 0 0 18px;
  align-items: start;
}
dt { padding-top: 7px; color: var(--muted); font-size: var(--step--1); }
dd { margin: 0; min-width: 0; }
.inline { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.inline .field { width: auto; flex: 1 1 140px; }
.date { flex: 0 1 150px !important; }
.time { flex: 0 1 120px !important; }
.note { display: flex; align-items: center; gap: 4px; margin: 6px 0 0; color: var(--muted); font-size: var(--step--1); }
.inline .note { margin: 0; }
.warn { color: var(--rail-late); }

.seg { display: flex; padding: 2px; border-radius: var(--radius-m); background: var(--ground); }
.seg button { flex: 1; height: 30px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); }
.seg button.on { background: var(--raised); color: var(--ink); box-shadow: 0 1px 2px rgb(0 0 0 / 0.08); }
.seg button.on.high { color: var(--rail-late); font-weight: 700; }

.tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; min-height: 34px; }
.tag {
  display: inline-flex; align-items: center; gap: 2px;
  padding: 2px 4px 2px 9px; border-radius: 999px; background: var(--accent-soft);
}
.tag button { display: grid; place-items: center; width: 20px; height: 20px; padding: 0; border: 0; background: none; color: var(--muted); border-radius: 50%; }
.tag button:hover { color: var(--ink); }
.tag-input { flex: 1 1 90px; min-width: 90px; height: 30px; border: 0; background: transparent; outline: none; }

.section-label { display: block; margin: 20px 0 8px; font-size: var(--step--1); font-weight: 600; color: var(--muted); }
.notes { min-height: 120px; }

.kids { list-style: none; margin: 0; padding: 0; }
.kids li { display: flex; align-items: center; gap: 8px; min-height: 34px; border-bottom: 1px solid var(--line); }
.kids li.done .kid-title { color: var(--muted); text-decoration: line-through; }
.kid-title { flex: 1; padding: 6px 0; border: 0; background: none; text-align: left; }
.kid-add { margin-top: 2px; border-radius: var(--radius-m); border: 1px dashed var(--line); background: transparent; }
.check {
  display: grid; place-items: center; flex: none; width: 18px; height: 18px; padding: 0;
  border: 1.5px solid var(--faint); border-radius: 5px; background: var(--raised); color: var(--accent-ink);
}
.check.on { background: var(--accent); border-color: var(--accent); }

.history { margin: 0; padding-left: 18px; color: var(--muted); font-size: var(--step--1); line-height: 1.7; }

.foot { margin-top: 28px; padding-top: 14px; border-top: 1px solid var(--line); display: grid; gap: 10px; justify-items: start; }
.meta { margin: 0; color: var(--faint); font-size: var(--step--1); }
.confirm p { margin: 0 0 8px; }

@media (max-width: 759px) {
  .fields { grid-template-columns: 1fr; gap: 4px; }
  dt { padding-top: 10px; }
  .field { height: 42px; }
  .seg button { height: 36px; }
}
</style>
