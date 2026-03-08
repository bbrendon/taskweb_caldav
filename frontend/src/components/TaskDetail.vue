<template>
  <div class="task-detail" v-if="task">
    <!-- Header -->
    <div class="detail-header">
      <!-- Mobile back button -->
      <button class="back-btn" @click="ui.closeTask()">
        <n-icon :component="ArrowBackOutline" size="18" />
        Back
      </button>
      <div class="detail-actions">
        <n-button text size="medium" @click="ui.closeTask()" class="desktop-close">
          <template #icon><n-icon :component="CloseOutline" size="20" /></template>
        </n-button>
        <n-button text size="medium" @click="ui.openEditForm(task)" title="Edit">
          <template #icon><n-icon :component="CreateOutline" size="20" /></template>
        </n-button>
        <n-button text size="medium" @click="completeTask" :disabled="task.status === 'COMPLETED'" title="Complete">
          <template #icon><n-icon :component="CheckmarkCircleOutline" size="20" /></template>
        </n-button>
        <n-button text size="medium" @click="addSubtask" title="Add subtask">
          <template #icon><n-icon :component="AddCircleOutline" size="20" /></template>
        </n-button>
        <n-popconfirm @positive-click="deleteTask">
          <template #trigger>
            <n-button text size="medium" title="Delete">
              <template #icon><n-icon :component="TrashOutline" size="20" color="#f87171" /></template>
            </n-button>
          </template>
          Delete this task?
        </n-popconfirm>
      </div>
    </div>

    <!-- Title -->
    <div class="detail-title">{{ task.title }}</div>

    <!-- Virtual tag badges -->
    <div class="virtual-tags" v-if="task.virtual_tags?.length">
      <span v-for="vt in task.virtual_tags" :key="vt" class="vtag" :class="vt.toLowerCase()">
        {{ vt.replace('_', ' ') }}
      </span>
    </div>

    <!-- Metadata grid -->
    <div class="detail-grid">
      <template v-if="task.status">
        <span class="meta-label">Status</span>
        <span class="status-badge" :class="task.status.toLowerCase().replace('-', '')">
          {{ task.status }}
        </span>
      </template>

      <template v-if="task.priority">
        <span class="meta-label">Priority</span>
        <span>{{ priorityLabel }}</span>
      </template>

      <template v-if="task.due">
        <span class="meta-label">Due</span>
        <span :class="{ overdue: isOverdue, due_today: isDueToday }">
          {{ formatDate(task.due) }}
        </span>
      </template>

      <template v-if="task.start">
        <span class="meta-label">Start</span>
        <span>{{ formatDate(task.start) }}</span>
      </template>

      <template v-if="task.tags?.length">
        <span class="meta-label">Tags</span>
        <div class="tag-list">
          <span v-for="tag in task.tags" :key="tag" class="tag-badge">{{ tag }}</span>
        </div>
      </template>

      <template v-if="task.location">
        <span class="meta-label">Location</span>
        <span class="location-val">
          <n-icon :component="LocationOutline" size="13" />
          {{ task.location }}
        </span>
      </template>

      <template v-if="task.recurrence">
        <span class="meta-label">Recurs</span>
        <span class="recur-val">
          <n-icon :component="RepeatOutline" size="13" />
          {{ formatRecurrence(task.recurrence) }}
        </span>
      </template>

      <template v-if="task.percent > 0">
        <span class="meta-label">Progress</span>
        <div style="flex: 1">
          <n-progress type="line" :percentage="task.percent" :height="6" :border-radius="3" />
        </div>
      </template>

      <template v-if="task.completed_at">
        <span class="meta-label">Completed</span>
        <span>{{ formatDate(task.completed_at) }}</span>
      </template>

      <template v-if="task.parent_uid">
        <span class="meta-label">Parent</span>
        <span class="parent-link" @click="openParent">{{ task.parent_uid.slice(0, 8) }}…</span>
      </template>
    </div>

    <!-- Description -->
    <div v-if="task.description" class="detail-description">
      <div class="section-label">Notes</div>
      <pre class="description-text">{{ task.description }}</pre>
    </div>

    <!-- Subtasks -->
    <div class="subtasks-section">
      <div class="section-label">
        Subtasks
        <n-button text size="tiny" @click="addSubtask">
          <template #icon><n-icon :component="AddOutline" /></template>
        </n-button>
      </div>
      <div v-if="loadingSubtasks" style="padding: 8px; color: #6b7280; font-size: 12px">Loading...</div>
      <div v-else-if="!subtasks.length" style="padding: 4px 0; color: #4b5563; font-size: 12px">
        No subtasks
      </div>
      <div v-else class="subtask-list">
        <div
          v-for="sub in subtasks"
          :key="sub.uid"
          class="subtask-item"
          @click="ui.openTask(sub.uid)"
        >
          <span class="subtask-check" :class="{ done: sub.status === 'COMPLETED' }">
            <n-icon v-if="sub.status === 'COMPLETED'" :component="CheckmarkOutline" size="10" />
          </span>
          <span :class="{ 'line-through': sub.status === 'COMPLETED' }">{{ sub.title }}</span>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="detail-empty">
    <n-icon :component="DocumentTextOutline" size="40" color="#374151" />
    <span>Select a task to view details</span>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import {
  CloseOutline, CreateOutline, CheckmarkCircleOutline, TrashOutline,
  AddCircleOutline, AddOutline, LocationOutline, RepeatOutline,
  CheckmarkOutline, DocumentTextOutline, ArrowBackOutline,
} from '@vicons/ionicons5'
import { useTasksStore } from '@/stores/tasks.js'
import { useUiStore } from '@/stores/ui.js'
import { tasksApi } from '@/api/tasks.js'

