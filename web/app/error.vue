<template>
  <div class="mx-auto max-w-md space-y-4 py-16 text-center">
    <h1 class="text-2xl font-extrabold text-slate-900">Une erreur est survenue</h1>
    <p class="text-sm text-slate-600">{{ error?.message ?? 'Erreur inattendue.' }}</p>
    <NuxtLink to="/" class="inline-block rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white">Retour à l'accueil</NuxtLink>
  </div>
</template>

<script setup lang="ts">
defineProps<{ error?: { message?: string } }>()
</script>
