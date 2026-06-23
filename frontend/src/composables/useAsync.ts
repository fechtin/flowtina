import { ref } from 'vue'
import { extractErrorMessage } from '@/services/http'
import { useToastStore } from '@/stores/toast'

/**
 * Wraps an async action with loading state and toast-based error reporting.
 */
export function useAsync() {
  const loading = ref(false)
  const toast = useToastStore()

  async function run<T>(
    action: () => Promise<T>,
    options: { successMessage?: string; silentError?: boolean } = {},
  ): Promise<T | undefined> {
    loading.value = true
    try {
      const result = await action()
      if (options.successMessage) toast.success(options.successMessage)
      // Callers distinguish success from failure via `result !== undefined`.
      // Many actions resolve to void (delete, job-run, login/register), which
      // would otherwise look identical to the error path and silently swallow
      // success handlers (toasts, redirects, list reloads). Return a truthy
      // sentinel so success is always detectable, while preserving real data
      // when present (?? keeps falsy-but-valid values like 0, '' or []).
      return result ?? (true as unknown as T)
    } catch (err) {
      if (!options.silentError) toast.error(extractErrorMessage(err))
      return undefined
    } finally {
      loading.value = false
    }
  }

  return { loading, run }
}
