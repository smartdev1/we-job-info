<template>
  <div class="flex min-h-[60vh] items-center justify-center p-6">
    <UCard class="w-full max-w-sm">
      <template #header>
        <h1 class="text-xl font-semibold">
          Login
        </h1>
      </template>
      <form
        class="space-y-4"
        @submit.prevent="onSubmit"
      >
        <UFormField
          label="Email"
          name="email"
        >
          <UInput
            v-model="email"
            type="email"
            required
            autocomplete="username"
          />
        </UFormField>
        <UFormField
          label="Password"
          name="password"
        >
          <UInput
            v-model="password"
            type="password"
            required
            autocomplete="current-password"
          />
        </UFormField>
        <UButton
          type="submit"
          :loading="auth.loading"
          block
        >
          Sign in
        </UButton>
        <p
          v-if="error"
          class="text-sm text-red-500"
        >
          {{ error }}
        </p>
      </form>
    </UCard>
  </div>
</template>

<script setup lang="ts">
const auth = useAuthStore()
const email = ref('')
const password = ref('')
const error = ref('')

async function onSubmit() {
  error.value = ''
  const ok = await auth.login(email.value, password.value)
  if (ok) {
    await navigateTo('/dashboard')
  } else {
    error.value = 'Invalid credentials'
  }
}
</script>
