<template>
  <div class="app-shell">
    <!-- Mobile sidebar backdrop -->
    <div
      class="sidebar-backdrop"
      :class="{ visible: sidebarOpen }"
      @click="sidebarOpen = false"
    />

    <Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />

    <div class="main-content">
      <!-- Mobile-only top bar -->
      <div class="mobile-header">
        <button class="mobile-icon-btn" @click="sidebarOpen = true" aria-label="Menu">
          <n-icon :component="MenuOutline" size="22" />
        </button>
        <span class="mobile-title">Tasks</span>
        <button class="mobile-icon-btn" @click="ui.openCreateForm()" aria-label="New task">
          <n-icon :component="AddOutline" size="22" />
        </button>
      </div>

      <SearchBar />

      <div class="task-area">
        <TaskList />
        <TaskDetail v-if="ui.activeTaskUid && !ui.showTaskForm" />
        <TaskForm v-if="ui.showTaskForm" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { MenuOutline, AddOutline } from '@vicons/ionicons5'
import Sidebar from './Sidebar.vue'
import SearchBar from './SearchBar.vue'
import TaskList from './TaskList.vue'
import TaskDetail from './TaskDetail.vue'
import TaskForm from './TaskForm.vue'
import { useTasksStore } from '@/stores/tasks.js'
import { useUiStore } from '@/stores/ui.js'

const route = useRoute()
const tasksStore = useTasksStore()
const ui = useUiStore()
const sidebarOpen = ref(false)

onMounted(async () => {
  await tasksStore.fetchTasks(route.query)
  await tasksStore.fetchTags()
})

watch(() => route.query, () => {
  tasksStore.fetchTasks(route.query)
}, { deep: true })

// Auto-close sidebar on navigation (mobile)
watch(() => route.fullPath, () => {
  sidebarOpen.value = false
})
</script>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  height: 100dvh; /* dynamic viewport height — avoids mobile browser chrome issues */
  overflow: hidden;
  background: #111318;
  color: #e5e7eb;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.task-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Mobile header — hidden on desktop */
.mobile-header {
  display: none;
}

/* Backdrop — hidden on desktop */
.sidebar-backdrop {
  display: none;
}

@media (max-width: 768px) {
  .mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: env(safe-area-inset-top) 8px 0;
    height: calc(52px + env(safe-area-inset-top));
    flex-shrink: 0;
    border-bottom: 1px solid #1e2130;
    background: #0d0f14;
  }

  .mobile-title {
    font-size: 17px;
    font-weight: 700;
    color: #e5e7eb;
  }

  .mobile-icon-btn {
    background: none;
    border: none;
    color: #9ca3af;
    cursor: pointer;
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
  }

  .mobile-icon-btn:active {
    background: #1e2130;
    color: #e5e7eb;
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 99;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s;
  }

  .sidebar-backdrop.visible {
    opacity: 1;
    pointer-events: all;
  }
}
</style>
