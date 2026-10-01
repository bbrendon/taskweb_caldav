<script setup lang="ts">
import { PopoverContent, PopoverPortal, PopoverRoot, PopoverTrigger } from 'reka-ui'
import { computed } from 'vue'
import { COLUMNS, DEFAULT_COLUMNS } from '@/lib/columns'
import Icon from './Icon.vue'

const props = defineProps<{ columns: string[] }>()
const emit = defineEmits<{ change: [cols: string[]] }>()

// Visible columns first (in display order), then the hidden ones.
const ordered = computed(() => [
  ...props.columns.map((id) => COLUMNS.find((c) => c.id === id)!).filter(Boolean),
  ...COLUMNS.filter((c) => !props.columns.includes(c.id)),
])

function toggle(id: string) {
  emit('change', props.columns.includes(id) ? props.columns.filter((c) => c !== id) : [...props.columns, id])
}

function move(id: string, by: number) {
  const cols = [...props.columns]
  const i = cols.indexOf(id)
  const j = i + by
  if (i < 0 || j < 1 || j >= cols.length) return // title stays first
  ;[cols[i], cols[j]] = [cols[j], cols[i]]
  emit('change', cols)
}
</script>

<template>
  <PopoverRoot>
    <PopoverTrigger class="icon-btn" aria-label="Choose columns" title="Columns">
      <Icon name="columns" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent class="col-menu" align="end" :side-offset="6">
        <p class="head">Columns</p>
        <ul>
          <li v-for="c in ordered" :key="c.id">
            <label>
              <input type="checkbox" :checked="columns.includes(c.id)" :disabled="c.id === 'title'" @change="toggle(c.id)" />
              {{ c.label }}
            </label>
            <span v-if="columns.includes(c.id) && c.id !== 'title'" class="moves">
              <button class="icon-btn" :aria-label="`Move ${c.label} left`" @click="move(c.id, -1)">
                <Icon name="chevron" :size="14" style="transform: rotate(-90deg)" />
              </button>
              <button class="icon-btn" :aria-label="`Move ${c.label} right`" @click="move(c.id, 1)">
                <Icon name="chevron" :size="14" style="transform: rotate(90deg)" />
              </button>
            </span>
          </li>
        </ul>
        <button class="btn btn-ghost reset" @click="emit('change', [...DEFAULT_COLUMNS])">Reset to default</button>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<style>
.col-menu {
  z-index: 50;
  width: 250px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: var(--radius-m);
  background: var(--raised);
  box-shadow: var(--shadow-panel);
}
.col-menu .head { margin: 2px 6px 6px; font-weight: 700; }
.col-menu ul { list-style: none; margin: 0; padding: 0; }
.col-menu li { display: flex; align-items: center; justify-content: space-between; min-height: 32px; padding: 0 6px; border-radius: var(--radius-s); }
.col-menu li:hover { background: var(--ground); }
.col-menu label { display: flex; align-items: center; gap: 8px; flex: 1; }
.col-menu .moves { display: flex; }
.col-menu .moves .icon-btn { width: 26px; height: 26px; }
.col-menu .reset { width: 100%; margin-top: 6px; justify-content: center; }
</style>
