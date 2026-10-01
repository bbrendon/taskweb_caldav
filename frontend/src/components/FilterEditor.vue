<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  defaultCondition, FIELD_DEFS, SMART_LABELS, type Condition, type ConditionField, type Filter, type View,
} from '@/lib/filters'
import { useTasks } from '@/stores/tasks'
import Icon from './Icon.vue'

const props = defineProps<{ view: View; dirty: boolean; count: number }>()
const filter = defineModel<Filter>({ required: true })
const emit = defineEmits<{ save: [name: string]; saveAsNew: [name: string]; remove: []; reset: []; close: [] }>()

const tasks = useTasks()
const isSaved = computed(() => !props.view.builtin)
const name = ref('')
watch(() => props.view.id, () => { name.value = isSaved.value ? props.view.name : '' }, { immediate: true })
const confirmingDelete = ref(false)

const defFor = (c: Condition) => FIELD_DEFS.find((d) => d.field === c.field)!
const opFor = (c: Condition) => defFor(c).ops.find((o) => o.op === c.op) ?? defFor(c).ops[0]

function edit(i: number, patch: Partial<Condition>) {
  const conditions = filter.value.conditions.map((c, j) => (j === i ? { ...c, ...patch } : c))
  filter.value = { ...filter.value, conditions }
}
function setField(i: number, field: ConditionField) {
  const conditions = [...filter.value.conditions]
  conditions[i] = defaultCondition(field)
  filter.value = { ...filter.value, conditions }
}
function setOp(i: number, op: string) {
  const c = filter.value.conditions[i]
  const next = defFor(c).ops.find((o) => o.op === op)!
  const keep = next.value === opFor(c).value
  edit(i, { op, value: keep ? c.value : defaultCondition(c.field).value })
}
function add() {
  filter.value = { ...filter.value, conditions: [...filter.value.conditions, defaultCondition('tag')] }
}
function remove(i: number) {
  filter.value = { ...filter.value, conditions: filter.value.conditions.filter((_, j) => j !== i) }
}

const PRIORITIES = [['high', 'High'], ['medium', 'Medium'], ['low', 'Low'], ['none', 'None']]
const places = computed(() => tasks.config?.places.map((p) => p.name) ?? [])
const canSave = computed(() => name.value.trim().length > 0)
</script>

