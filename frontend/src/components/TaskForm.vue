<template>
  <div class="task-form-panel">
    <div class="form-header">
      <!-- Mobile back button -->
      <button class="back-btn" @click="ui.closeForm()">
        <n-icon :component="ArrowBackOutline" size="18" />
        Back
      </button>
      <span class="form-title">{{ isEditing ? 'Edit Task' : 'New Task' }}</span>
      <n-button text size="small" @click="ui.closeForm()" class="desktop-close">
        <template #icon><n-icon :component="CloseOutline" /></template>
      </n-button>
    </div>

    <n-scrollbar style="flex: 1">
      <div class="form-body">
        <!-- Title -->
        <div class="form-field">
          <label>Title <span class="required">*</span></label>
          <n-input
            v-model:value="form.title"
            placeholder="Task title"
            size="medium"
            autofocus
            @keydown.enter.ctrl="submit"
          />
        </div>

        <!-- Description -->
        <div class="form-field">
          <label>Notes</label>
          <n-input
            v-model:value="form.description"
            type="textarea"
            placeholder="Add notes..."
            :rows="3"
          />
        </div>

        <!-- Status + Priority row -->
        <div class="form-row">
          <div class="form-field">
            <label>Status</label>
            <n-select v-model:value="form.status" :options="statusOptions" size="small" />
          </div>
          <div class="form-field">
            <label>Priority</label>
            <n-select v-model:value="form.priority" :options="priorityOptions" size="small" />
          </div>
        </div>

        <!-- Due + Start dates -->
        <div class="form-row">
          <div class="form-field">
            <label>Due Date</label>
            <n-date-picker
              v-model:value="dueTimestamp"
              type="datetime"
              size="small"
              clearable
              style="width: 100%"
              @update:value="(v) => form.due = v ? new Date(v).toISOString() : null"
            />
          </div>
          <div class="form-field">
            <label>Start Date</label>
            <n-date-picker
              v-model:value="startTimestamp"
              type="datetime"
              size="small"
              clearable
              style="width: 100%"
              @update:value="(v) => form.start = v ? new Date(v).toISOString() : null"
            />
          </div>
        </div>

        <!-- Tags -->
        <div class="form-field">
          <label>Tags</label>
          <n-dynamic-tags v-model:value="form.tags" :max="20" />
        </div>

        <!-- Location -->
        <div class="form-field">
          <label>Location</label>
          <n-auto-complete
            v-model:value="form.location"
            :options="locationOptions"
            placeholder="arriving:home, departing:work..."
            clearable
            size="small"
          />
        </div>

        <!-- Parent task -->
        <div class="form-field">
          <label>Parent Task</label>
          <n-select
            v-model:value="form.parent_uid"
            :options="parentOptions"
            placeholder="Search for a parent task..."
            size="small"
            clearable
            filterable
          />
        </div>

        <!-- Starred -->
        <div class="form-field-inline">
          <label>Starred</label>
          <n-switch v-model:value="form.starred" />
        </div>

        <!-- Recurrence -->
        <div class="form-field">
          <label>Recurrence</label>
          <RecurrenceField v-model="form.recurrence" />
        </div>

        <!-- Percent -->
        <div class="form-field">
          <label>Progress: {{ form.percent }}%</label>
          <n-slider v-model:value="form.percent" :min="0" :max="100" :step="5" />
        </div>
      </div>
    </n-scrollbar>

    <!-- Footer -->
    <div class="form-footer">
      <div v-if="errors.length" class="form-errors">
        <span v-for="e in errors" :key="e">{{ e }}</span>
      </div>
      <div class="form-buttons">
        <n-button @click="ui.closeForm()">Cancel</n-button>
        <n-button type="primary" :loading="saving" @click="submit">
          {{ isEditing ? 'Save' : 'Create' }}
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { CloseOutline, ArrowBackOutline } from '@vicons/ionicons5'
import { useTasksStore } from '@/stores/tasks.js'
import { useUiStore } from '@/stores/ui.js'
import RecurrenceField from './RecurrenceField.vue'

const route = useRoute()
const tasksStore = useTasksStore()
const ui = useUiStore()

// Exclude the task being edited from the parent list (can't be its own parent)
const parentOptions = computed(() =>
  tasksStore.tasks
    .filter(t => t.uid !== ui.editingTask?.uid && t.status !== 'COMPLETED')
    .map(t => ({ label: t.title, value: t.uid }))
)
const saving = ref(false)
const errors = ref([])

