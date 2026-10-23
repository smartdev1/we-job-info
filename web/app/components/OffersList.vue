<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useInfiniteQuery } from '@tanstack/vue-query'

const props = withDefaults(defineProps<{ bulk?: boolean }>(), { bulk: false })

const router = useRouter()
const api = useApi()

interface OfferItem {
  id: string
  title: string | null
  company: string | null
  city: string | null
  contract_type: string | null
  sector: string | null
  status: string
  score: number | null
  suspicious: boolean
  created_at: string
}

interface Page {
  items: OfferItem[]
  next_cursor: string | null
}

/** The statuses of the offer state machine, in the wording of the channel. */
const STATUSES = [
  { value: 'nouvelle', label: 'Nouvelle' },
  { value: 'selectionnee', label: 'Sélectionnée' },
  { value: 'rejetee', label: 'Rejetée' },
  { value: 'publiee', label: 'Publiée' },
  { value: 'archivee', label: 'Archivée' }
]

const search = ref('')
const debouncedSearch = ref('')
const status = ref('')
const city = ref('')
const cursor = ref<string | null>(null)
const selected = ref<string[]>([])
const actionError = ref<string | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(search, (value) => {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    debouncedSearch.value = value.trim()
  }, 350)
})

const queryKey = computed(() => ['offers', status.value, city.value, debouncedSearch.value])

const {
  data,
  isLoading,
  isFetching,
  error,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  refetch
} = useInfiniteQuery({
  queryKey,
  initialPageParam: null as string | null,
  queryFn: async ({ pageParam }: { pageParam: string | null }) => {
    const params = new URLSearchParams()
    if (status.value) params.set('status', status.value)
    if (city.value) params.set('city', city.value)
    if (debouncedSearch.value) params.set('q', debouncedSearch.value)
    if (pageParam) params.set('cursor', pageParam)
    const { data, error } = await api.get<Page>(`/api/v1/offers?${params.toString()}`)
    if (error) throw new Error(error.message)
    return data as Page
  },
  getNextPageParam: (last: Page) => last.next_cursor ?? undefined,
  refetchInterval: 10000
})

const items = computed(() => (data.value?.pages ?? []).flatMap((page) => page.items))
const total = computed(() => items.value.length)
const nextCursor = computed(() => data.value?.pages?.[data.value.pages.length - 1]?.next_cursor ?? null)

function statusLabel(value: string) {
  return STATUSES.find((s) => s.value === value)?.label ?? value
}

function statusClass(value: string) {
  switch (value) {
    case 'selectionnee': return 'bg-sky-100 text-sky-800'
    case 'publiee': return 'bg-green-100 text-green-800'
    case 'rejetee': return 'bg-red-100 text-red-800'
    case 'archivee': return 'bg-slate-100 text-slate-600'
    default: return 'bg-slate-100 text-slate-700'
  }
}

function contractClass(value: string | null) {
  switch (value) {
    case 'CDI': return 'bg-violet-100 text-violet-900'
    case 'Freelance': return 'bg-amber-100 text-amber-900'
    case 'Stage': return 'bg-sky-100 text-sky-800'
    case 'CDD': return 'bg-blue-50 text-blue-800 border border-blue-200'
    case 'Temps partiel': return 'bg-teal-50 text-teal-800'
    default: return 'bg-slate-100 text-slate-700'
  }
}

function formatRelative(value: string) {
  const date = new Date(value)
  const seconds = Math.round((Date.now() - date.getTime()) / 1000)
  if (Number.isNaN(seconds)) return ''
  if (seconds < 60) return "à l'instant"
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `il y a ${minutes} min`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `il y a ${hours} h`
  const days = Math.round(hours / 24)
  if (days < 31) return `il y a ${days} j`
  return date.toLocaleDateString('fr-FR')
}

function toggleAll(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  selected.value = checked ? items.value.map((o) => o.id) : []
}

function toggleOne(id: string) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((value) => value !== id)
    : [...selected.value, id]
}

