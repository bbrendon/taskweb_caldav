<script setup lang="ts">
import { computed } from 'vue'
import { matches, placeView, SMART_LISTS, tagView, type View } from '@/lib/filters'
import { useSession } from '@/stores/session'
import { useTasks } from '@/stores/tasks'
import { useViews } from '@/stores/views'
import Icon from './Icon.vue'

defineProps<{ active: string; open: boolean }>()
const emit = defineEmits<{ close: [] }>()

const tasks = useTasks()
const views = useViews()
const session = useSession()

const PRIMARY = ['pending', 'today', 'week', 'overdue', 'starred']
const MORE = ['high', 'recurring', 'single', 'subtasks', 'deferred', 'completed', 'all']
const primary = SMART_LISTS.filter((v) => PRIMARY.includes(v.id))
const more = SMART_LISTS.filter((v) => MORE.includes(v.id))

const count = (v: View) => tasks.all.filter((t) => matches(t, v.filter, tasks.tz)).length

const tagLists = computed(() => tasks.allTags.map(tagView))
const placeLists = computed(() => (tasks.config?.places ?? []).map((p) => placeView(p.name)))

// Overdue gets the rail color so it reads at a glance; other counts stay quiet.
const urgentCount = computed(() => count(SMART_LISTS.find((v) => v.id === 'overdue')!))
</script>

<template>
  <div class="scrim" :class="{ open }" @click="emit('close')" />
  <nav class="nav" :class="{ open }" aria-label="Lists">
    <div class="brand">
      <img src="/favicon.svg" width="24" height="24" alt="" />
      <span>TaskWeb</span>
      <button class="icon-btn close" aria-label="Close menu" @click="emit('close')"><Icon name="x" /></button>
    </div>

    <ul class="group">
      <li v-for="v in primary" :key="v.id">
        <RouterLink :to="`/list/${v.id}`" class="item" :class="{ active: active === v.id }" @click="emit('close')">
          <span class="name">{{ v.name }}</span>
          <span class="count" :class="{ urgent: v.id === 'overdue' && urgentCount }">{{ count(v) || '' }}</span>
        </RouterLink>
      </li>
    </ul>

    <h2 v-if="tagLists.length">Tags</h2>
    <ul class="group">
      <li v-for="v in tagLists" :key="v.id">
        <RouterLink :to="`/list/${encodeURIComponent(v.id)}`" class="item" :class="{ active: active === v.id }" @click="emit('close')">
          <span class="name"><span class="hash">#</span>{{ v.name }}</span>
          <span class="count">{{ count(v) || '' }}</span>
        </RouterLink>
      </li>
    </ul>

    <h2 v-if="placeLists.length">Places</h2>
    <ul class="group">
      <li v-for="v in placeLists" :key="v.id">
        <RouterLink :to="`/list/${encodeURIComponent(v.id)}`" class="item" :class="{ active: active === v.id }" @click="emit('close')">
          <span class="name"><Icon name="pin" :size="15" class="lead" />{{ v.name }}</span>
          <span class="count">{{ count(v) || '' }}</span>
        </RouterLink>
      </li>
    </ul>

    <h2 v-if="views.saved.length">Saved searches</h2>
    <ul class="group">
      <li v-for="v in views.saved" :key="v.id">
        <RouterLink :to="`/list/${encodeURIComponent(v.id)}`" class="item" :class="{ active: active === v.id }" @click="emit('close')">
          <span class="name">{{ v.name }}</span>
          <span class="count">{{ count(v) || '' }}</span>
        </RouterLink>
      </li>
    </ul>

    <h2>More lists</h2>
    <ul class="group">
      <li v-for="v in more" :key="v.id">
        <RouterLink :to="`/list/${v.id}`" class="item" :class="{ active: active === v.id }" @click="emit('close')">
          <span class="name">{{ v.name }}</span>
          <span class="count">{{ count(v) || '' }}</span>
        </RouterLink>
      </li>
    </ul>

    <button class="item signout" @click="session.logout()">
      <span class="name"><Icon name="logout" :size="15" class="lead" />Sign out</span>
    </button>
  </nav>
</template>

<style scoped>
.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  height: 100%;
  overflow-y: auto;
  padding: calc(12px + var(--safe-t)) 10px calc(16px + var(--safe-b));
  background: var(--ground);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 8px 14px;
  font-weight: 700;
  font-size: var(--step-1);
}
.brand .close { margin-left: auto; display: none; }
h2 {
  margin: 16px 8px 4px;
  font-size: var(--step--1);
  font-weight: 600;
  color: var(--muted);
}
.group { list-style: none; margin: 0; padding: 0; }
.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-height: 32px;
  padding: 0 8px;
  border: 0;
  border-radius: var(--radius-m);
  background: transparent;
  color: var(--ink);
  text-decoration: none;
  text-align: left;
}
.item:hover { background: var(--accent-soft); }
.item.active { background: var(--accent); color: var(--accent-ink); }
.item.active .count, .item.active .hash { color: inherit; opacity: 0.85; }
.name { display: inline-flex; align-items: center; gap: 6px; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.hash { color: var(--faint); }
.lead { color: var(--muted); flex: none; }
.count { color: var(--muted); font-size: var(--step--1); }
.count.urgent { color: var(--rail-late); font-weight: 700; }
.signout { margin-top: auto; color: var(--muted); }
.scrim { display: none; }

@media (pointer: coarse) {
  .item { min-height: 44px; }
}

@media (max-width: 759px) {
  .nav {
    position: fixed;
    inset: 0 auto 0 0;
    z-index: 30;
    width: min(300px, 84vw);
    transform: translateX(-100%);
    transition: transform 0.22s ease;
    box-shadow: var(--shadow-panel);
  }
  .nav.open { transform: none; }
  .brand .close { display: inline-grid; }
  .scrim {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 29;
    background: rgb(15 20 26 / 0.35);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.22s;
  }
  .scrim.open { opacity: 1; pointer-events: auto; }
}
</style>