<template>
  <section class="filters" aria-label="Filter">
    <div class="match">
      <span>Show tasks that match</span>
      <select :value="filter.match" class="field small" aria-label="Match"
              @change="filter = { ...filter, match: ($event.target as HTMLSelectElement).value as 'all' | 'any' }">
        <option value="all">all</option>
        <option value="any">any</option>
      </select>
      <span>of these</span>
      <button class="icon-btn close" aria-label="Close filter" @click="emit('close')"><Icon name="x" /></button>
    </div>

    <ul class="conds">
      <li v-for="(c, i) in filter.conditions" :key="i">
        <select class="field" :value="c.field" aria-label="Field" @change="setField(i, ($event.target as HTMLSelectElement).value as ConditionField)">
          <option v-for="d in FIELD_DEFS" :key="d.field" :value="d.field">{{ d.label }}</option>
        </select>
        <select class="field" :value="c.op" aria-label="Condition" @change="setOp(i, ($event.target as HTMLSelectElement).value)">
          <option v-for="o in defFor(c).ops" :key="o.op" :value="o.op">{{ o.label }}</option>
        </select>
        <template v-if="opFor(c).value === 'text'">
          <input class="field" :value="c.value ?? ''" placeholder="Words" aria-label="Text"
                 @input="edit(i, { value: ($event.target as HTMLInputElement).value })" />
        </template>
        <template v-else-if="opFor(c).value === 'number'">
          <input class="field num" type="number" min="0" inputmode="numeric" :value="c.value ?? 7" aria-label="Days"
                 @input="edit(i, { value: Number(($event.target as HTMLInputElement).value) })" />
        </template>
        <select v-else-if="opFor(c).value === 'tag'" class="field" :value="c.value ?? ''" aria-label="Tag"
                @change="edit(i, { value: ($event.target as HTMLSelectElement).value })">
          <option value="" disabled>Choose a tag</option>
          <option v-for="t in tasks.allTags" :key="t" :value="t">{{ t }}</option>
        </select>
        <select v-else-if="opFor(c).value === 'place'" class="field" :value="c.value ?? ''" aria-label="Place"
                @change="edit(i, { value: ($event.target as HTMLSelectElement).value })">
          <option value="" disabled>Choose a place</option>
          <option v-for="p in places" :key="p" :value="p">{{ p }}</option>
        </select>
        <select v-else-if="opFor(c).value === 'priority'" class="field" :value="c.value" aria-label="Priority"
                @change="edit(i, { value: ($event.target as HTMLSelectElement).value })">
          <option v-for="[v, l] in PRIORITIES" :key="v" :value="v">{{ l }}</option>
        </select>
        <select v-else-if="opFor(c).value === 'smart'" class="field" :value="c.value" aria-label="Status"
                @change="edit(i, { value: ($event.target as HTMLSelectElement).value })">
          <option v-for="(l, v) in SMART_LABELS" :key="v" :value="v">{{ l }}</option>
        </select>
        <span v-else class="spacer" />
        <button class="icon-btn" aria-label="Remove condition" @click="remove(i)"><Icon name="x" :size="15" /></button>
      </li>
    </ul>

    <div class="row">
      <button class="btn btn-ghost" @click="add"><Icon name="plus" :size="16" />Add condition</button>
      <label class="check"><input type="checkbox" aria-label="Include completed" :checked="filter.showCompleted" @change="filter = { ...filter, showCompleted: ($event.target as HTMLInputElement).checked }" /> Include completed</label>
      <label class="check"><input type="checkbox" aria-label="Include deferred" :checked="filter.showDeferred" @change="filter = { ...filter, showDeferred: ($event.target as HTMLInputElement).checked }" /> Include deferred</label>
    </div>

    <footer class="save">
      <span class="count">{{ count }} {{ count === 1 ? 'task' : 'tasks' }} match</span>
      <input v-model="name" class="field name" :placeholder="isSaved ? 'List name' : 'Name this search'" aria-label="Search name"
             @keydown.enter.prevent="canSave && (isSaved ? emit('save', name.trim()) : emit('saveAsNew', name.trim()))" />
      <template v-if="isSaved">
        <button class="btn btn-primary" :disabled="!canSave || (!dirty && name.trim() === view.name)" @click="emit('save', name.trim())">Save</button>
        <button class="btn" :disabled="!canSave || name.trim() === view.name" @click="emit('saveAsNew', name.trim())">Save as new</button>
      </template>
      <button v-else class="btn btn-primary" :disabled="!canSave" @click="emit('saveAsNew', name.trim())">Save search</button>
      <button v-if="dirty" class="btn btn-ghost" @click="emit('reset')">Undo changes</button>
      <template v-if="isSaved">
        <button v-if="!confirmingDelete" class="btn btn-ghost btn-danger" @click="confirmingDelete = true">Delete search</button>
        <span v-else class="confirm">
          Delete “{{ view.name }}”? Tasks aren’t affected.
          <button class="btn btn-danger" @click="emit('remove')">Delete</button>
          <button class="btn btn-ghost" @click="confirmingDelete = false">Cancel</button>
        </span>
      </template>
    </footer>
  </section>
</template>

<style scoped>
.filters {
  display: grid;
  gap: 10px;
  padding: 12px 16px 14px;
  border-bottom: 1px solid var(--line);
  background: var(--ground);
}
.match { display: flex; align-items: center; gap: 8px; color: var(--muted); }
.match .close { margin-left: auto; }
.small { width: auto; height: 30px; }
.conds { display: grid; gap: 6px; margin: 0; padding: 0; list-style: none; }
.conds li { display: grid; grid-template-columns: 130px 210px minmax(120px, 220px) 32px; gap: 6px; align-items: center; }
.num { width: 90px; }
.spacer { display: block; }
.row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 16px; }
.check { display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }
.save { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding-top: 10px; border-top: 1px solid var(--line); }
.count { color: var(--muted); margin-right: 4px; }
.name { width: 220px; }
.confirm { display: inline-flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.btn:disabled { opacity: 0.5; cursor: default; }

@media (max-width: 759px) {
  .conds li { grid-template-columns: 1fr 1fr 32px; }
  .conds li > :nth-child(3) { grid-column: 1 / 3; }
  .conds li > :nth-child(4) { grid-row: 1; grid-column: 3; }
  .field { height: 40px; }
  .name { flex: 1 1 100%; width: auto; }
}
</style>
