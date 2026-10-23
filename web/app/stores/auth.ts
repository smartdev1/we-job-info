import { defineStore } from 'pinia'

interface AuthUser {
  id: string
  email: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)
  const initialized = ref(false)

  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const client = useApiClient()
      const { data, error, response } = await client.POST('/api/v1/auth/login', {
        body: { email, password }
      })
      if (error || !response?.ok) return false
      // Set user from login response + fetch full profile
      await fetchMe()
      initialized.value = true
      return true
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    const client = useApiClient()
    const csrf = useCookie('csrf_token').value
    await client.POST('/api/v1/auth/logout', {
      headers: { 'x-csrf-token': csrf ?? '' }
    })
    user.value = null
    initialized.value = false
    await navigateTo('/login')
  }

  async function fetchMe(): Promise<void> {
    const client = useApiClient()
    const { data, error, response } = await client.GET('/api/v1/auth/me')
    if (error || !response?.ok || !data) {
      user.value = null
      return
    }
    user.value = { id: (data as any).id as string, email: (data as any).email as string }
  }

  const isAuthenticated = computed(() => user.value !== null)

  return { user, loading, initialized, isAuthenticated, login, logout, fetchMe }
})
