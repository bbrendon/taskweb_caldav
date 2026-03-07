<template>
  <div class="task-list-container">
    <!-- Loading -->
    <div v-if="tasksStore.loading" class="state-msg">
      <n-spin size="medium" />
      <span>Loading tasks...</span>
    </div>

    <!-- Error -->
    <div v-else-if="tasksStore.error" class="state-msg error">
      <n-icon :component="AlertCircleOutline" size="24" />
      <span>{{ tasksStore.error }}</span>
      <n-button size="small" @click="reload">Retry</n-button>
    </div>

    <!-- Empty -->
    <div v-else-if="!tasksStore.tasks.length" class="state-msg">
      <n-icon :component="CheckmarkDoneOutline" size="32" color="#374151" />
      <span style="color: #6b7280">No tasks found</span>
      <n-button size="small" @click="ui.openCreateForm()">Create task</n-button>
    </div>

    <!-- Task list -->
    <div v-else class="task-list">
      <div v-for="group in groupedTasks" :key="group.label">
        <div v-if="group.label" class="group-header">{{ group.label }}</div>
        <template v-for="task in group.tasks" :key="task.uid">
          <TaskRow
            :task="task"
            @click="ui.openTask(task.uid)"
            @complete="completeTask(task)"
            @star="toggleStar(task)"
            @expand="toggleExpand(task)"
            :expanded="expandedUids.has(task.uid)"
          />
          <!-- Subtasks inline, after their parent row -->
          <template v-if="expandedUids.has(task.uid)">
            <TaskRow
              v-for="sub in subtasks[task.uid] || []"
              :key="sub.uid"
              :task="sub"
              :is-subtask="true"
              @click="ui.openTask(sub.uid)"
              @complete="completeTask(sub)"
              @star="toggleStar(sub)"
            />
          </template>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircleOutline, CheckmarkDoneOutline } from '@vicons/ionicons5'
import { useTasksStore } from '@/stores/tasks.js'
import { useUiStore } from '@/stores/ui.js'
import { tasksApi } from '@/api/tasks.js'
import TaskRow from './TaskRow.vue'

const route = useRoute()
const tasksStore = useTasksStore()
const ui = useUiStore()
const expandedUids = ref(new Set())
const subtasks = ref({})

function reload() {
  tasksStore.fetchTasks(route.query)
}

const groupedTasks = computed(() => {
  const tasks = tasksStore.tasks
  if (!tasks.length) return []

  // Check if any tasks have due dates — if so, group by date
  const hasDueDates = tasks.some(t => t.due)
  if (!hasDueDates) {
    return [{ label: '', tasks }]
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const nextWeek = new Date(today)
  nextWeek.setDate(nextWeek.getDate() + 7)

  const groups = {
    overdue: { label: 'Overdue', tasks: [] },
    today: { label: 'Today', tasks: [] },
    tomorrow: { label: 'Tomorrow', tasks: [] },
    week: { label: 'This Week', tasks: [] },
    later: { label: 'Later', tasks: [] },
    noDue: { label: 'No Due Date', tasks: [] },
  }

  for (const task of tasks) {
    if (!task.due) {
      groups.noDue.tasks.push(task)
      continue
    }
    const due = new Date(task.due)
    due.setHours(0, 0, 0, 0)
    if (due < today) {
      groups.overdue.tasks.push(task)
    } else if (due.getTime() === today.getTime()) {
      groups.today.tasks.push(task)
    } else if (due.getTime() === tomorrow.getTime()) {
      groups.tomorrow.tasks.push(task)
    } else if (due <= nextWeek) {
      groups.week.tasks.push(task)
    } else {
      groups.later.tasks.push(task)
    }
  }

  return Object.values(groups).filter(g => g.tasks.length)
})

async function toggleExpand(task) {
  if (expandedUids.value.has(task.uid)) {
    expandedUids.value.delete(task.uid)
  } else {
    expandedUids.value.add(task.uid)
    if (!subtasks.value[task.uid]) {
      const res = await tasksApi.list({ parent_uid: task.uid })
      subtasks.value[task.uid] = res.data.tasks || []
    }
  }
}

async function completeTask(task) {
  if (task.status === 'COMPLETED') {
    await tasksStore.patchTask(task.uid, { status: 'NEEDS-ACTION', completed_at: null, percent: 0 })
  } else {
    await tasksStore.completeTask(task.uid)
  }
}

async function toggleStar(task) {
  await tasksStore.patchTask(task.uid, { starred: !task.starred })
}
</script>

<style scoped>
.task-list-container {
  flex: 1;
  overflow-y: auto;
  background: #111318;
}

.state-msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 24px;
  color: #9ca3af;
  font-size: 14px;
}

.state-msg.error {
  color: #f87171;
}

.task-list {
  padding: 0;
}

.group-header {
  padding: 12px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #4b5563;
  border-bottom: 1px solid #1a1d27;
}
</style>
