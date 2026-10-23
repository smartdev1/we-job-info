/**
 * Auth state restoration.
 *
 * The session lives in an httponly cookie, so the store cannot know whether
 * the operator is already signed in when the app boots. This plugin asks the
 * server for the current user on mount; a successful answer unlocks every
 * protected route, a failure leaves the operator on the login page.
 */

export default defineNuxtPlugin({
  name: 'auth:restore',
  setup() {
    const auth = useAuthStore()
    onMounted(() => {
      if (!auth.isAuthenticated) {
        auth.fetchMe()
      }
    })
  }
})