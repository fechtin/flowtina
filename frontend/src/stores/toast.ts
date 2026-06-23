import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface Toast {
  id: number
  type: ToastType
  message: string
}

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])
  let counter = 0

  function push(message: string, type: ToastType = 'info', duration = 4000): void {
    const id = ++counter
    toasts.value.push({ id, type, message })
    window.setTimeout(() => dismiss(id), duration)
  }

  function dismiss(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  const success = (m: string) => push(m, 'success')
  const error = (m: string) => push(m, 'error')
  const info = (m: string) => push(m, 'info')
  const warning = (m: string) => push(m, 'warning')

  return { toasts, push, dismiss, success, error, info, warning }
})
