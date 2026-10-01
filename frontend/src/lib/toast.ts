import { ref } from 'vue'

export interface Toast { id: number; text: string; action?: { label: string; run: () => void } }

export const toasts = ref<Toast[]>([])
let seq = 0

export function toast(text: string, action?: Toast['action'], ms = 5000) {
  const t = { id: ++seq, text, action }
  toasts.value = [...toasts.value.slice(-2), t]
  window.setTimeout(() => dismiss(t.id), ms)
}

export function dismiss(id: number) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}
