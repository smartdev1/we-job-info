<script setup lang="ts">
import { computed } from 'vue'
import { useQuery } from '@tanstack/vue-query'

const config = useRuntimeConfig()
const apiBase = (config.public.apiBase as string).replace(/\/$/, '')

interface Stats {
  total: number
  suspicious: number
  by_status: Record<string, number>
  by_contract: { contract: string; count: number }[]
  by_source: { source: string; count: number }[]
}

const { data: stats, isLoading, error } = useQuery({
  queryKey: ['offer-stats'],
  queryFn: async () => {
    const res = await fetch(`${apiBase}/api/v1/offers/stats`, { credentials: 'include' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return res.json() as Promise<Stats>
  },
  refetchInterval: 30000
})

const cards = computed(() => {
  const value = stats.value
  return [
    { label: 'Offres recueillies', value: value?.total ?? 0, tone: 'text-slate-900' },
    { label: 'Nouvelles', value: value?.by_status?.nouvelle ?? 0, tone: 'text-sky-700' },
    { label: 'Sélectionnées', value: value?.by_status?.selectionnee ?? 0, tone: 'text-violet-700' },
    { label: 'Publiées', value: value?.by_status?.publiee ?? 0, tone: 'text-emerald-700' },
    { label: 'À vérifier', value: value?.suspicious ?? 0, tone: 'text-red-700' }
  ]
})
</script>

<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-2xl font-extrabold tracking-tight text-slate-900">
        Tableau de bord
      </h1>
      <p class="mt-1 text-sm text-slate-600">
        L’état de la collecte, source par source.
      </p>
    </div>

    <p
      v-if="isLoading"
      class="text-sm text-slate-500"
    >
      Chargement des statistiques…
    </p>
    <p
      v-else-if="error"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      role="alert"
    >
      Statistiques indisponibles.
    </p>

    <template v-else>
      <div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <div
          v-for="card in cards"
          :key="card.label"
          class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
        >
          <p class="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {{ card.label }}
          </p>
          <p
            class="mt-2 font-mono text-2xl font-bold"
            :class="card.tone"
          >
            {{ card.value }}
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-sm font-bold uppercase tracking-wider text-slate-500">
            Par source
          </h2>
          <ul class="mt-4 space-y-2.5">
            <li
              v-for="row in stats?.by_source ?? []"
              :key="row.source"
              class="flex items-center gap-3"
            >
              <span class="w-32 shrink-0 truncate text-sm text-slate-700">{{ row.source }}</span>
              <span class="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <span
                  class="block h-full rounded-full bg-sky-500"
                  :style="{ width: `${stats && stats.total ? Math.round((row.count / stats.total) * 100) : 0}%` }"
                />
              </span>
              <span class="w-10 shrink-0 text-right font-mono text-xs text-slate-500">{{ row.count }}</span>
            </li>
          </ul>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-sm font-bold uppercase tracking-wider text-slate-500">
            Par type de contrat
          </h2>
          <ul class="mt-4 space-y-2.5">
            <li
              v-for="row in stats?.by_contract ?? []"
              :key="row.contract"
              class="flex items-center gap-3"
            >
              <span class="w-32 shrink-0 truncate text-sm text-slate-700">{{ row.contract }}</span>
              <span class="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <span
                  class="block h-full rounded-full bg-violet-400"
                  :style="{ width: `${stats && stats.total ? Math.round((row.count / stats.total) * 100) : 0}%` }"
                />
              </span>
              <span class="w-10 shrink-0 text-right font-mono text-xs text-slate-500">{{ row.count }}</span>
            </li>
          </ul>
        </section>
      </div>
    </template>

    <section class="space-y-4">
      <div class="flex items-end justify-between gap-4">
        <h2 class="text-lg font-extrabold tracking-tight text-slate-900">
          Dernières offres
        </h2>
        <NuxtLink
          to="/offers"
          class="text-sm font-semibold text-sky-700 underline-offset-2 hover:underline"
        >
          Traiter la liste
        </NuxtLink>
      </div>
      <OffersList />
    </section>
  </div>
</template>
