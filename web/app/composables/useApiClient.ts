import createClient from 'openapi-fetch'
import type { paths } from '~/api-client/schema'

export function useApiClient() {
  const config = useRuntimeConfig()
  const baseUrl = config.public.apiBase as string

  return createClient<paths>({
    baseUrl,
    credentials: 'include'
  })
}
