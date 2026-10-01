<script setup lang="ts">
import { onMounted } from 'vue'
import { useSession } from '@/stores/session'
import LoginView from '@/views/LoginView.vue'

const session = useSession()
onMounted(session.check)
</script>

<template>
  <RouterView v-if="session.authenticated" />
  <LoginView v-else-if="session.authenticated === false" />
</template>
