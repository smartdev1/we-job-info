<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const api = useApi()

const id = computed(() => route.params.id as string)

interface OfferDuplicate {
  id: string
  title: string | null
  company: string | null
}

interface Offer {
  id: string
  title: string | null
  company: string | null
  city: string | null
  contract_type: string | null
  sector: string | null
  description: string | null
  missions: string[] | null
  profile: string[] | null
  benefits: string | null
  how_to_apply: string | null
  contact_email: string | null
  application_url: string | null
  deadline: string | null
  origin_url: string | null
  confidence: Record<string, string> | null
  suspicious: boolean
  suspicion_reasons: string[] | null
  status: string
  score: number | null
  duplicates: OfferDuplicate[] | null
  internal_note: string | null
  allowed_transitions: string[] | null
  created_at: string
}

const STATUS_LABELS: Record<string, string> = {
  nouvelle: 'Nouvelle',
  selectionnee: 'Sélectionnée',
  rejetee: 'Rejetée',
  publiee: 'Publiée',
  archivee: 'Archivée'
}

const TRANSITION_LABELS: Record<string, string> = {
  selectionnee: 'Sélectionner',
  rejetee: 'Rejeter',
  publiee: 'Publier',
  archivee: 'Archiver',
  nouvelle: 'Remettre à neuve'
}

const offer = ref<Offer | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const saving = ref(false)
const saveMsg = ref<string | null>(null)
const actionMsg = ref<string | null>(null)

const editableFields = ['title', 'company', 'city', 'contract_type', 'sector', 'description'] as const
const form = reactive<Record<string, string>>({})

const statusLabel = computed(() => (offer.value ? STATUS_LABELS[offer.value.status] ?? offer.value.status : ''))
const transitions = computed(() => offer.value?.allowed_transitions ?? [])

function confidenceLevel(field: string): string {
  return offer.value?.confidence?.[field] || 'unknown'
}

function confidenceClass(field: string): string {
  const level = confidenceLevel(field)
  if (level === 'high') return 'border-emerald-400 focus:border-emerald-500 focus:ring-emerald-500/25'
  if (level === 'medium') return 'border-amber-400 focus:border-amber-500 focus:ring-amber-500/25'
  if (level === 'low') return 'border-red-400 focus:border-red-500 focus:ring-red-500/25'
  return 'border-slate-200 focus:border-sky-500 focus:ring-sky-500/25'
}

function confidenceTextClass(field: string): string {
  const level = confidenceLevel(field)
  if (level === 'high') return 'text-emerald-600'
  if (level === 'medium') return 'text-amber-600'
  if (level === 'low') return 'text-red-600'
  return 'text-slate-400'
}

function confidenceLabel(field: string): string {
  const labels: Record<string, string> = {
    high: 'Fiable',
    medium: 'À vérifier',
    low: 'Douteux',
    unknown: 'Non renseignée'
  }
  return labels[confidenceLevel(field)] ?? confidenceLevel(field)
}

function fieldLabel(field: string): string {
  const labels: Record<string, string> = {
    title: 'Poste',
    company: 'Entreprise',
    city: 'Ville',
    contract_type: 'Contrat',
    sector: 'Secteur',
    description: 'Description'
  }
  return labels[field] ?? field
}