const tasksStore = useTasksStore()
const ui = useUiStore()

const subtasks = ref([])
const loadingSubtasks = ref(false)
const fetchedTask = ref(null)

const task = computed(() => {
  if (!ui.activeTaskUid) return null
  return tasksStore.getTask(ui.activeTaskUid) || fetchedTask.value
})

watch(() => ui.activeTaskUid, async (uid) => {
  fetchedTask.value = null
  if (uid && !tasksStore.getTask(uid)) {
    try {
      const res = await tasksApi.get(uid)
      if (ui.activeTaskUid === uid) fetchedTask.value = res.data
    } catch {}
  }
})

const isOverdue = computed(() => (task.value?.virtual_tags || []).includes('OVERDUE'))
const isDueToday = computed(() => (task.value?.virtual_tags || []).includes('DUE_TODAY'))

const priorityLabel = computed(() => {
  const p = task.value?.priority || 0
  if (p >= 1 && p <= 4) return `High (${p})`
  if (p === 5) return 'Medium'
  if (p >= 6 && p <= 9) return `Low (${p})`
  return 'None'
})

function parseDate(str) {
  if (!str) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [y, m, d] = str.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(str)
}

function formatDate(iso) {
  if (!iso) return ''
  const d = parseDate(iso)
  const opts = { month: 'short', day: 'numeric', year: 'numeric' }
  // Only show time if the original value had a time component
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    opts.hour = 'numeric'
    opts.minute = '2-digit'
  }
  return d.toLocaleString('en-US', opts)
}

function formatRecurrence(rrule) {
  if (!rrule) return ''
  // Parse basic RRULE for human display
  const freq = rrule.match(/FREQ=(\w+)/)?.[1]?.toLowerCase()
  const interval = rrule.match(/INTERVAL=(\d+)/)?.[1]
  if (!freq) return rrule
  if (interval && parseInt(interval) > 1) return `Every ${interval} ${freq}s`
  return `Every ${freq}`
}

async function loadSubtasks() {
  if (!task.value?.uid) return
  loadingSubtasks.value = true
  try {
    const res = await tasksApi.list({ parent_uid: task.value.uid })
    subtasks.value = res.data.tasks || []
  } catch {
    subtasks.value = []
  } finally {
    loadingSubtasks.value = false
  }
}

