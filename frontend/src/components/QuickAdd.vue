<script setup lang="ts">
import { computed, ref } from 'vue'
import { today } from '@/lib/dates'
import type { View } from '@/lib/filters'
import { parseQuickAdd } from '@/lib/quickadd'
import { toast } from '@/lib/toast'
import type { TaskPatch } from '@/lib/types'
import { useTasks } from '@/stores/tasks'
import Icon from './Icon.vue'

const props = defineProps<{ view: View; parentUid?: string | null }>()
const emit = defineEmits<{ created: [uid: string] }>()

const tasks = useTasks()
const text = ref('')
const busy = ref(false)
const input = ref<HTMLInputElement>()

const parsed = computed(() => parseQuickAdd(text.value, tasks.tz, tasks.config?.places ?? []))

/** New tasks inherit what the current list is about, so they don't vanish on creation. */
function contextDefaults(): TaskPatch {
  const d: TaskPatch = {}
  for (const c of props.view.filter.conditions) {
    if (c.field === 'tag' && c.op === 'has') d.tags = [String(c.value)]
    if (c.field === 'smart' && c.value === 'STARRED') d.starred = true
    if (c.field === 'smart' && c.value === 'HIGH') d.priority = 1
    if (c.field === 'smart' && (c.value === 'DUE_TODAY' || c.value === 'DUE_WEEK')) d.due = today(tasks.tz)
    if (c.field === 'place' && c.op === 'is') {
      const p = tasks.config?.places.find((x) => x.name === c.value)
      if (p) {
        d.location = p.name
        d.location_alarm = { title: p.name, address: p.address, lat: p.lat, lon: p.lon, radius: p.radius, proximity: 'ARRIVE' }
      }
    }
  }
  return d
}

async function submit() {
  const { title, patch } = parsed.value
  if (!title || busy.value) return
  busy.value = true
  const defaults = contextDefaults()
  const merged: TaskPatch = { ...defaults, ...patch }
  if (defaults.tags || patch.tags) merged.tags = [...new Set([...(defaults.tags ?? []), ...(patch.tags ?? [])])]
  if (props.parentUid) merged.parent_uid = props.parentUid
  try {
    const t = await tasks.create(merged)
    text.value = ''
    emit('created', t.uid)
  } catch (e) {
    toast((e as Error).message)
  } finally {
    busy.value = false
    input.value?.focus()
  }
}

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
  <form class="quick" @submit.prevent="submit">
    <Icon name="plus" class="plus" />
    <label class="sr-only" for="quick-add">{{ parentUid ? 'Add a subtask' : 'Add a task' }}</label>
    <input
      id="quick-add"
      ref="input"
      v-model="text"
      class="input"
      :placeholder="parentUid ? 'Add a subtask' : 'Add a task, e.g. Charge batteries fri #drone every 2w'"
      autocomplete="off"
      enterkeyhint="done"
      :disabled="busy"
      @keydown.esc="text = ''; input?.blur()"
    />
    <ul v-if="text && parsed.chips.length" class="chips" aria-label="Recognized">
      <li v-for="c in parsed.chips" :key="c.kind + c.label" :class="c.kind">{{ c.label }}</li>
    </ul>
  </form>
</template>

<style scoped>
.quick {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
  min-height: var(--row-h);
  padding: 4px 12px 4px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--raised);
}
.plus { color: var(--accent); flex: none; }
.input {
  flex: 1 1 200px;
  min-width: 0;
  height: 30px;
  border: 0;
  background: transparent;
  outline: none;
}
.input::placeholder { color: var(--faint); }
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin: 0 0 4px 26px;
  padding: 0;
  list-style: none;
  flex-basis: 100%;
}
.chips li {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--ink);
  font-size: var(--step--1);
}
</style>
