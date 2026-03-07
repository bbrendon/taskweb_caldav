<template>
  <div
    class="task-row"
    :class="{
      active: ui.activeTaskUid === task.uid,
      completed: task.status === 'COMPLETED',
      overdue: isOverdue,
      subtask: isSubtask,
    }"
    @click="$emit('click')"
  >
    <!-- Checkbox -->
    <button
      class="checkbox"
      :class="{ checked: task.status === 'COMPLETED' }"
      @click.stop="$emit('complete')"
      :title="task.status === 'COMPLETED' ? 'Mark incomplete' : 'Complete'"
    >
      <n-icon v-if="task.status === 'COMPLETED'" :component="CheckmarkOutline" size="12" />
    </button>

    <!-- Expand toggle (if PARENT virtual tag) -->
    <button
      v-if="isParent"
      class="expand-btn"
      @click.stop="$emit('expand')"
      :title="expanded ? 'Collapse subtasks' : 'Expand subtasks'"
    >
      <n-icon :component="expanded ? ChevronDownOutline : ChevronForwardOutline" size="12" />
    </button>

    <!-- Title + metadata -->
    <div class="task-info">
      <div class="task-title">{{ task.title }}</div>
      <div class="task-meta">
        <!-- Due date -->
        <span v-if="task.due" class="meta-chip due" :class="dueClass">
          <n-icon :component="CalendarOutline" size="11" />
          {{ formatDue(task.due) }}
        </span>
        <!-- Priority -->
        <span v-if="priorityLabel" class="meta-chip priority" :class="priorityClass">
          {{ priorityLabel }}
        </span>
        <!-- Tags -->
        <span v-for="tag in (task.tags || []).slice(0, 3)" :key="tag" class="meta-chip tag">
          {{ tag }}
        </span>
        <!-- Recurrence indicator -->
        <span v-if="task.recurrence" class="meta-chip recur" title="Recurring">
          <n-icon :component="RepeatOutline" size="11" />
        </span>
        <!-- Location -->
        <span v-if="task.location" class="meta-chip location" :title="task.location">
          <n-icon :component="LocationOutline" size="11" />
        </span>
      </div>
    </div>

    <!-- Star -->
    <button
      class="star-btn"
      :class="{ starred: task.starred }"
      @click.stop="$emit('star')"
      :title="task.starred ? 'Unstar' : 'Star'"
    >
      <n-icon :component="task.starred ? Star : StarOutline" size="14" />
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  CheckmarkOutline, CalendarOutline, RepeatOutline,
  StarOutline, Star, ChevronForwardOutline, ChevronDownOutline,
  LocationOutline,
} from '@vicons/ionicons5'
import { useUiStore } from '@/stores/ui.js'

const props = defineProps({
  task: { type: Object, required: true },
  isSubtask: { type: Boolean, default: false },
  expanded: { type: Boolean, default: false },
})

defineEmits(['click', 'complete', 'star', 'expand'])

const ui = useUiStore()

const isParent = computed(() => (props.task.virtual_tags || []).includes('PARENT'))
const isOverdue = computed(() => (props.task.virtual_tags || []).includes('OVERDUE'))

const priorityLabel = computed(() => {
  const p = props.task.priority || 0
  if (p >= 1 && p <= 4) return 'High'
  if (p === 5) return 'Med'
  if (p >= 6 && p <= 9) return 'Low'
  return null
})

const priorityClass = computed(() => {
  const p = props.task.priority || 0
  if (p >= 1 && p <= 4) return 'high'
  if (p === 5) return 'medium'
  if (p >= 6 && p <= 9) return 'low'
  return ''
})

const dueClass = computed(() => {
  if (isOverdue.value) return 'overdue'
  const vt = props.task.virtual_tags || []
  if (vt.includes('DUE_TODAY')) return 'today'
  if (vt.includes('DUE_WEEK')) return 'week'
  return ''
})

function parseDate(str) {
  if (!str) return null
  // Date-only ISO strings (YYYY-MM-DD) must be parsed as local midnight,
  // otherwise JS treats them as UTC midnight which shifts to the previous day in US timezones.
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [y, m, d] = str.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(str)
}

function formatDue(due) {
  if (!due) return ''
  const d = parseDate(due)
  const now = new Date()
  // Strip time to compare calendar days
  const dDay = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((dDay - today) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays === -1) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.task-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-bottom: 1px solid #1a1d27;
  cursor: pointer;
  transition: background 0.1s;
  min-height: 48px;
}

.task-row:hover { background: #15181f; }
.task-row.active { background: #1a1f2e; }
.task-row.subtask { padding-left: 40px; background: #0e1016; }
.task-row.subtask:hover { background: #13161d; }
.task-row.completed .task-title { text-decoration: line-through; color: #4b5563; }
.task-row.completed .checkbox { border-color: #374151; background: #1f2937; }

.checkbox {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid #374151;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #10b981;
  transition: border-color 0.15s, background 0.15s;
}

.checkbox:hover { border-color: #10b981; }
.checkbox.checked { background: #10b981; border-color: #10b981; color: #fff; }

.expand-btn {
  background: none;
  border: none;
  color: #4b5563;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.expand-btn:hover { color: #9ca3af; }

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 13px;
  color: #e5e7eb;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 3px;
}

.task-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 500;
}

.meta-chip.due { background: #1a2335; color: #93c5fd; }
.meta-chip.due.overdue { background: #2a1818; color: #f87171; }
.meta-chip.due.today { background: #1f2a1a; color: #6ee7b7; }
.meta-chip.due.week { background: #1e2330; color: #818cf8; }

.meta-chip.priority { font-size: 10px; }
.meta-chip.priority.high { background: #2a1818; color: #f87171; }
.meta-chip.priority.medium { background: #2a2218; color: #fbbf24; }
.meta-chip.priority.low { background: #1e2130; color: #9ca3af; }

.meta-chip.tag { background: #1e2130; color: #93c5fd; }
.meta-chip.recur { background: transparent; color: #6b7280; padding: 0; }
.meta-chip.location { background: transparent; color: #6b7280; padding: 0; }

.star-btn {
  background: none;
  border: none;
  color: #374151;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  transition: color 0.15s;
}

.star-btn:hover { color: #fbbf24; }
.star-btn.starred { color: #fbbf24; }

@media (max-width: 768px) {
  .task-row {
    min-height: 60px;
    padding: 12px 16px;
  }

  .task-row.subtask {
    padding-left: 36px;
  }

  .checkbox {
    width: 24px;
    height: 24px;
    min-width: 24px;
  }

  .task-title {
    font-size: 15px;
    margin-bottom: 4px;
  }

  .meta-chip {
    font-size: 12px;
    padding: 2px 7px;
  }

  /* Always show star on touch — no hover needed */
  .star-btn {
    color: #4b5563;
    padding: 8px;
    margin: -8px -8px -8px 0;
  }

  .star-btn.starred {
    color: #fbbf24;
  }
}
</style>
