import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const ACCESS_KEY = 'flowtina_access_token'
const REFRESH_KEY = 'flowtina_refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}
export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}
export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}
export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export const http: AxiosInstance = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

// Bare client for token refresh to avoid interceptor recursion.
const refreshClient: AxiosInstance = axios.create({ baseURL })

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

interface RetriableConfig extends AxiosRequestConfig {
  _retry?: boolean
}

let isRefreshing = false
let pendingQueue: Array<(token: string | null) => void> = []

function flushQueue(token: string | null): void {
  pendingQueue.forEach((cb) => cb(token))
  pendingQueue = []
}

function onAuthFailure(): void {
  clearTokens()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

http.interceptors.response.use(
  (response) => {
    // Unwrap the success envelope { success, message, data }.
    const body = response.data
    if (body && typeof body === 'object' && 'success' in body && 'data' in body) {
      return body.data
    }
    return body
  },
  async (error) => {
    const original = error.config as RetriableConfig
    const status = error.response?.status

    if (status === 401 && original && !original._retry) {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        onAuthFailure()
        return Promise.reject(error)
      }
      original._retry = true

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingQueue.push((token) => {
            if (token) {
              original.headers = { ...original.headers, Authorization: `Bearer ${token}` }
              resolve(http(original))
            } else {
              reject(error)
            }
          })
        })
      }

      isRefreshing = true
      try {
        const resp = await refreshClient.post('/auth/refresh', {
          refresh_token: refreshToken,
        })
        const data = resp.data?.data ?? resp.data
        const newAccess: string = data.access_token
        const newRefresh: string = data.refresh_token
        setTokens(newAccess, newRefresh)
        flushQueue(newAccess)
        original.headers = { ...original.headers, Authorization: `Bearer ${newAccess}` }
        return http(original)
      } catch (refreshErr) {
        flushQueue(null)
        onAuthFailure()
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data
    if (data?.error?.message) return data.error.message
    if (data?.message) return data.message
    return err.message
  }
  if (err instanceof Error) return err.message
  return 'Unexpected error'
}
