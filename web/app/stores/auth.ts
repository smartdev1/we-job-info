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
      const api = useApi()
      const { data, error } = await api.post('/api/v1/auth/login', { email, password })
      if (error) return false
      await fetchMe()
      initialized.value = true
      return true
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    const api = useApi()
    const csrf = useCookie('csrf_token').value
    await api.post('/api/v1/auth/logout', {})
    user.value = null
    initialized.value = false
    await navigateTo('/login')
  }

  async function fetchMe(): Promise<void> {
    const api = useApi()
    const { data, error } = await api.get('/api/v1/auth/me')
    if (error || !data) {
      user.value = null
      return
    }
    user.value = { id: (data as any).id as string, email: (data as any).email as string }
  }

  const isAuthenticated = computed(() => user.value !== null)

  return { user, loading, initialized, isAuthenticated, login, logout, fetchMe }
})
