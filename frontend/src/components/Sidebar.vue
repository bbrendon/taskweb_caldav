<template>
  <aside class="sidebar" :class="{ 'sidebar--open': isOpen }">
    <div class="sidebar-header">
      <span class="app-title">Tasks</span>
      <div class="header-actions">
        <n-button text size="small" @click="$emit('close')" class="close-btn" aria-label="Close menu">
          <template #icon><n-icon :component="CloseOutline" /></template>
        </n-button>
        <n-button text size="small" @click="ui.openCreateForm(); $emit('close')">
          <template #icon><n-icon :component="AddOutline" /></template>
        </n-button>
      </div>
    </div>

    <!-- Main navigation -->
    <nav class="nav-section">
      <router-link :to="{ path: '/tasks' }" class="nav-item" :class="{ active: isAllTasks }">
        <n-icon :component="ListOutline" />
        <span>All Tasks</span>
      </router-link>
      <router-link :to="{ path: '/tasks', query: { status: 'pending' } }" class="nav-item">
        <n-icon :component="CheckboxOutline" />
        <span>Pending</span>
      </router-link>
      <router-link :to="{ path: '/tasks', query: { status: 'completed' } }" class="nav-item">
        <n-icon :component="CheckmarkDoneOutline" />
        <span>Completed</span>
      </router-link>
    </nav>

    <!-- Virtual tags -->
    <div class="section-title">Smart Filters</div>
    <nav class="nav-section">
      <router-link
        v-for="vt in virtualTagNav"
        :key="vt.tag"
        :to="{ path: '/tasks', query: { virtual: vt.tag, status: 'pending' } }"
        class="nav-item virtual-tag"
      >
        <n-icon :component="vt.icon" />
        <span>{{ vt.label }}</span>
        <span v-if="vtCount(vt.tag)" class="badge">{{ vtCount(vt.tag) }}</span>
      </router-link>
    </nav>

    <!-- User tags -->
    <div v-if="tasksStore.allTags.length" class="section-title">Tags</div>
    <nav v-if="tasksStore.allTags.length" class="nav-section tags-section">
      <router-link
        v-for="tag in tasksStore.allTags"
        :key="tag"
        :to="{ path: '/tasks', query: { tags: tag, status: 'pending' } }"
        class="nav-item tag-item"
      >
        <n-icon :component="PricetagOutline" size="14" />
        <span>{{ tag }}</span>
      </router-link>
    </nav>

    <!-- Logout -->
    <div class="sidebar-footer">
      <button class="logout-btn" @click="logout">
        <n-icon :component="LogOutOutline" size="14" />
        Sign out
      </button>
    </div>

    <!-- Saved views -->
    <div v-if="ui.savedViews.length" class="section-title">
      <span>Saved Views</span>
    </div>
    <nav v-if="ui.savedViews.length" class="nav-section">
      <div
        v-for="view in ui.savedViews"
        :key="view.id"
        class="nav-item saved-view"
      >
        <router-link :to="{ path: '/tasks', query: parseQuery(view.query) }" class="view-link">
          <n-icon :component="BookmarkOutline" size="14" />
          <span>{{ view.name }}</span>
        </router-link>
        <n-button text size="tiny" @click.stop="ui.deleteView(view.id)" class="delete-view">
          <n-icon :component="CloseOutline" size="12" />
        </n-button>
      </div>
    </nav>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  AddOutline, ListOutline, CheckboxOutline, CheckmarkDoneOutline,
  AlertCircleOutline, CalendarOutline, StarOutline, RepeatOutline,
  PricetagOutline, BookmarkOutline, CloseOutline, FlashOutline,
  ArrowForwardCircleOutline, LayersOutline, LogOutOutline,
} from '@vicons/ionicons5'
import { useRouter } from 'vue-router'
import { authApi } from '@/api/tasks.js'
import { useTasksStore } from '@/stores/tasks.js'
import { useUiStore } from '@/stores/ui.js'

const router = useRouter()

async function logout() {
  await authApi.logout()
  router.push('/login')
}

defineProps({
  isOpen: { type: Boolean, default: false },
})
defineEmits(['close'])

const route = useRoute()
const tasksStore = useTasksStore()
const ui = useUiStore()

const isAllTasks = computed(() => !Object.keys(route.query).length)

const virtualTagNav = [
  { tag: 'OVERDUE', label: 'Overdue', icon: AlertCircleOutline },
  { tag: 'DUE_TODAY', label: 'Due Today', icon: CalendarOutline },
  { tag: 'DUE_WEEK', label: 'Due This Week', icon: ArrowForwardCircleOutline },
  { tag: 'STARRED', label: 'Starred', icon: StarOutline },
  { tag: 'HIGH', label: 'High Priority', icon: FlashOutline },
  { tag: 'RECURRING', label: 'Recurring', icon: RepeatOutline },
  { tag: 'PARENT', label: 'Has Subtasks', icon: LayersOutline },
]

function vtCount(tag) {
  return tasksStore.virtualTagCounts[tag] || 0
}

function parseQuery(queryStr) {
  if (!queryStr) return {}
  const params = new URLSearchParams(queryStr)
  const obj = {}
  params.forEach((v, k) => { obj[k] = v })
  return obj
}
</script>

<style scoped>
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #0d0f14;
  border-right: 1px solid #1e2130;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 8px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Close button hidden on desktop — only shown on mobile */
.close-btn {
  display: none;
}

.app-title {
  font-size: 16px;
  font-weight: 700;
  color: #e5e7eb;
  letter-spacing: 0.02em;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
}

.nav-section {
  display: flex;
  flex-direction: column;
  padding: 4px 8px;
  gap: 1px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: #9ca3af;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
  white-space: nowrap;
  overflow: hidden;
  min-height: 36px;
}

.nav-item:hover,
.nav-item.router-link-active {
  background: #1e2130;
  color: #e5e7eb;
}

.nav-item.active {
  background: #1e2130;
  color: #e5e7eb;
}

.badge {
  margin-left: auto;
  background: #374151;
  color: #9ca3af;
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 11px;
  font-weight: 600;
}

.virtual-tag .badge {
  background: #1e2a3a;
  color: #5c8df6;
}

.tags-section {
  max-height: 200px;
  overflow-y: auto;
}

.tag-item {
  font-size: 12px;
}

.saved-view {
  justify-content: space-between;
  padding-right: 4px;
}

.view-link {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  text-decoration: none;
  color: inherit;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-view {
  opacity: 0;
  transition: opacity 0.1s;
  flex-shrink: 0;
}

.saved-view:hover .delete-view {
  opacity: 1;
}

.sidebar-footer {
  margin-top: auto;
  padding: 8px;
  border-top: 1px solid #1e2130;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 8px;
  background: none;
  border: none;
  border-radius: 6px;
  color: #6b7280;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.1s, color 0.1s;
}

.logout-btn:hover {
  background: #1e2130;
  color: #e5e7eb;
}

/* ── Mobile ─────────────────────────────────────── */
@media (max-width: 768px) {
  .sidebar-header {
    padding-top: calc(16px + env(safe-area-inset-top));
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    width: 280px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  }

  .sidebar--open {
    transform: translateX(0);
  }

  .close-btn {
    display: flex;
  }

  /* Larger tap targets on mobile */
  .nav-item {
    min-height: 44px;
    font-size: 15px;
    padding: 10px 12px;
  }

  /* Always show delete button for saved views (no hover on touch) */
  .delete-view {
    opacity: 1;
  }
}
</style>
