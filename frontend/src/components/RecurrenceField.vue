<template>
  <div class="recurrence-field">
    <div class="recur-row">
      <label class="recur-label">Repeats</label>
      <n-select
        v-model:value="frequency"
        :options="freqOptions"
        size="small"
        style="width: 130px"
        @update:value="emitRrule"
      />
    </div>

    <template v-if="frequency !== 'none'">
      <div class="recur-row">
        <label class="recur-label">Every</label>
        <n-input-number
          v-model:value="interval"
          :min="1"
          :max="365"
          size="small"
          style="width: 80px"
          @update:value="emitRrule"
        />
        <span class="recur-unit">{{ freqUnit }}</span>
      </div>

      <div class="recur-row" v-if="frequency === 'WEEKLY'">
        <label class="recur-label">On</label>
        <div class="day-picker">
          <button
            v-for="d in days"
            :key="d.value"
            class="day-btn"
            :class="{ active: byDay.includes(d.value) }"
            @click="toggleDay(d.value)"
            type="button"
          >{{ d.short }}</button>
        </div>
      </div>

      <div class="recur-row">
        <label class="recur-label">Ends</label>
        <n-select
          v-model:value="endType"
          :options="endOptions"
          size="small"
          style="width: 120px"
          @update:value="emitRrule"
        />
        <n-input-number
          v-if="endType === 'count'"
          v-model:value="count"
          :min="1"
          :max="999"
          size="small"
          style="width: 70px"
          placeholder="times"
          @update:value="emitRrule"
        />
        <n-date-picker
          v-if="endType === 'until'"
          v-model:value="until"
          type="date"
          size="small"
          @update:value="emitRrule"
        />
      </div>

      <div class="rrule-preview" v-if="rruleStr">
        <code>{{ rruleStr }}</code>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const freqOptions = [
  { label: 'Never', value: 'none' },
  { label: 'Daily', value: 'DAILY' },
  { label: 'Weekly', value: 'WEEKLY' },
  { label: 'Monthly', value: 'MONTHLY' },
  { label: 'Yearly', value: 'YEARLY' },
]

const endOptions = [
  { label: 'Never', value: 'never' },
  { label: 'After N times', value: 'count' },
  { label: 'On date', value: 'until' },
]

const days = [
  { short: 'M', value: 'MO' },
  { short: 'T', value: 'TU' },
  { short: 'W', value: 'WE' },
  { short: 'T', value: 'TH' },
  { short: 'F', value: 'FR' },
  { short: 'S', value: 'SA' },
  { short: 'S', value: 'SU' },
]

const frequency = ref('none')
const interval = ref(1)
const byDay = ref([])
const endType = ref('never')
const count = ref(10)
const until = ref(null) // timestamp

const freqUnit = computed(() => {
  const map = { DAILY: 'day(s)', WEEKLY: 'week(s)', MONTHLY: 'month(s)', YEARLY: 'year(s)' }
  return map[frequency.value] || ''
})

const rruleStr = computed(() => {
  if (frequency.value === 'none') return ''
  let rule = `FREQ=${frequency.value}`
  if (interval.value > 1) rule += `;INTERVAL=${interval.value}`
  if (frequency.value === 'WEEKLY' && byDay.value.length) {
    rule += `;BYDAY=${byDay.value.join(',')}`
  }
  if (endType.value === 'count' && count.value) {
    rule += `;COUNT=${count.value}`
  } else if (endType.value === 'until' && until.value) {
    const d = new Date(until.value)
    const iso = d.toISOString().replace(/[-:]/g, '').slice(0, 15) + 'Z'
    rule += `;UNTIL=${iso}`
  }
  return rule
})

function emitRrule() {
  emit('update:modelValue', frequency.value === 'none' ? '' : rruleStr.value)
}

function toggleDay(day) {
  const idx = byDay.value.indexOf(day)
  if (idx === -1) byDay.value.push(day)
  else byDay.value.splice(idx, 1)
  emitRrule()
}

// Parse incoming rrule string
watch(() => props.modelValue, (val) => {
  if (!val) { frequency.value = 'none'; return }
  const freq = val.match(/FREQ=(\w+)/)?.[1]
  if (freq) frequency.value = freq
  const iv = val.match(/INTERVAL=(\d+)/)?.[1]
  if (iv) interval.value = parseInt(iv)
  const bd = val.match(/BYDAY=([\w,]+)/)?.[1]
  if (bd) byDay.value = bd.split(',')
  const c = val.match(/COUNT=(\d+)/)?.[1]
  if (c) { endType.value = 'count'; count.value = parseInt(c) }
  const u = val.match(/UNTIL=(\w+)/)?.[1]
  if (u) { endType.value = 'until' }
}, { immediate: true })
</script>

<style scoped>
.recurrence-field {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.recur-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.recur-label {
  font-size: 12px;
  color: #9ca3af;
  width: 50px;
  flex-shrink: 0;
}

.recur-unit {
  font-size: 12px;
  color: #6b7280;
}

.day-picker {
  display: flex;
  gap: 4px;
}

.day-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid #374151;
  background: transparent;
  color: #9ca3af;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.1s, border-color 0.1s;
}

.day-btn:hover { border-color: #5c8df6; color: #e5e7eb; }
.day-btn.active { background: #5c8df6; border-color: #5c8df6; color: #fff; }

.rrule-preview {
  padding: 6px 10px;
  background: #1a1d27;
  border-radius: 6px;
}

.rrule-preview code {
  font-size: 11px;
  color: #6ee7b7;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
</style>
