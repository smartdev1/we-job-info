<template>
  <div class="p-6 text-center text-muted">
    Signing out…
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore()
onMounted(() => {
  auth.logout()
})
</script>