async function completeTask() {
  if (!task.value) return
  await tasksStore.completeTask(task.value.uid)
}

async function deleteTask() {
  if (!task.value) return
  await tasksStore.deleteTask(task.value.uid)
  ui.closeTask()
}

function addSubtask() {
  if (!task.value) return
  ui.openCreateForm(task.value)
}

function openParent() {
  if (task.value?.parent_uid) ui.openTask(task.value.parent_uid)
}

watch(() => ui.activeTaskUid, () => {
  subtasks.value = []
  loadSubtasks()
}, { immediate: true })
</script>

<style scoped>
.task-detail {
  width: 360px;
  flex-shrink: 0;
  background: #0d0f14;
  border-left: 1px solid #1e2130;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.detail-empty {
  width: 360px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #4b5563;
  font-size: 14px;
  border-left: 1px solid #1e2130;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 12px;
  border-bottom: 1px solid #1e2130;
}

.detail-actions {
  display: flex;
  gap: 4px;
}

/* Back button — mobile only */
.back-btn {
  display: none;
  align-items: center;
  gap: 6px;
  background: none;
  border: none;
  color: #5c8df6;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  padding: 4px 0;
  margin-right: auto;
}

@media (max-width: 768px) {
  .task-detail {
    position: fixed;
    inset: 0;
    width: 100%;
    z-index: 50;
    border-left: none;
  }

  /* Hide the detail-empty on mobile — there's nothing to show */
  .detail-empty {
    display: none;
  }

  .back-btn {
    display: flex;
  }

  .desktop-close {
    display: none;
  }

  .detail-header {
    justify-content: space-between;
    padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
  }

  .subtask-item {
    min-height: 44px;
  }
}

.detail-title {
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #e5e7eb;
  line-height: 1.4;
  border-bottom: 1px solid #1e2130;
}

.virtual-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid #1e2130;
}

.vtag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  background: #1e2130;
  color: #6b7280;
}

.vtag.overdue { background: #2a1818; color: #f87171; }
.vtag.due_today { background: #1f2a1a; color: #6ee7b7; }
.vtag.due_week { background: #1e2330; color: #818cf8; }
.vtag.starred { background: #2a2518; color: #fbbf24; }
.vtag.high { background: #2a1818; color: #f87171; }
.vtag.medium { background: #2a2218; color: #fbbf24; }
.vtag.recurring { background: #1e2830; color: #38bdf8; }
.vtag.parent { background: #1e2130; color: #a78bfa; }

.detail-grid {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 8px 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #1e2130;
  align-items: start;
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding-top: 1px;
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: #1e2130;
  color: #9ca3af;
  display: inline-block;
}

.status-badge.completed { background: #1f2a1a; color: #6ee7b7; }
.status-badge.needsaction { background: #1e2330; color: #818cf8; }
.status-badge.inprocess { background: #1e2a35; color: #38bdf8; }
.status-badge.cancelled { background: #2a1818; color: #f87171; }

.overdue { color: #f87171; }
.due_today { color: #6ee7b7; }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.tag-badge {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 10px;
  background: #1e2130;
  color: #93c5fd;
}

.location-val, .recur-val {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #9ca3af;
}

.parent-link {
  color: #818cf8;
  cursor: pointer;
  font-family: monospace;
  font-size: 12px;
}

.parent-link:hover { text-decoration: underline; }

.detail-description {
  padding: 14px 16px;
  border-bottom: 1px solid #1e2130;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6b7280;
  margin-bottom: 8px;
}

.description-text {
  font-size: 13px;
  color: #9ca3af;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  margin: 0;
  line-height: 1.6;
}

.subtasks-section {
  padding: 14px 16px;
  flex: 1;
}

.subtask-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.subtask-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #9ca3af;
  transition: background 0.1s;
}

.subtask-item:hover { background: #1a1d27; color: #e5e7eb; }

.subtask-check {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1.5px solid #374151;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.subtask-check.done { background: #10b981; border-color: #10b981; color: #fff; }

.line-through { text-decoration: line-through; color: #4b5563; }
</style>
