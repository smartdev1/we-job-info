import { defineStore } from 'pinia'

interface AuthUser {
  id: string
  email: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)

  async function login(email: string, password: string): Promise<boolean> {
    loading.value = true
    try {
      const client = useApiClient()
      const { error } = await client.POST('/api/v1/auth/login', {
        body: { email, password }
      })
      if (error) return false
      await fetchMe()
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
    await navigateTo('/login')
  }

  async function fetchMe(): Promise<void> {
    const client = useApiClient()
    const { data, error } = await client.GET('/api/v1/auth/me')
    if (error || !data) {
      user.value = null
      return
    }
    user.value = { id: data.id as string, email: data.email as string }
  }

  const isAuthenticated = computed(() => user.value !== null)

  return { user, loading, isAuthenticated, login, logout, fetchMe }
})