async function load() {
  loading.value = true
  error.value = null
  try {
    const { data, error: err } = await api.get<Offer>(`/api/v1/offers/${id.value}`)
    if (err) throw new Error(err.message)
    offer.value = data as Offer
    for (const field of editableFields) {
      form[field] = (offer.value[field] as string | null) ?? ''
    }
    form.internal_note = offer.value.internal_note ?? ''
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Impossible de charger cette offre.'
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  saveMsg.value = null
  error.value = null
  try {
    const payload: Record<string, unknown> = {}
    for (const field of editableFields) payload[field] = form[field] || null
    payload.internal_note = form.internal_note || null
    const { error: err } = await api.patch(`/api/v1/offers/${id.value}`, payload)
    if (err) throw new Error(err.message)
    saveMsg.value = 'Modifications enregistrées.'
    await load()
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Enregistrement impossible.'
  } finally {
    saving.value = false
  }
}

async function transition(target: string) {
  error.value = null
  actionMsg.value = null
  const { error: err } = await api.post(`/api/v1/offers/${id.value}/status`, { status: target })
  if (err) {
    error.value = 'Transition impossible depuis le statut actuel.'
    return
  }
  actionMsg.value = `Statut mis à jour : ${STATUS_LABELS[target] ?? target}.`
  await load()
}

/** A near duplicate is never deleted: it is parked on "rejetee", a state the
 *  operator can undo, and the link back to the kept offer stays visible. */
async function parkDuplicate(duplicateId: string) {
  const { error: err } = await api.post(`/api/v1/offers/${duplicateId}/status`, { status: 'rejetee' })
  if (err) {
    error.value = 'Impossible de signaler ce doublon.'
    return
  }
  actionMsg.value = 'Doublon signalé.'
  await load()
}

function generate() {
  router.push(`/generate/${id.value}`)
}

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center gap-3">
      <NuxtLink
        to="/offers"
        class="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm font-semibold text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900"
      >
        <UIcon
          name="i-lucide-arrow-left"
          class="size-4"
        />
        Offres
      </NuxtLink>
    </div>

    <p
      v-if="loading"
      class="text-sm text-slate-500"
    >
      Chargement de la fiche…
    </p>
    <p
      v-else-if="error && !offer"
      class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
      role="alert"
    >
      {{ error }}
    </p>

    <template v-if="offer">
      <!-- Header -->
      <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-start gap-3">
          <div class="min-w-0 flex-1">
            <h1 class="text-xl font-extrabold tracking-tight text-slate-900">
              {{ offer.title || '(sans titre)' }}
            </h1>
            <p class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-600">
              <span v-if="offer.company">{{ offer.company }}</span>
              <span v-if="offer.city" class="inline-flex items-center gap-1">
                <UIcon
                  name="i-lucide-map-pin"
                  class="size-3.5 text-slate-400"
                />
                {{ offer.city }}
              </span>
              <a
                v-if="offer.origin_url"
                :href="offer.origin_url"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1 font-semibold text-sky-700 underline-offset-2 hover:underline"
              >
                <UIcon
                  name="i-lucide-external-link"
                  class="size-3.5"
                />
                Offre d'origine
              </a>
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <span
              v-if="offer.suspicious"
              class="rounded bg-red-50 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-red-700"
            >
              À vérifier
            </span>
            <span class="rounded bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
              {{ statusLabel }}
            </span>
            <span
              v-if="offer.score !== null"
              class="rounded bg-sky-50 px-2.5 py-1 font-mono text-xs font-semibold text-sky-800"
            >
              score {{ offer.score.toFixed(2) }}
            </span>
          </div>
        </div>

        <div class="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
          <button
            v-for="target in transitions"
            :key="target"
            type="button"
            class="rounded-lg px-3 py-1.5 text-xs font-semibold transition-all active:scale-[0.98]"
            :class="target === 'rejetee'
              ? 'bg-white text-red-700 ring-1 ring-red-200 hover:bg-red-50'
              : 'bg-sky-600 text-white shadow-sm hover:bg-sky-700'"
            @click="transition(target)"
          >
            {{ TRANSITION_LABELS[target] ?? target }}
          </button>
          <button
            type="button"
            class="ml-auto inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all hover:bg-slate-700 active:scale-[0.98]"
            @click="generate"
          >
            <UIcon
              name="i-lucide-wand-sparkles"
              class="size-3.5"
            />
            Préparer la publication
          </button>
        </div>

        <p
          v-if="actionMsg"
          class="mt-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800"
          role="status"
        >
          {{ actionMsg }}
        </p>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <!-- Left: read-only content -->
        <div class="space-y-4 lg:col-span-2">
          <section
            v-if="offer.suspicion_reasons?.length"
            class="rounded-xl border border-red-200 bg-red-50/60 p-5"
            aria-labelledby="suspicion-heading"
          >
            <h2
              id="suspicion-heading"
              class="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-red-700"
            >
              <UIcon
                name="i-lucide-shield-alert"
                class="size-4"
              />
              Signaux d'alerte
            </h2>
            <ul class="mt-3 space-y-1.5 text-sm text-red-800">
              <li
                v-for="reason in offer.suspicion_reasons"
                :key="reason"
                class="flex gap-2"
              >
                <span aria-hidden="true">•</span>
                <span>{{ reason }}</span>
              </li>
            </ul>
          </section>

          <section
            v-if="offer.description"
            class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            aria-labelledby="description-heading"
          >
            <h2
              id="description-heading"
              class="text-sm font-bold uppercase tracking-wider text-slate-500"
            >
              Description
            </h2>
            <p class="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {{ offer.description }}
            </p>
          </section>

          <section
            v-if="offer.missions?.length"
            class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            aria-labelledby="missions-heading"
          >
            <h2
              id="missions-heading"
              class="text-sm font-bold uppercase tracking-wider text-slate-500"
            >
              Missions
            </h2>
            <ul class="mt-3 space-y-2">
              <li
                v-for="mission in offer.missions"
                :key="mission"
                class="flex gap-2.5 text-sm leading-relaxed text-slate-700"
              >
                <UIcon
                  name="i-lucide-check-circle-2"
                  class="mt-0.5 size-4 shrink-0 text-sky-600"
                />
                <span>{{ mission }}</span>
              </li>
            </ul>
          </section>

          <section
            v-if="offer.profile?.length"
            class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            aria-labelledby="profile-heading"
          >
            <h2
              id="profile-heading"
              class="text-sm font-bold uppercase tracking-wider text-slate-500"
            >
              Profil recherché
            </h2>
            <ul class="mt-3 space-y-2">
              <li
                v-for="criterion in offer.profile"
                :key="criterion"
                class="flex gap-2.5 text-sm leading-relaxed text-slate-700"
              >
                <UIcon
                  name="i-lucide-user-round"
                  class="mt-0.5 size-4 shrink-0 text-slate-400"
                />
                <span>{{ criterion }}</span>
              </li>
            </ul>
          </section>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <section
              v-if="offer.benefits"
              class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              aria-labelledby="benefits-heading"
            >
              <h2
                id="benefits-heading"
                class="text-sm font-bold uppercase tracking-wider text-slate-500"
              >
                Avantages
              </h2>
              <p class="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {{ offer.benefits }}
              </p>
            </section>

            <section
              v-if="offer.how_to_apply"
              class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
              aria-labelledby="apply-heading"
            >
              <h2
                id="apply-heading"
                class="text-sm font-bold uppercase tracking-wider text-slate-500"
              >
                Comment postuler
              </h2>
              <p class="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {{ offer.how_to_apply }}
              </p>
              <a
                v-if="offer.application_url"
                :href="offer.application_url"
                target="_blank"
                rel="noopener noreferrer"
                class="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-sky-700 underline-offset-2 hover:underline"
              >
                Lien de candidature
                <UIcon
                  name="i-lucide-external-link"
                  class="size-3.5"
                />
              </a>
              <p
                v-if="offer.contact_email"
                class="mt-2 font-mono text-xs text-slate-500"
              >
                {{ offer.contact_email }}
              </p>
            </section>
          </div>

          <section
            v-if="offer.duplicates?.length"
            class="rounded-xl border border-amber-200 bg-amber-50/60 p-5"
            aria-labelledby="duplicates-heading"
          >
            <h2
              id="duplicates-heading"
              class="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-amber-800"
            >
              <UIcon
                name="i-lucide-copy-check"
                class="size-4"
              />
              Doublons signalés
            </h2>
            <p class="mt-2 text-xs text-amber-800">
              Ces offres ressemblent à celle-ci. Elles ne sont jamais supprimées : les signaler les met de côté,
              et l'action reste réversible.
            </p>
            <ul class="mt-3 space-y-2">
              <li
                v-for="duplicate in offer.duplicates"
                :key="duplicate.id"
                class="flex flex-wrap items-center gap-3 rounded-lg bg-white/70 px-3 py-2 ring-1 ring-amber-200"
              >
                <span class="min-w-0 flex-1 text-sm font-medium text-slate-800">
                  {{ duplicate.title || '(sans titre)' }}
                  <span
                    v-if="duplicate.company"
                    class="text-slate-500"
                  > — {{ duplicate.company }}</span>
                </span>
                <NuxtLink
                  :to="`/offers/${duplicate.id}`"
                  class="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50"
                >
                  Ouvrir
                </NuxtLink>
                <button
                  type="button"
                  class="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-amber-700"
                  @click="parkDuplicate(duplicate.id)"
                >
                  Signaler comme doublon
                </button>
              </li>
            </ul>
          </section>
        </div>

        <!-- Right: correction form -->
        <div class="lg:col-span-1">
          <form
            class="sticky top-20 space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            @submit.prevent="save"
          >
            <h2 class="text-sm font-bold uppercase tracking-wider text-slate-500">
              Correction
            </h2>

            <div
              v-for="field in editableFields"
              :key="field"
              class="space-y-1.5"
            >
              <label
                :for="field"
                class="block text-sm font-medium text-slate-700"
              >
                {{ fieldLabel(field) }}
              </label>
              <textarea
                v-if="field === 'description'"
                :id="field"
                v-model="form[field]"
                rows="5"
                class="w-full rounded-lg border-2 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors"
                :class="confidenceClass(field)"
              />
              <input
                v-else
                :id="field"
                v-model="form[field]"
                type="text"
                class="w-full rounded-lg border-2 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors"
                :class="confidenceClass(field)"
              >
              <span
                class="text-xs font-medium"
                :class="confidenceTextClass(field)"
              >
                Extraction : {{ confidenceLabel(field) }}
              </span>
            </div>

            <div class="space-y-1.5">
              <label
                for="internal_note"
                class="block text-sm font-medium text-slate-700"
              >
                Note interne
              </label>
              <textarea
                id="internal_note"
                v-model="form.internal_note"
                rows="3"
                class="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none transition-colors focus:border-sky-500 focus:ring-2 focus:ring-sky-500/25"
              />
            </div>

            <button
              type="submit"
              class="w-full rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-sky-700 active:scale-[0.98] disabled:opacity-60"
              :disabled="saving"
            >
              {{ saving ? 'Enregistrement…' : 'Enregistrer' }}
            </button>

            <p
              v-if="saveMsg"
              class="text-sm font-medium text-emerald-700"
              role="status"
            >
              {{ saveMsg }}
            </p>
            <p
              v-if="error"
              class="text-sm font-medium text-red-600"
              role="alert"
            >
              {{ error }}
            </p>
          </form>
        </div>
      </div>
    </template>
  </div>
</template>
