import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const ACCESS_KEY = 'flowtina_access_token'
const REFRESH_KEY = 'flowtina_refresh_token'

// Refresh the access token this many seconds before it actually expires so a
// request is never sent with an already-dead token.
const EXPIRY_SKEW_SECONDS = 30

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

interface RetriableConfig extends AxiosRequestConfig {
  _retry?: boolean
}

function onAuthFailure(): void {
  clearTokens()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

// Read the `exp` claim from a JWT without verifying the signature.
function getTokenExpiry(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return typeof payload.exp === 'number' ? payload.exp : null
  } catch {
    return null
  }
}

function isExpiringSoon(token: string): boolean {
  const exp = getTokenExpiry(token)
  if (exp === null) return false
  return Date.now() / 1000 >= exp - EXPIRY_SKEW_SECONDS
}

// A single in-flight refresh shared by every caller so concurrent requests
// trigger at most one /auth/refresh and never reuse a rotated refresh token.
let refreshPromise: Promise<string | null> | null = null

function refreshTokens(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return Promise.resolve(null)

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post('/auth/refresh', { refresh_token: refreshToken })
      .then((resp) => {
        const data = resp.data?.data ?? resp.data
        setTokens(data.access_token, data.refresh_token)
        return data.access_token as string
      })
      .catch(() => null)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

http.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  let token = getAccessToken()
  // Proactively refresh before the token expires so no request ever 401s.
  if (token && isExpiringSoon(token)) {
    token = (await refreshTokens()) ?? token
  }
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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

    // Reactive fallback: token was accepted as valid but the server rejected it
    // (e.g. revoked, clock skew). Refresh once and retry the original request.
    if (status === 401 && original && !original._retry) {
      original._retry = true
      const newToken = await refreshTokens()
      if (newToken) {
        original.headers = { ...original.headers, Authorization: `Bearer ${newToken}` }
        return http(original)
      }
      onAuthFailure()
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
