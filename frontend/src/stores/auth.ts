import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authService } from '@/services'
import { clearTokens, getAccessToken, getRefreshToken, setTokens } from '@/services/http'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(getAccessToken())
  const refreshToken = ref<string | null>(getRefreshToken())
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function persist(access: string, refresh: string): void {
    accessToken.value = access
    refreshToken.value = refresh
    setTokens(access, refresh)
  }

  async function login(email: string, password: string): Promise<void> {
    const tokens = await authService.login({ email, password })
    persist(tokens.access_token, tokens.refresh_token)
    await fetchProfile()
  }

  async function register(email: string, password: string, name: string): Promise<void> {
    const tokens = await authService.register({ email, password, name })
    persist(tokens.access_token, tokens.refresh_token)
    await fetchProfile()
  }

  async function fetchProfile(): Promise<void> {
    user.value = await authService.getProfile()
  }

  async function logout(): Promise<void> {
    try {
      await authService.logout()
    } catch {
      // Ignore network/logout errors; clear local state regardless.
    }
    clearTokens()
    accessToken.value = null
    refreshToken.value = null
    user.value = null
  }

  function setUser(value: User): void {
    user.value = value
  }

  return {
    accessToken,
    refreshToken,
    user,
    isAuthenticated,
    login,
    register,
    logout,
    fetchProfile,
    setUser,
  }
})
