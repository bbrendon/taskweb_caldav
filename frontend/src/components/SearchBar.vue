<template>
  <div class="search-bar">
    <div class="search-input-wrap">
      <n-icon :component="SearchOutline" class="search-icon" />
      <input
        v-model="searchText"
        class="search-input"
        placeholder="Search tasks..."
        @input="onSearchInput"
      />
      <button v-if="searchText" class="clear-btn" @click="clearSearch">
        <n-icon :component="CloseOutline" />
      </button>
    </div>

    <!-- Active filter chips -->
    <div class="filter-chips">
      <template v-for="chip in activeChips" :key="chip.key">
        <div class="chip" :class="chip.type">
          {{ chip.label }}
          <button class="chip-remove" @click="removeFilter(chip.key)">×</button>
        </div>
      </template>
    </div>

    <!-- Right side actions -->
    <div class="search-actions">
      <n-button
        v-if="hasActiveFilters"
        size="small"
        text
        @click="saveCurrentView"
      >
        <template #icon><n-icon :component="BookmarkOutline" /></template>
        Save View
      </n-button>
      <n-button size="small" @click="ui.openCreateForm()" type="primary">
        <template #icon><n-icon :component="AddOutline" /></template>
        New Task
      </n-button>
    </div>

    <!-- Save view dialog -->
    <n-modal v-model:show="showSaveDialog">
      <n-card title="Save View" style="width: 360px">
        <n-input v-model:value="viewName" placeholder="View name..." />
        <template #footer>
          <div style="display: flex; gap: 8px; justify-content: flex-end">
            <n-button @click="showSaveDialog = false">Cancel</n-button>
            <n-button type="primary" @click="confirmSaveView">Save</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { SearchOutline, CloseOutline, AddOutline, BookmarkOutline } from '@vicons/ionicons5'
import { useUiStore } from '@/stores/ui.js'

const route = useRoute()
const router = useRouter()
const ui = useUiStore()

const searchText = ref(route.query.search || '')
const showSaveDialog = ref(false)
const viewName = ref('')

let debounceTimer = null

function onSearchInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    const q = { ...route.query }
    if (searchText.value.trim()) {
      q.search = searchText.value.trim()
    } else {
      delete q.search
    }
    router.replace({ query: q })
  }, 300)
}

function clearSearch() {
  searchText.value = ''
  const q = { ...route.query }
  delete q.search
  router.replace({ query: q })
}

function removeFilter(key) {
  const q = { ...route.query }
  delete q[key]
  router.replace({ query: q })
}

const activeChips = computed(() => {
  const chips = []
  const q = route.query
  if (q.status) chips.push({ key: 'status', label: `Status: ${q.status}`, type: 'status' })
  if (q.tags) chips.push({ key: 'tags', label: `Tags: ${q.tags}`, type: 'tag' })
  if (q.virtual) chips.push({ key: 'virtual', label: `Filter: ${q.virtual}`, type: 'virtual' })
  if (q.priority) chips.push({ key: 'priority', label: `Priority: ${q.priority}`, type: 'priority' })
  if (q.search) chips.push({ key: 'search', label: `Search: ${q.search}`, type: 'search' })
  return chips
})

const hasActiveFilters = computed(() => Object.keys(route.query).length > 0)

function saveCurrentView() {
  viewName.value = ''
  showSaveDialog.value = true
}

function confirmSaveView() {
  if (!viewName.value.trim()) return
  const queryStr = new URLSearchParams(route.query).toString()
  ui.saveView(viewName.value.trim(), queryStr)
  showSaveDialog.value = false
}

// Sync search text from URL changes (e.g. sidebar navigation)
watch(() => route.query.search, (val) => {
  searchText.value = val || ''
})
</script>

<style scoped>
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid #1e2130;
  background: #111318;
  flex-wrap: wrap;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #1a1d27;
  border: 1px solid #2d3148;
  border-radius: 8px;
  padding: 0 10px;
  flex: 1;
  min-width: 200px;
  max-width: 360px;
}

.search-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: #e5e7eb;
  font-size: 13px;
  padding: 8px 0;
}

.search-input::placeholder {
  color: #4b5563;
}

.clear-btn {
  background: none;
  border: none;
  color: #6b7280;
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
}

.clear-btn:hover {
  color: #e5e7eb;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}

.chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  background: #1e2130;
  color: #9ca3af;
}

.chip.status { background: #1e2a1e; color: #6ee7b7; }
.chip.tag { background: #1e2130; color: #93c5fd; }
.chip.virtual { background: #2a1e1e; color: #fca5a5; }
.chip.priority { background: #2a2a1e; color: #fde68a; }
.chip.search { background: #1e1e2a; color: #c4b5fd; }

.chip-remove {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  font-size: 14px;
  line-height: 1;
  opacity: 0.7;
}

.chip-remove:hover { opacity: 1; }

.search-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}

@media (max-width: 768px) {
  .search-bar {
    padding: 8px 12px;
    gap: 6px;
  }

  .search-input-wrap {
    max-width: 100%;
    min-width: 0;
    flex: 1;
  }

  /* Stack chips below search row */
  .filter-chips {
    order: 3;
    width: 100%;
    flex-basis: 100%;
  }

  .search-actions {
    margin-left: 0;
    flex-shrink: 0;
  }
}
</style>
