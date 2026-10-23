/**
 * Global auth guard.
 *
 * Every page of the tool except the login/logout entry points requires an
 * authenticated session. An operator who lands on a protected route without
 * one is sent to the login page, with the original URL preserved so that a
 * successful sign-in can send them straight back where they were going.
 */

const PUBLIC_PATHS = ['/login', '/logout']

export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuthStore()
  if (auth.isAuthenticated) {
    return
  }
  if (PUBLIC_PATHS.includes(to.path)) {
    return
  }
  return navigateTo({
    path: '/login',
    query: { redirect: to.path }
  })
})