const statusOptions = [
  { label: 'Needs Action', value: 'NEEDS-ACTION' },
  { label: 'In Process', value: 'IN-PROCESS' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Cancelled', value: 'CANCELLED' },
]

const priorityOptions = [
  { label: 'None', value: 0 },
  { label: 'High (1)', value: 1 },
  { label: 'High (2)', value: 2 },
  { label: 'High (3)', value: 3 },
  { label: 'High (4)', value: 4 },
  { label: 'Medium (5)', value: 5 },
  { label: 'Low (6)', value: 6 },
  { label: 'Low (7)', value: 7 },
  { label: 'Low (8)', value: 8 },
  { label: 'Low (9)', value: 9 },
]

const locationOptions = [
  'arriving:home', 'departing:home',
  'arriving:work', 'departing:work',
  'arriving:car', 'departing:car',
].map(l => ({ label: l, value: l }))

const isEditing = computed(() => !!(ui.editingTask?.uid))

// Form state
const form = ref({
  title: '',
  description: '',
  status: 'NEEDS-ACTION',
  priority: 0,
  due: null,
  start: null,
  tags: [],
  location: '',
  parent_uid: null,
  starred: false,
  recurrence: '',
  percent: 0,
})

function parseDateLocal(str) {
  if (!str) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
    const [y, m, d] = str.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(str)
}

// For date pickers (timestamp in ms)
const dueTimestamp = ref(null)
const startTimestamp = ref(null)

onMounted(() => {
  if (ui.editingTask) {
    const t = ui.editingTask
    form.value = {
      title: t.title || '',
      description: t.description || '',
      status: t.status || 'NEEDS-ACTION',
      priority: t.priority ?? 0,
      due: t.due || null,
      start: t.start || null,
      tags: [...(t.tags || [])],
      location: t.location || '',
      parent_uid: t.parent_uid || null,
      starred: t.starred || false,
      recurrence: t.recurrence || '',
      percent: t.percent || 0,
    }
    if (t.due) dueTimestamp.value = parseDateLocal(t.due).getTime()
    if (t.start) startTimestamp.value = parseDateLocal(t.start).getTime()
  }
})

async function submit() {
  errors.value = []
  if (!form.value.title.trim()) {
    errors.value = ['Title is required']
    return
  }
  if (form.value.recurrence && !form.value.due) {
    errors.value = ['Recurring tasks must have a due date']
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value }
    // Clean empty strings
    if (!payload.location) delete payload.location
    if (!payload.recurrence) delete payload.recurrence
    if (!payload.parent_uid) delete payload.parent_uid
    if (!payload.description) delete payload.description

    if (isEditing.value) {
      await tasksStore.updateTask(ui.editingTask.uid, payload)
    } else {
      const created = await tasksStore.createTask(payload)
      ui.openTask(created.uid)
      // Re-fetch full list so server-computed virtual tags (e.g. PARENT) are correct
      tasksStore.fetchTasks(route.query)
    }
    ui.closeForm()
    // Refresh tags sidebar
    tasksStore.fetchTags()
  } catch (e) {
    errors.value = [e.message || 'Failed to save task']
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.task-form-panel {
  width: 400px;
  flex-shrink: 0;
  background: #0d0f14;
  border-left: 1px solid #1e2130;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #1e2130;
}

.form-title {
  font-size: 14px;
  font-weight: 600;
  color: #e5e7eb;
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
}

@media (max-width: 768px) {
  .task-form-panel {
    position: fixed;
    inset: 0;
    width: 100%;
    z-index: 50;
    border-left: none;
  }

  .form-header {
    padding-top: calc(12px + env(safe-area-inset-top));
  }

  .back-btn {
    display: flex;
  }

  .desktop-close {
    display: none;
  }

  .form-title {
    margin-right: auto;
    margin-left: 12px;
  }

  /* Larger inputs on mobile */
  .form-row {
    grid-template-columns: 1fr;
  }
}

.form-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-field label {
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
}

.required { color: #f87171; }

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.form-field-inline label {
  font-size: 12px;
  font-weight: 500;
  color: #9ca3af;
}

.form-footer {
  padding: 12px 16px;
  border-top: 1px solid #1e2130;
}

.form-errors {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-errors span {
  font-size: 12px;
  color: #f87171;
}

.form-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
