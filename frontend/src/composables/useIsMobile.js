import { ref, onMounted, onUnmounted } from 'vue'

export function useIsMobile(breakpoint = 768) {
  const isMobile = ref(
    typeof window !== 'undefined' ? window.innerWidth < breakpoint : false
  )

  function onResize() {
    isMobile.value = window.innerWidth < breakpoint
  }

  onMounted(() => window.addEventListener('resize', onResize))
  onUnmounted(() => window.removeEventListener('resize', onResize))

  return isMobile
}
