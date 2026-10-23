import createClient from 'openapi-fetch'
import type { paths } from '~/api-client/schema'

export function useApiClient() {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBase as string

  const csrfToken = useCookie('csrf_token').value

  return createClient<paths>({
    baseUrl,
    credentials: 'include',
    headers: csrfToken ? { 'x-csrf-token': csrfToken } : undefined,
  })
}