/**
 * Centralized API client.
 *
 * Wraps fetch() with:
 *   - credentials: 'include' (session cookie)
 *   - x-csrf-token header on write methods
 *   - unified error handling (401 → redirect to login, 429 → toast, etc.)
 *   - base URL from runtimeConfig
 *
 * Usage:
 *   const api = useApi()
 *   const { data, error } = await api.get('/api/v1/offers')
 *   const { data, error } = await api.post('/api/v1/offers/from-url', { body: { url } })
 */

interface ApiResult<T> {
  data: T | null
  error: ApiError | null
  response: Response | null
}

interface ApiError {
  status: number
  message: string
  detail?: unknown
}

export function useApi() {
  const config = useRuntimeConfig()
  const baseUrl = (config.public.apiBase as string).replace(/\/$/, '')
  const auth = useAuthStore()

  function csrfToken(): string | undefined {
    return useCookie('csrf_token').value ?? undefined
  }

  async function request<T = any>(
    method: string,
    path: string,
    options?: { body?: any; params?: Record<string, any> }
  ): Promise<ApiResult<T>> {
    const url = new URL(`${baseUrl}${path}`)
    if (options?.params) {
      for (const [k, v] of Object.entries(options.params)) {
        if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
      }
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = csrfToken()
    if (token && method !== 'GET') {
      headers['x-csrf-token'] = token
    }

    let response: Response
    try {
      response = await fetch(url.toString(), {
        method,
        credentials: 'include',
        headers,
        body: options?.body ? JSON.stringify(options.body) : undefined,
      })
    } catch (e) {
      // Network error (cold start, timeout, CORS)
      return { data: null, error: { status: 0, message: 'Erreur réseau. Réessayez.' }, response: null }
    }

    // Handle 401 — session expired
    if (response.status === 401) {
      auth.user = null
      if (import.meta.client) {
        navigateTo('/login', { replace: true })
      }
      return { data: null, error: { status: 401, message: 'Session expirée. Reconnectez-vous.' }, response }
    }

    // Handle 429 — rate limited
    if (response.status === 429) {
      return { data: null, error: { status: 429, message: 'Trop de tentatives. Réessayez dans 15 minutes.' }, response }
    }

    // Handle 422 — validation error
    if (response.status === 422) {
      const body = await response.json().catch(() => null)
      const detail = body?.detail
      const message = Array.isArray(detail)
        ? detail.map((d: any) => d.msg || d).join(', ')
        : (typeof detail === 'string' ? detail : 'Données invalides.')
      return { data: null, error: { status: 422, message, detail }, response }
    }

    // Handle other errors
    if (!response.ok) {
      const body = await response.text().catch(() => '')
      return { data: null, error: { status: response.status, message: `Erreur ${response.status}. ${body}`.trim() }, response }
    }

    // Parse JSON response
    let data: T | null = null
    try {
      data = await response.json()
    } catch {
      // Empty response (204 No Content)
    }

    return { data, error: null, response }
  }

  return {
    get: <T = any>(path: string, params?: Record<string, any>) => request<T>('GET', path, { params }),
    post: <T = any>(path: string, body?: any) => request<T>('POST', path, { body }),
    patch: <T = any>(path: string, body?: any) => request<T>('PATCH', path, { body }),
    put: <T = any>(path: string, body?: any) => request<T>('PUT', path, { body }),
    delete: <T = any>(path: string) => request<T>('DELETE', path),
  }
}