<script setup lang="ts">
const title = 'Offres'
const subtitle = 'Les offres recueillies sur les plateformes, classées de la plus récente à la plus ancienne.'
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">
          {{ title }}
        </h1>
        <p class="mt-1 max-w-2xl text-sm text-slate-600">
          {{ subtitle }}
        </p>
      </div>
      <NuxtLink
        to="/offers/new"
        class="inline-flex items-center gap-2 rounded-xl bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-sky-700 active:scale-[0.98]"
      >
        <UIcon
          name="i-lucide-plus"
          class="size-4"
        />
        Nouvelle offre
      </NuxtLink>
    </div>

    <OffersList bulk />
  </div>
</template>