async function transition(ids: string[], newStatus: string) {
  actionError.value = null
  const failures: string[] = []
  for (const id of ids) {
    const { error } = await api.post(`/api/v1/offers/${id}/status`, { status: newStatus })
    if (error) {
      failures.push(id)
    }
  }
  if (failures.length) {
    actionError.value = failures.length === ids.length
      ? `Transition impossible depuis le statut actuel (${newStatus}).`
      : `${failures.length} offre(s) n'ont pas pu changer de statut.`
  }
  selected.value = []
  await refetch()
}

function resetFilters() {
  search.value = ''
  debouncedSearch.value = ''
  status.value = ''
  city.value = ''
}

function goTo(id: string) {
  router.push(`/offers/${id}`)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Filters -->
    <div class="rounded-xl border border-slate-200 bg-white p-2 shadow-sm">
      <div class="grid grid-cols-1 gap-2 md:grid-cols-12">
        <div class="relative md:col-span-4">
          <span
            class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            aria-hidden="true"
          >
            <UIcon name="i-lucide-search" />
          </span>
          <input
            v-model="search"
            type="search"
            placeholder="Poste, entreprise, ville…"
            aria-label="Rechercher une offre"
            class="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/30"
          >
        </div>

        <div class="md:col-span-3 md:border-l md:border-slate-200 md:pl-3">
          <label
            for="filter-status"
            class="sr-only"
          >Statut</label>
          <select
            id="filter-status"
            v-model="status"
            class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors focus:border-sky-500 focus:ring-2 focus:ring-sky-500/30"
          >
            <option value="">
              Tous les statuts
            </option>
            <option
              v-for="s in STATUSES"
              :key="s.value"
              :value="s.value"
            >
              {{ s.label }}
            </option>
          </select>
        </div>

        <div class="md:col-span-3 md:border-l md:border-slate-200 md:pl-3">
          <label
            for="filter-city"
            class="sr-only"
          >Ville</label>
          <input
            id="filter-city"
            v-model="city"
            type="text"
            placeholder="Ville"
            class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors placeholder:text-slate-400 focus:border-sky-500 focus:ring-2 focus:ring-sky-500/30"
            @change="refetch()"
          >
        </div>

        <div class="flex items-center justify-end gap-2 md:col-span-2 md:border-l md:border-slate-200 md:pl-3">
          <span class="hidden font-mono text-xs text-slate-500 lg:inline">
            {{ total }} offre(s)
          </span>
          <button
            type="button"
            class="rounded-lg px-2 py-1.5 text-xs font-semibold text-sky-700 transition-colors hover:bg-sky-50"
            @click="resetFilters"
          >
            Réinitialiser
          </button>
        </div>
      </div>
    </div>

    <!-- Bulk actions -->
    <div
      v-if="props.bulk && selected.length"
      class="flex flex-wrap items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3"
    >
      <span class="font-mono text-xs font-semibold text-sky-900">{{ selected.length }} sélectionnée(s)</span>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:bg-sky-700 active:scale-[0.98]"
          @click="transition(selected, 'selectionnee')"
        >
          Sélectionner
        </button>
        <button
          type="button"
          class="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-slate-200 transition-all hover:bg-slate-50 active:scale-[0.98]"
          @click="transition(selected, 'rejetee')"
        >
          Rejeter
        </button>
        <button
          type="button"
          class="rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm ring-1 ring-slate-200 transition-all hover:bg-slate-50 active:scale-[0.98]"
          @click="transition(selected, 'publiee')"
        >
          Publier
        </button>
      </div>
    </div>

    <p
      v-if="actionError"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      role="alert"
    >
      {{ actionError }}
    </p>

    <!-- Table -->
    <div class="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <p
        v-if="isLoading"
        class="px-4 py-8 text-center text-sm text-slate-500"
      >
        Chargement des offres…
      </p>
      <p
        v-else-if="error"
        class="px-4 py-8 text-center text-sm text-red-600"
        role="alert"
      >
        {{ error instanceof Error ? error.message : 'Impossible de charger les offres.' }}
      </p>
      <p
        v-else-if="items.length === 0"
        class="px-4 py-8 text-center text-sm text-slate-500"
      >
        Aucune offre ne correspond à ces critères.
      </p>

      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="min-w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50/70">
              <th
                v-if="props.bulk"
                scope="col"
                class="w-10 px-3 py-2.5"
              >
                <input
                  type="checkbox"
                  aria-label="Tout sélectionner"
                  class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  @change="toggleAll"
                >
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Poste
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Entreprise
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Ville
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Contrat
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Secteur
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Score
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Statut
              </th>
              <th
                scope="col"
                class="px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500"
              >
                Recueillie
              </th>
              <th scope="col" class="px-3 py-2.5">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="o in items"
              :key="o.id"
              class="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/70"
            >
              <td
                v-if="props.bulk"
                class="px-3 py-3"
              >
                <input
                  type="checkbox"
                  :aria-label="`Sélectionner ${o.title ?? 'offre'}`"
                  class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  :checked="selected.includes(o.id)"
                  @change="toggleOne(o.id)"
                >
              </td>
              <td class="max-w-xs px-3 py-3">
                <button
                  type="button"
                  class="text-left font-semibold text-slate-900 transition-colors hover:text-sky-700"
                  @click="goTo(o.id)"
                >
                  {{ o.title || '(sans titre)' }}
                </button>
                <span
                  v-if="o.suspicious"
                  class="ml-2 rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-700"
                >
                  À vérifier
                </span>
              </td>
              <td class="px-3 py-3 text-slate-700">
                {{ o.company || '—' }}
              </td>
              <td class="px-3 py-3 text-slate-700">
                {{ o.city || '—' }}
              </td>
              <td class="px-3 py-3">
                <span
                  v-if="o.contract_type"
                  class="rounded px-2.5 py-1 text-xs font-bold"
                  :class="contractClass(o.contract_type)"
                >
                  {{ o.contract_type }}
                </span>
                <span
                  v-else
                  class="text-slate-400"
                >—</span>
              </td>
              <td class="max-w-[12rem] truncate px-3 py-3 text-slate-600">
                {{ o.sector || '—' }}
              </td>
              <td class="px-3 py-3">
                <span class="font-mono text-xs font-semibold text-slate-700">
                  {{ o.score === null ? '—' : o.score.toFixed(2) }}
                </span>
              </td>
              <td class="px-3 py-3">
                <span
                  class="rounded px-2.5 py-1 text-xs font-semibold"
                  :class="statusClass(o.status)"
                >
                  {{ statusLabel(o.status) }}
                </span>
              </td>
              <td class="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-500">
                {{ formatRelative(o.created_at) }}
              </td>
              <td class="px-3 py-3 text-right">
                <button
                  type="button"
                  class="rounded-lg border border-sky-300 bg-sky-50 px-3 py-1.5 text-xs font-semibold text-sky-800 transition-all hover:bg-sky-600 hover:text-white active:scale-[0.98]"
                  @click="goTo(o.id)"
                >
                  Détails
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div
      v-if="hasNextPage"
      class="flex flex-col items-center gap-2 pt-2"
    >
      <button
        type="button"
        class="inline-flex items-center gap-2 rounded-xl border border-sky-300 bg-white px-6 py-3 text-sm font-semibold text-sky-800 shadow-sm transition-all hover:bg-sky-50 hover:shadow active:scale-[0.98]"
        :disabled="isFetchingNextPage"
        @click="fetchNextPage()"
      >
        <UIcon
          name="i-lucide-chevron-down"
          class="size-4"
        />
        Charger plus d'offres
      </button>
      <span class="font-mono text-xs text-slate-400">
        {{ isFetching || isFetchingNextPage ? 'Chargement…' : `Affichage de ${total} offre(s), les plus récentes d'abord` }}
      </span>
    </div>
  </div>
</template>
