<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { parseInterval } from '@/lib/dates'

const props = defineProps<{ recurAfter: string | null; rrule: string | null }>()
const emit = defineEmits<{ change: [value: { recur_after: string | null; rrule: string | null }] }>()

type Kind = 'none' | 'after' | 'fixed'
type Unit = 'D' | 'W' | 'M' | 'Y'
const FREQ: Record<Unit, string> = { D: 'DAILY', W: 'WEEKLY', M: 'MONTHLY', Y: 'YEARLY' }
const UNITS: [Unit, string][] = [['D', 'days'], ['W', 'weeks'], ['M', 'months'], ['Y', 'years']]
const WEEK: [string, string][] = [['MO', 'M'], ['TU', 'T'], ['WE', 'W'], ['TH', 'T'], ['FR', 'F'], ['SA', 'S'], ['SU', 'S']]
const WEEK_NAMES: Record<string, string> = { MO: 'Monday', TU: 'Tuesday', WE: 'Wednesday', TH: 'Thursday', FR: 'Friday', SA: 'Saturday', SU: 'Sunday' }

const kind = ref<Kind>('none')
const n = ref(1)
const unit = ref<Unit>('D')
const byDay = ref<string[]>([])
const monthDay = ref<number | null>(null)
const custom = ref<string | null>(null) // an RRULE this editor can't represent; kept as-is

function load() {
  custom.value = null
  byDay.value = []
  monthDay.value = null
  const iv = parseInterval(props.recurAfter)
  if (iv) {
    kind.value = 'after'; n.value = iv.n; unit.value = iv.unit
    return
  }
  if (props.rrule) {
    kind.value = 'fixed'
    const p = Object.fromEntries(props.rrule.split(';').map((kv) => kv.split('=')))
    const u = (Object.keys(FREQ) as Unit[]).find((k) => FREQ[k] === p.FREQ)
    const known = new Set(['FREQ', 'INTERVAL', 'BYDAY', 'BYMONTHDAY', 'WKST'])
    if (!u || Object.keys(p).some((k) => !known.has(k)) || (p.BYMONTHDAY && p.BYMONTHDAY.includes(','))) {
      custom.value = props.rrule
      return
    }
    unit.value = u
    n.value = Number(p.INTERVAL ?? 1)
    byDay.value = p.BYDAY ? String(p.BYDAY).split(',') : []
    monthDay.value = p.BYMONTHDAY ? Number(p.BYMONTHDAY) : null
    return
  }
  kind.value = 'none'
}
watch(() => [props.recurAfter, props.rrule], load, { immediate: true })

const rule = computed(() => {
  const parts = [`FREQ=${FREQ[unit.value]}`]
  if (n.value > 1) parts.push(`INTERVAL=${n.value}`)
  if (unit.value === 'W' && byDay.value.length) parts.push(`BYDAY=${byDay.value.join(',')}`)
  if (unit.value === 'M' && monthDay.value) parts.push(`BYMONTHDAY=${monthDay.value}`)
  return parts.join(';')
})

function commit() {
  n.value = Math.max(1, Math.min(999, Math.round(n.value || 1)))
  if (kind.value === 'none') emit('change', { recur_after: null, rrule: null })
  else if (kind.value === 'after') emit('change', { recur_after: `P${n.value}${unit.value}`, rrule: null })
  else if (custom.value) emit('change', { recur_after: null, rrule: custom.value })
  else emit('change', { recur_after: null, rrule: rule.value })
}

function setKind(k: Kind) {
  kind.value = k
  if (k !== 'fixed') custom.value = null
  commit()
}

function toggleDay(d: string) {
  byDay.value = byDay.value.includes(d) ? byDay.value.filter((x) => x !== d) : [...byDay.value, d]
  commit()
}

const unitWord = computed(() => UNITS.find(([u]) => u === unit.value)![1].replace(/s$/, n.value === 1 ? '' : 's'))
</script>

<template>
  <div class="repeat">
    <div class="seg" role="radiogroup" aria-label="Repeat">
      <button v-for="[k, label] in ([['none', 'Never'], ['after', 'After done'], ['fixed', 'Schedule']] as const)"
              :key="k" role="radio" :aria-checked="kind === k" :class="{ on: kind === k }" @click="setKind(k)">
        {{ label }}
      </button>
    </div>

    <div v-if="kind === 'after'" class="line">
      <span>Every</span>
      <input v-model.number="n" class="field num" type="number" min="1" max="999" inputmode="numeric" aria-label="How many" @change="commit" />
      <select v-model="unit" class="field unit" aria-label="Unit" @change="commit">
        <option v-for="[u, w] in UNITS" :key="u" :value="u">{{ n === 1 ? w.replace(/s$/, '') : w }}</option>
      </select>
      <span>after it’s done</span>
    </div>

    <template v-else-if="kind === 'fixed'">
      <p v-if="custom" class="hint">Custom schedule <code>{{ custom }}</code>. Pick another option to replace it.</p>
      <template v-else>
        <div class="line">
          <span>Every</span>
          <input v-model.number="n" class="field num" type="number" min="1" max="999" inputmode="numeric" aria-label="How many" @change="commit" />
          <select v-model="unit" class="field unit" aria-label="Unit" @change="commit">
            <option v-for="[u, w] in UNITS" :key="u" :value="u">{{ n === 1 ? w.replace(/s$/, '') : w }}</option>
          </select>
        </div>
        <div v-if="unit === 'W'" class="days" role="group" aria-label="On days">
          <button v-for="[code, letter] in WEEK" :key="code" :class="{ on: byDay.includes(code) }"
                  :aria-pressed="byDay.includes(code)" :aria-label="WEEK_NAMES[code]" @click="toggleDay(code)">
            {{ letter }}
          </button>
        </div>
        <div v-if="unit === 'M'" class="line">
          <span>On day</span>
          <input v-model.number="monthDay" class="field num" type="number" min="1" max="31" inputmode="numeric"
                 placeholder="—" aria-label="Day of month" @change="commit" />
          <span class="hint">of the {{ unitWord }}</span>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
.repeat { display: grid; gap: 10px; }
.seg { display: flex; padding: 2px; border-radius: var(--radius-m); background: var(--ground); }
.seg button, .days button {
  flex: 1; height: 30px; padding: 0 8px; border: 0; border-radius: 6px; background: transparent; color: var(--muted);
  white-space: nowrap;
}
.seg button.on { background: var(--raised); color: var(--ink); box-shadow: 0 1px 2px rgb(0 0 0 / 0.08); }
.line { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.num { width: 64px; }
.unit { width: auto; padding-right: 6px; }
.days { display: flex; gap: 4px; }
.days button { flex: none; width: 34px; height: 34px; border-radius: 50%; background: var(--ground); }
.days button.on { background: var(--accent); color: var(--accent-ink); }
.hint { margin: 0; color: var(--muted); font-size: var(--step--1); }
code { font-size: var(--step--1); }
</style>
